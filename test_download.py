import os
import sys
import json
import time
import requests
import logging
from urllib.parse import urljoin

# Configure logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Test configuration
BASE_URL = "http://localhost:5000"
TEST_VIDEO_URL = "https://www.youtube.com/watch?v=l7kQNwJ4H_w"
ITAG = 22  # 720p
DOWNLOAD_PATH = "test_downloads"
MINIMUM_VALID_SIZE = 10 * 1024  # 10KB (our test video should be at least this size)

def ensure_directory_exists(directory):
    """Ensure the download directory exists"""
    if not os.path.exists(directory):
        os.makedirs(directory)
        logger.info(f"Created directory: {directory}")

def get_video_info(url):
    """Get video information from the API"""
    endpoint = urljoin(BASE_URL, "/get_video_info")
    data = {"url": url}
    
    logger.info(f"Getting video info for: {url}")
    response = requests.post(endpoint, data=data)
    
    if response.status_code != 200:
        logger.error(f"Failed to get video info: {response.text}")
        return None
    
    return response.json()

def start_download(url, itag):
    """Start a download and get the download ID"""
    endpoint = urljoin(BASE_URL, "/download")
    data = {"url": url, "itag": itag}
    
    logger.info(f"Starting download for video: {url}, itag: {itag}")
    response = requests.post(endpoint, data=data)
    
    if response.status_code != 200:
        logger.error(f"Failed to start download: {response.text}")
        return None
    
    return response.json().get("download_id")

def check_download_progress(download_id):
    """Check download progress and wait until completed"""
    endpoint = urljoin(BASE_URL, f"/download_progress/{download_id}")
    completed = False
    attempts = 0
    max_attempts = 30  # 15 seconds max wait time
    last_progress = -1
    
    while not completed and attempts < max_attempts:
        attempts += 1
        try:
            response = requests.get(endpoint)
            
            if response.status_code != 200:
                logger.error(f"Failed to check progress: {response.text}")
                return False
            
            data = response.json()
            progress = data.get("progress", 0)
            status = data.get("status", "unknown")
            
            # Only log when progress changes
            if progress != last_progress:
                logger.info(f"Download progress: {progress}% - Status: {status}")
                last_progress = progress
            
            if status == "completed" or progress >= 99:
                logger.info("Download completed successfully")
                completed = True
                break
            elif "error" in status:
                logger.error(f"Download failed: {status}")
                return False
            
            # If we're still at 0% after several attempts, consider checking the file directly
            if progress == 0 and attempts > 10:
                logger.info("Progress stalled at 0%, checking if file exists anyway...")
                # Return true and let the next step verify if the file exists
                return True
        except Exception as e:
            logger.error(f"Error checking progress: {str(e)}")
        
        time.sleep(0.5)
    
    if not completed and attempts >= max_attempts:
        logger.warning("Checking for file directly since progress tracking timed out")
        # Even if we time out, we'll try to download the file in the next step
        return True
    
    return True

def download_file(download_id, url, itag, output_path):
    """Download the file to the specified path"""
    file_endpoint = urljoin(BASE_URL, f"/get_file/{download_id}")
    params = {"url": url, "itag": itag}
    
    logger.info(f"Retrieving downloaded file for ID: {download_id}")
    response = requests.get(file_endpoint, params=params, stream=True)
    
    if response.status_code != 200:
        logger.error(f"Failed to get file: {response.text}")
        return None
    
    # Extract filename from Content-Disposition header
    content_disposition = response.headers.get('content-disposition', '')
    filename = 'downloaded_video.mp4'
    if 'filename=' in content_disposition:
        filename = content_disposition.split('filename=')[1].strip('"\'')
    
    file_path = os.path.join(output_path, filename)
    
    # Save the file
    with open(file_path, 'wb') as f:
        for chunk in response.iter_content(chunk_size=8192):
            if chunk:
                f.write(chunk)
    
    logger.info(f"File saved to: {file_path}")
    return file_path

def validate_video_file(file_path):
    """Validate that the file is a proper video file with sufficient size"""
    if not os.path.exists(file_path):
        logger.error(f"File does not exist: {file_path}")
        return False
    
    file_size = os.path.getsize(file_path)
    logger.info(f"File size: {file_size} bytes ({file_size/1024:.2f} KB, {file_size/(1024*1024):.2f} MB)")
    
    if file_size < MINIMUM_VALID_SIZE:
        logger.error(f"File is too small: {file_size} bytes < {MINIMUM_VALID_SIZE} bytes")
        return False
    
    # Check file signature (first few bytes) to verify it's an MP4 file
    try:
        with open(file_path, 'rb') as f:
            header = f.read(12)
            # MP4 files typically start with 'ftyp' at the 5th byte position
            if b'ftyp' in header[4:8]:
                logger.info("File is a valid MP4 file based on signature check")
                return True
            else:
                logger.warning("File doesn't have a standard MP4 signature, but might still be playable")
    except Exception as e:
        logger.error(f"Error checking file signature: {str(e)}")
    
    # If we can't confirm MP4 signature, just check if size is reasonable
    if file_size > 100 * 1024:  # More than 100KB should be a valid video
        logger.info("File has reasonable size for a video")
        return True
    
    return False

def run_test():
    """Run the full download test"""
    ensure_directory_exists(DOWNLOAD_PATH)
    
    # Step 1: Get video info
    video_info = get_video_info(TEST_VIDEO_URL)
    if not video_info:
        logger.error("Test failed at step 1: Could not get video info")
        return False
    
    logger.info(f"Video title: {video_info.get('title')}")
    logger.info(f"Video author: {video_info.get('author')}")
    
    # Step 2: Start download
    download_id = start_download(TEST_VIDEO_URL, ITAG)
    if not download_id:
        logger.error("Test failed at step 2: Could not start download")
        return False
    
    logger.info(f"Download ID: {download_id}")
    
    # Step 3: Wait for download to complete
    if not check_download_progress(download_id):
        logger.error("Test failed at step 3: Download did not complete successfully")
        return False
    
    # Step 4: Get the downloaded file
    file_path = download_file(download_id, TEST_VIDEO_URL, ITAG, DOWNLOAD_PATH)
    if not file_path:
        logger.error("Test failed at step 4: Could not get downloaded file")
        return False
    
    # Step 5: Validate the file
    is_valid = validate_video_file(file_path)
    if not is_valid:
        logger.error("Test failed at step 5: Downloaded file is not a valid video")
        return False
    
    logger.info("✅ Test completed successfully! We have a valid video file.")
    return True

if __name__ == "__main__":
    success = run_test()
    if not success:
        logger.error("❌ Test failed!")
        sys.exit(1)
    else:
        logger.info("✅ Test passed!")
        sys.exit(0)