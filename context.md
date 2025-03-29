# DY Context & Dependencies

## Overview
DY (YouTube Downloader) requires ffmpeg for media processing. This document explains what ffmpeg does and how to install it.

## What is ffmpeg?
ffmpeg is a powerful multimedia framework that:
- Converts between media formats
- Extracts audio from videos
- Processes video/audio streams
- Adds metadata and thumbnails
- Handles various media formats

## Why DY needs ffmpeg
DY uses ffmpeg for:
1. Audio extraction (for MP3 downloads)
2. Format conversion
3. Stream merging
4. Metadata embedding
5. Thumbnail processing

## Installation Methods

### Using Homebrew (macOS)
```bash
brew install ffmpeg
```

### Using APT (Ubuntu/Debian)
```bash
sudo apt update
sudo apt install ffmpeg
```

### Using DNF (Fedora)
```bash
sudo dnf install ffmpeg
```

### Using Pacman (Arch Linux)
```bash
sudo pacman -S ffmpeg
```

## Verifying Installation
After installation, verify ffmpeg is working:
```bash
ffmpeg -version
```

## Common Operations in DY
1. **Audio Extraction**: 
   ```bash
   ffmpeg -i video.mp4 -vn audio.mp3
   ```

2. **Format Conversion**:
   ```bash
   ffmpeg -i input.webm output.mp4
   ```

3. **Stream Merging**:
   ```bash
   ffmpeg -i video.mp4 -i audio.m4a -c copy output.mp4
   ```

## Troubleshooting
If you see errors like:
```
ERROR: ffprobe/ffmpeg not found. Please install or provide the path
```
This means ffmpeg is not installed or not in your system PATH.

## Additional Resources
- [FFmpeg Official Documentation](https://ffmpeg.org/documentation.html)
- [FFmpeg Wiki](https://trac.ffmpeg.org/wiki)