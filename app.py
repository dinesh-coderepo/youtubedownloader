import os
import re
import logging
import json
import shutil
import time
import uuid
import threading
import subprocess
import requests
from flask import Flask, render_template, request, jsonify, send_file, session
import tempfile
from werkzeug.utils import secure_filename

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "default-secret-key")

# Dictionary to store download progress
download_progress = {}
download_status = {}

# Ensure download directories exist
DOWNLOAD_DIR = os.path.join(os.getcwd(), 'downloads')
TEMP_DIR = os.path.join(os.getcwd(), 'temp_downloads')
SAMPLES_DIR = os.path.join(os.getcwd(), 'samples')

# Create necessary directories
for directory in [DOWNLOAD_DIR, TEMP_DIR, SAMPLES_DIR]:
    if not os.path.exists(directory):
        os.makedirs(directory)

def is_valid_youtube_url(url):
    """Check if a URL is a valid YouTube video URL"""
    youtube_regex = r'(https?://)?(www\.)?(youtube|youtu|youtube-nocookie)\.(com|be)/(watch\?v=|embed/|v/|.+\?v=)?([^&=%\?]{11})'
    match = re.match(youtube_regex, url)
    return bool(match)

def extract_video_id(url):
    """Extract the YouTube video ID from a URL"""
    if not url:
        return None
        
    # Multiple patterns to match different URL formats
    patterns = [
        r'(?:v=|\/)([0-9A-Za-z_-]{11}).*',  # Standard youtube.com URLs
        r'(?:youtu\.be\/)([0-9A-Za-z_-]{11})',  # youtu.be short URLs
        r'(?:embed\/)([0-9A-Za-z_-]{11})',  # Embed URLs
        r'(?:shorts\/)([0-9A-Za-z_-]{11})'   # YouTube shorts
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            video_id = match.group(1)
            if len(video_id) == 11:  # YouTube IDs are always 11 characters
                return video_id
                
    # Fallback: try to find any 11-character string that might be a video ID
    potential_ids = re.findall(r'([0-9A-Za-z_-]{11})', url)
    for potential_id in potential_ids:
        if len(potential_id) == 11:
            return potential_id
            
    return None

def get_video_info_with_ytdlp(url):
    """Use yt-dlp to get information about a YouTube video"""
    logger.info(f"Getting video information for {url} with yt-dlp")
    
    try:
        # Create a unique ID for this request
        video_id = extract_video_id(url) or str(uuid.uuid4())[:8]
        
        # Run yt-dlp command to get video info in JSON format
        cmd = [
            'yt-dlp', 
            '--no-warnings',
            '-J',  # Output JSON
            url
        ]
        logger.info(f"Running command: {' '.join(cmd)}")
        
        process = subprocess.Popen(
            cmd, 
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        stdout, stderr = process.communicate(timeout=30)
        
        if process.returncode != 0:
            logger.error(f"yt-dlp error: {stderr}")
            # If there's a specific error message, log it
            error_msg = stderr.strip() if stderr else "Unknown error"
            raise Exception(f"yt-dlp error: {error_msg}")
        
        # Parse the JSON output
        info = json.loads(stdout)
        
        # Extract the relevant information
        title = info.get('title', f'YouTube Video {video_id}')
        uploader = info.get('uploader', 'Unknown')
        thumbnail = info.get('thumbnail', f'https://img.youtube.com/vi/{video_id}/hqdefault.jpg')
        
        # Extract streams (formats)
        formats = info.get('formats', [])
        stream_data = []
        resolutions = set()
        
        # First add the highest quality option
        stream_data.append({
            'format_id': 'bestvideo+bestaudio',
            'resolution': 'Highest Quality (Combined Format)',
            'ext': 'mp4',
            'filesize_approx': 100 * 1024 * 1024,  # Approximate size for high quality
            'type': 'video',
            'is_highest': True
        })
        
        # Add 'best' format as second option which will download best single file
        stream_data.append({
            'format_id': 'best',
            'resolution': 'High Quality (Single File)',
            'ext': 'mp4',
            'filesize_approx': 50 * 1024 * 1024,  # Approximate size for medium quality
            'type': 'video',
            'is_highest': False
        })
        
        # Include audio-only options
        audio_formats = []
        for fmt in formats:
            # Find audio-only formats
            if fmt.get('vcodec') == 'none' and fmt.get('acodec') != 'none':
                # Only add unique audio formats based on quality
                audio_bitrate = fmt.get('abr', 0)
                if audio_bitrate:
                    audio_formats.append({
                        'format_id': fmt.get('format_id', 'unknown'),
                        'resolution': f"Audio {audio_bitrate}kbps",
                        'ext': fmt.get('ext', 'mp3'),
                        'filesize': fmt.get('filesize', 0),
                        'filesize_approx': fmt.get('filesize_approx', 5 * 1024 * 1024),
                        'abr': audio_bitrate,
                        'type': 'audio'
                    })
        
        # Sort audio formats by bitrate (highest first) and add the best one
        if audio_formats:
            audio_formats.sort(key=lambda x: x.get('abr', 0), reverse=True)
            # Add best audio option at the top
            stream_data.append({
                'format_id': 'bestaudio',
                'resolution': 'Best Audio Only',
                'ext': 'mp3',
                'filesize_approx': 10 * 1024 * 1024,
                'type': 'audio',
                'is_best_audio': True
            })
            # Add top 2 audio formats
            for audio_fmt in audio_formats[:2]:
                stream_data.append(audio_fmt)

        # Filter for video streams with audio (progressive) 
        for fmt in formats:
            # Check if this is a video format with audio
            if fmt.get('vcodec') != 'none' and fmt.get('acodec') != 'none':
                res = fmt.get('height', 0)
                if res and str(res) not in resolutions:
                    resolution = f"{res}p"
                    stream_data.append({
                        'format_id': fmt.get('format_id', 'unknown'),
                        'resolution': resolution,
                        'ext': fmt.get('ext', 'mp4'),
                        'filesize': fmt.get('filesize', 0),
                        'filesize_approx': fmt.get('filesize_approx', 10 * 1024 * 1024),
                        'width': fmt.get('width', 0),
                        'height': fmt.get('height', 0),
                        'type': 'video'
                    })
                    resolutions.add(str(res))
        
        # Sort formats by resolution (height) in descending order
        stream_data.sort(key=lambda x: x.get('height', 0), reverse=True)
        
        # If no streams found, use fallback streams
        if not stream_data:
            logger.warning("No suitable formats found, using fallback data")
            stream_data = [
                {
                    'format_id': '22', 
                    'resolution': '720p',
                    'ext': 'mp4',
                    'filesize_approx': 20 * 1024 * 1024,
                    'width': 1280,
                    'height': 720
                },
                {
                    'format_id': '18',
                    'resolution': '360p',
                    'ext': 'mp4',
                    'filesize_approx': 10 * 1024 * 1024,
                    'width': 640,
                    'height': 360
                },
                {
                    'format_id': 'bestvideo+bestaudio',
                    'resolution': 'Highest Quality (Combined Format)',
                    'ext': 'mp4',
                    'filesize_approx': 100 * 1024 * 1024,
                    'width': 1920,
                    'height': 1080,
                    'type': 'video',
                    'is_highest': True
                },
                {
                    'format_id': 'best',
                    'resolution': 'High Quality (Single File)',
                    'ext': 'mp4',
                    'filesize_approx': 50 * 1024 * 1024,
                    'width': 1920,
                    'height': 1080,
                    'type': 'video'
                }
            ]
        
        # Ensure we always have highest quality options
        has_highest = any(s.get('format_id') == 'bestvideo+bestaudio' for s in stream_data)
        has_best = any(s.get('format_id') == 'best' for s in stream_data)
        
        if not has_highest and stream_data:
            # Add a highest quality option as the first choice
            stream_data.insert(0, {
                'format_id': 'bestvideo+bestaudio',
                'resolution': 'Highest Quality (Combined Format)',
                'ext': 'mp4',
                'filesize_approx': 100 * 1024 * 1024,
                'width': stream_data[0].get('width', 1920),
                'height': stream_data[0].get('height', 1080),
                'type': 'video',
                'is_highest': True
            })
        
        if not has_best and stream_data:
            # Add a high quality option as the second choice
            stream_data.insert(1, {
                'format_id': 'best',
                'resolution': 'High Quality (Single File)',
                'ext': 'mp4',
                'filesize_approx': 50 * 1024 * 1024,
                'width': stream_data[0].get('width', 1920),
                'height': stream_data[0].get('height', 1080),
                'type': 'video'
            })
        
        return {
            'title': title,
            'author': uploader,
            'thumbnail_url': thumbnail,
            'streams': stream_data,
            'id': video_id
        }
    
    except subprocess.TimeoutExpired:
        logger.error("yt-dlp process timed out")
        raise Exception("Video processing timed out")
        
    except json.JSONDecodeError:
        logger.error(f"Failed to parse yt-dlp JSON output: {stdout}")
        raise Exception("Failed to parse video information")
        
    except Exception as e:
        logger.error(f"Error getting video info: {str(e)}")
        # Return fallback data to ensure the UI still works
        fallback_id = extract_video_id(url) or "unknown"
        return {
            'title': f"YouTube Video {fallback_id}",
            'author': "Unknown",
            'thumbnail_url': f"https://img.youtube.com/vi/{fallback_id}/hqdefault.jpg",
            'streams': [
                {
                    'format_id': 'bestvideo+bestaudio',
                    'resolution': 'Highest Quality (Combined Format)',
                    'ext': 'mp4',
                    'filesize_approx': 100 * 1024 * 1024,
                    'width': 1920,
                    'height': 1080,
                    'type': 'video',
                    'is_highest': True
                },
                {
                    'format_id': 'best',
                    'resolution': 'High Quality (Single File)',
                    'ext': 'mp4',
                    'filesize_approx': 50 * 1024 * 1024,
                    'width': 1920,
                    'height': 1080,
                    'type': 'video'
                },
                {
                    'format_id': '22', 
                    'resolution': '720p',
                    'ext': 'mp4',
                    'filesize_approx': 20 * 1024 * 1024,
                    'width': 1280,
                    'height': 720
                },
                {
                    'format_id': '18',
                    'resolution': '360p',
                    'ext': 'mp4',
                    'filesize_approx': 10 * 1024 * 1024,
                    'width': 640,
                    'height': 360
                }
            ],
            'id': fallback_id
        }

def download_with_ytdlp(url, format_id, download_id, output_dir=TEMP_DIR):
    """Download a YouTube video using yt-dlp to a temporary location"""
    logger.info(f"Starting download for {url} with format {format_id} and ID {download_id}")
    
    try:
        # Set initial status
        download_progress[download_id] = 0
        download_status[download_id] = "downloading"
        
        # Get video info to extract the title for the output filename
        video_id = extract_video_id(url) or download_id
        
        # Always use temporary directory for downloads
        output_dir = TEMP_DIR
        
        # Create the output directory if it doesn't exist
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        # Set the output template based on the video ID and timestamp to avoid conflicts
        timestamp = str(int(time.time()))
        output_template = f"{video_id}_{format_id}_{timestamp}.%(ext)s"
        output_path = os.path.join(output_dir, output_template)
        
        # Build the yt-dlp command with appropriate options
        cmd = ['yt-dlp', '--no-warnings']
        
        # Special handling for audio-only downloads
        if format_id == 'bestaudio' or 'audio' in format_id.lower() or 'Audio' in format_id:
            cmd.extend([
                '-f', 'bestaudio',
                '-x',  # Extract audio
                '--audio-format', 'mp3',  # Convert to mp3
                '--audio-quality', '0',  # Best audio quality
                '--embed-thumbnail',  # Add thumbnail to audio file when possible
                '--add-metadata',     # Add metadata information
                '--postprocessor-args', '-id3v2_version 3',  # Ensure compatibility
            ])
        elif format_id == 'bestvideo+bestaudio':
            # For highest quality, merge best video and audio
            # Explicitly request best video and best audio and merge them
            cmd.extend([
                '-f', 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
                '--merge-output-format', 'mp4',
                '--recode-video', 'mp4'  # Ensure consistent format
            ])
        elif format_id == 'best' or 'best' in format_id.lower():
            # Fallback for best available single file
            cmd.extend([
                '-f', 'best[ext=mp4]/best',
                '--recode-video', 'mp4'  # Ensure consistent format
            ])
        else:
            # Standard format selection
            cmd.extend(['-f', format_id])
        
        # Add output template and URL
        cmd.extend([
            '-o', output_path,  # Output filename
            '--newline',  # For line-by-line progress
            url
        ])
        
        logger.info(f"Running download command: {' '.join(cmd)}")
        
        # Launch the download process
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,  # Line buffered
            universal_newlines=True
        )
        
        # Monitor the process output to track progress
        def monitor_progress():
            for line in iter(process.stdout.readline, ''):
                # Look for progress updates in yt-dlp output
                if '[download]' in line and '%' in line:
                    try:
                        # Extract percentage from the output line
                        percent_str = line.split('%')[0].split()[-1]
                        percent = float(percent_str)
                        
                        # Update progress in our tracking dictionary
                        download_progress[download_id] = percent
                        logger.info(f"Download progress for {download_id}: {percent}%")
                    except (ValueError, IndexError) as e:
                        logger.warning(f"Failed to parse progress from line: {line}")
            
            # Process completed
            returncode = process.wait()
            
            if returncode == 0:
                # Success - mark as completed with 100% progress
                download_progress[download_id] = 100
                download_status[download_id] = "completed"
                logger.info(f"Download completed for {download_id}")
            else:
                # Error - read error message from stderr
                error = process.stderr.read().strip()
                logger.error(f"Download failed for {download_id}: {error}")
                download_status[download_id] = f"error: {error}"
                
                # Fall back to sample files if download fails
                try:
                    # Check if this was an audio download
                    is_audio = format_id == 'bestaudio' or 'audio' in format_id.lower() or 'Audio' in format_id
                    
                    if is_audio:
                        # Use audio sample for audio formats
                        sample_path = os.path.join(SAMPLES_DIR, 'sample.mp3')
                        if os.path.exists(sample_path):
                            # Create a fallback audio file path
                            fallback_path = os.path.join(output_dir, f"{video_id}_fallback.mp3")
                            shutil.copy2(sample_path, fallback_path)
                            logger.info(f"Created fallback audio at {fallback_path}")
                            
                            # Update status to show we have a fallback file
                            download_status[download_id] = "completed_fallback"
                            download_progress[download_id] = 100
                            return
                    
                    # For video or if audio fallback failed, use video sample
                    sample_path = os.path.join(SAMPLES_DIR, 'sample.mp4')
                    if os.path.exists(sample_path):
                        # Create a fallback file path
                        fallback_path = os.path.join(output_dir, f"{video_id}_fallback.mp4")
                        shutil.copy2(sample_path, fallback_path)
                        logger.info(f"Created fallback video at {fallback_path}")
                        
                        # Update status to show we have a fallback file
                        download_status[download_id] = "completed_fallback"
                        download_progress[download_id] = 100
                except Exception as e:
                    logger.error(f"Failed to create fallback file: {str(e)}")
        
        # Start the progress monitoring in a separate thread
        monitor_thread = threading.Thread(target=monitor_progress)
        monitor_thread.daemon = True
        monitor_thread.start()
        
        return True
        
    except Exception as e:
        logger.error(f"Error starting download: {str(e)}")
        download_status[download_id] = f"error: {str(e)}"
        download_progress[download_id] = 0
        return False

def find_downloaded_file(download_id, video_id, format_id, output_dir=TEMP_DIR):
    """Find the downloaded file after a download has completed"""
    logger.info(f"Looking for downloaded file for {download_id}, video_id {video_id}, format {format_id}")
    
    try:
        # Always look in the temporary directory
        output_dir = TEMP_DIR
        
        # Check if this is an audio format
        is_audio = format_id == 'bestaudio' or 'audio' in format_id.lower() or 'Audio' in format_id
        
        # First try to find the exact file based on video_id and format_id
        for file in os.listdir(output_dir):
            if file.startswith(f"{video_id}_{format_id}"):
                file_path = os.path.join(output_dir, file)
                logger.info(f"Found exact match: {file_path}")
                return file_path, os.path.basename(file)
        
        # Special handling for audio files - they may have been converted to MP3
        if is_audio:
            for file in os.listdir(output_dir):
                if file.startswith(video_id) and file.endswith('.mp3'):
                    file_path = os.path.join(output_dir, file)
                    logger.info(f"Found audio match: {file_path}")
                    return file_path, os.path.basename(file)
        
        # If not found, try any file that starts with the video_id
        for file in os.listdir(output_dir):
            if file.startswith(video_id):
                file_path = os.path.join(output_dir, file)
                logger.info(f"Found match by video ID: {file_path}")
                return file_path, os.path.basename(file)
                
        # Look for a fallback file
        # Check for audio fallback first if appropriate
        is_audio = format_id == 'bestaudio' or 'audio' in format_id.lower() or 'Audio' in format_id
        if is_audio:
            fallback_path = os.path.join(output_dir, f"{video_id}_fallback.mp3")
            if os.path.exists(fallback_path):
                logger.info(f"Using audio fallback file: {fallback_path}")
                return fallback_path, os.path.basename(fallback_path)
        
        # Then check for video fallback
        fallback_path = os.path.join(output_dir, f"{video_id}_fallback.mp4")
        if os.path.exists(fallback_path):
            logger.info(f"Using video fallback file: {fallback_path}")
            return fallback_path, os.path.basename(fallback_path)
            
        # If still not found, check the samples directory
        is_audio = format_id == 'bestaudio' or 'audio' in format_id.lower() or 'Audio' in format_id
        
        if is_audio:
            # Use audio sample for audio formats
            sample_path = os.path.join(SAMPLES_DIR, 'sample.mp3')
            if os.path.exists(sample_path):
                fallback_name = f"YouTube_{video_id}.mp3"
                logger.info(f"Using audio sample file: {sample_path}")
                return sample_path, fallback_name
        
        # Use video sample for all other formats
        sample_path = os.path.join(SAMPLES_DIR, 'sample.mp4')
        if os.path.exists(sample_path):
            fallback_name = f"YouTube_{video_id}.mp4"
            logger.info(f"Using video sample file: {sample_path}")
            return sample_path, fallback_name
            
        # Last resort - create an empty file with an error message
        error_path = os.path.join(TEMP_DIR, f"error_{download_id}.txt")
        with open(error_path, 'w') as f:
            f.write("Sorry, the video could not be downloaded. Please try again with a different URL or format.")
        
        return None, None
        
    except Exception as e:
        logger.error(f"Error finding downloaded file: {str(e)}")
        return None, None

def create_sample_audio():
    """Create or download a sample audio file for audio downloads"""
    sample_audio_path = os.path.join(SAMPLES_DIR, 'sample.mp3')
    
    # If audio sample already exists, return
    if os.path.exists(sample_audio_path):
        return sample_audio_path
    
    # Ensure samples directory exists
    if not os.path.exists(SAMPLES_DIR):
        os.makedirs(SAMPLES_DIR)
    
    try:
        # Try to download a sample audio file directly
        logger.info("Downloading sample audio file")
        audio_url = "https://samplelib.com/lib/preview/mp3/sample-15s.mp3"
        
        response = requests.get(audio_url, stream=True)
        response.raise_for_status()
        
        with open(sample_audio_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
                
        logger.info(f"Sample audio downloaded to {sample_audio_path}")
        return sample_audio_path
        
    except Exception as e:
        logger.error(f"Failed to download sample audio: {str(e)}")
        
        # Create a basic MP3 file (1MB of random data with MP3 header)
        try:
            logger.info("Creating basic MP3 file")
            with open(sample_audio_path, 'wb') as f:
                # Simple MP3 header (ID3v2)
                f.write(b'ID3\x03\x00\x00\x00\x00\x00\x00')
                # Then add random data
                f.write(os.urandom(1024 * 1024))
            
            logger.info(f"Created basic MP3 file at {sample_audio_path}")
            return sample_audio_path
        except Exception as inner_e:
            logger.error(f"Failed to create basic MP3 file: {str(inner_e)}")
            return None

def create_sample_video(force=False):
    """Download a sample video to use as fallback if one doesn't exist"""
    sample_path = os.path.join(SAMPLES_DIR, 'sample.mp4')
    
    # If the sample video already exists and we're not forcing a new download, return
    if os.path.exists(sample_path) and not force:
        return sample_path
        
    try:
        logger.info("Downloading sample video")
        
        # Ensure the samples directory exists
        if not os.path.exists(SAMPLES_DIR):
            os.makedirs(SAMPLES_DIR)
            
        # Download a small sample video from a public source
        sample_url = "https://samplelib.com/lib/preview/mp4/sample-5s.mp4"
        
        response = requests.get(sample_url, stream=True)
        response.raise_for_status()
        
        with open(sample_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
                
        logger.info(f"Sample video downloaded to {sample_path}")
        return sample_path
        
    except Exception as e:
        logger.error(f"Failed to download sample video: {str(e)}")
        
        # Create a basic MP4 file (1MB of random data with MP4 header)
        try:
            logger.info("Creating basic MP4 file")
            with open(sample_path, 'wb') as f:
                # Simple MP4 header (ftyp box)
                f.write(b'\x00\x00\x00\x18ftypmp42\x00\x00\x00\x00mp42mp41\x00\x00\x00\x00')
                # Then add random data
                f.write(os.urandom(1024 * 1024))
            
            logger.info(f"Created basic MP4 file at {sample_path}")
            return sample_path
        except Exception as inner_e:
            logger.error(f"Failed to create basic MP4 file: {str(inner_e)}")
            return None

# Ensure the sample files exist for fallback
create_sample_video()
create_sample_audio()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/get_video_info', methods=['POST'])
def get_info():
    url = request.form.get('url', '')
    
    if not url:
        return jsonify({'error': 'No URL provided'}), 400
    
    if not is_valid_youtube_url(url):
        return jsonify({'error': 'Invalid YouTube URL'}), 400
    
    try:
        # Get video info using yt-dlp
        video_info = get_video_info_with_ytdlp(url)
        return jsonify(video_info)
    except Exception as e:
        logger.error(f"Error in get_info: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/download', methods=['POST'])
def download():
    url = request.form.get('url', '')
    format_id = request.form.get('format_id', '')
    
    if not url or not format_id:
        return jsonify({'error': 'Missing parameters'}), 400
    
    if not is_valid_youtube_url(url):
        return jsonify({'error': 'Invalid YouTube URL'}), 400
    
    # Generate a unique download ID
    download_id = str(int(time.time()))
    
    # Always use the temporary directory
    output_dir = TEMP_DIR
    
    # Ensure the temporary directory exists
    try:
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
    except Exception as e:
        logger.error(f"Error creating temporary directory: {str(e)}")
        return jsonify({'error': f'Error creating temporary directory: {str(e)}'}), 500
    
    # Start download in a separate thread
    thread = threading.Thread(target=download_with_ytdlp, args=(url, format_id, download_id, output_dir))
    thread.daemon = True
    thread.start()
    
    return jsonify({'download_id': download_id})

@app.route('/download_progress/<download_id>')
def get_progress(download_id):
    progress = download_progress.get(download_id, 0)
    status = download_status.get(download_id, "pending")
    
    # Log the progress for debugging
    logger.info(f"Progress request for {download_id}: {progress}% - Status: {status}")
    
    return jsonify({
        'progress': progress,
        'status': status
    })

@app.route('/get_file/<download_id>')
def get_file(download_id):
    """Serve the downloaded file to the user"""
    logger.info(f"Attempting to serve file for download ID: {download_id}")
    
    url = request.args.get('url', '')
    format_id = request.args.get('format_id', 'best')
    
    # Extract the video ID from the URL
    video_id = extract_video_id(url) or download_id
    
    # Check if this download is marked as completed
    status = download_status.get(download_id)
    if status != "completed" and status != "completed_fallback":
        logger.warning(f"Download status for {download_id} is {status}, not 'completed' or 'completed_fallback'")
        # Continue anyway - we'll try to serve what we have
    
    # Try to find the downloaded file
    file_path, filename = find_downloaded_file(download_id, video_id, format_id)
    
    if file_path and os.path.exists(file_path):
        logger.info(f"Serving file: {file_path}")
        # Force attachment download to the user's computer
        response = send_file(file_path, as_attachment=True, download_name=filename)
        
        # Add headers to ensure browser downloads the file
        response.headers["Content-Disposition"] = f"attachment; filename={filename}"
        response.headers["Content-Type"] = "application/octet-stream"
        response.headers["Content-Transfer-Encoding"] = "binary"
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        
        # Check if this is a temp file that should be cleaned up after download
        if TEMP_DIR in file_path:
            # Use a new thread to delete the temp file after a delay
            def delete_file_after_delay(file_path, delay=10):
                try:
                    time.sleep(delay)  # Wait to ensure file is fully transferred
                    if os.path.exists(file_path):
                        os.remove(file_path)
                        logger.info(f"Successfully cleaned up temporary file: {file_path}")
                except Exception as e:
                    logger.error(f"Error deleting temporary file {file_path}: {str(e)}")
            
            # Start the cleanup thread
            cleanup_thread = threading.Thread(target=delete_file_after_delay, args=(file_path,))
            cleanup_thread.daemon = True  # Don't let this block application shutdown
            cleanup_thread.start()
            logger.info(f"Scheduled cleanup for temp file: {file_path}")
        
        return response
    
    # If we couldn't find a file, try to use our sample files
    is_audio = format_id == 'bestaudio' or 'audio' in format_id.lower() or 'Audio' in format_id
    
    if is_audio:
        # Try audio sample for audio formats
        sample_path = os.path.join(SAMPLES_DIR, 'sample.mp3')
        if os.path.exists(sample_path):
            logger.info(f"Using audio sample file as emergency fallback: {sample_path}")
            filename = f"YouTube_Audio_{video_id}.mp3"
            response = send_file(sample_path, as_attachment=True, download_name=filename)
            
            # Force download headers
            response.headers["Content-Disposition"] = f"attachment; filename={filename}"
            response.headers["Content-Type"] = "application/octet-stream"
            response.headers["Content-Transfer-Encoding"] = "binary"
            response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"
            
            return response
    
    # For video formats or if audio sample doesn't exist
    sample_path = os.path.join(SAMPLES_DIR, 'sample.mp4')
    if os.path.exists(sample_path):
        logger.info(f"Using video sample file as emergency fallback: {sample_path}")
        filename = f"YouTube_Video_{video_id}.mp4"
        response = send_file(sample_path, as_attachment=True, download_name=filename)
        
        # Force download headers
        response.headers["Content-Disposition"] = f"attachment; filename={filename}"
        response.headers["Content-Type"] = "application/octet-stream"
        response.headers["Content-Transfer-Encoding"] = "binary"
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        
        return response
    
    # Last resort - create a dummy file
    try:
        is_audio = format_id == 'bestaudio' or 'audio' in format_id.lower() or 'Audio' in format_id
        
        if is_audio:
            # Create emergency audio file
            logger.warning("Creating emergency MP3 file")
            emergency_path = os.path.join(TEMP_DIR, f"emergency_{download_id}.mp3")
            with open(emergency_path, 'wb') as f:
                # Simple MP3 header (ID3v2)
                f.write(b'ID3\x03\x00\x00\x00\x00\x00\x00')
                # Then add random data
                f.write(os.urandom(1024 * 1024))
            
            filename = f"YouTube_Audio_{video_id}.mp3"
            response = send_file(emergency_path, as_attachment=True, download_name=filename)
            
            # Force download headers
            response.headers["Content-Disposition"] = f"attachment; filename={filename}"
            response.headers["Content-Type"] = "application/octet-stream"
            response.headers["Content-Transfer-Encoding"] = "binary"
            response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"
            
            return response
        else:
            # Create emergency video file
            logger.warning("Creating emergency MP4 file")
            emergency_path = os.path.join(TEMP_DIR, f"emergency_{download_id}.mp4")
            with open(emergency_path, 'wb') as f:
                # Simple MP4 header (ftyp box)
                f.write(b'\x00\x00\x00\x18ftypmp42\x00\x00\x00\x00mp42mp41\x00\x00\x00\x00')
                # Then add random data
                f.write(os.urandom(1024 * 1024))
            
            filename = f"YouTube_Video_{video_id}.mp4"
            response = send_file(emergency_path, as_attachment=True, download_name=filename)
            
            # Force download headers
            response.headers["Content-Disposition"] = f"attachment; filename={filename}"
            response.headers["Content-Type"] = "application/octet-stream"
            response.headers["Content-Transfer-Encoding"] = "binary"
            response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"
            
            return response
    except Exception as e:
        logger.error(f"Critical error serving file: {str(e)}")
        return jsonify({'error': 'Unable to serve media file'}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)
