# youtubedownloader

Making this for edu purposes 

Looks like there is already a good tool available : https://github.com/dinesh-coderepo/youtube-dl-gui

# DY - Advanced YouTube Downloader

DY is a powerful, reliable, and stylish web application for downloading YouTube videos in various quality options, including audio-only formats. Built with Flask and yt-dlp, this application ensures downloads work "at any cost" through multiple fallback mechanisms.

**Created by: Maluchuru Sai Dinesh Reddy** with the help of AI code generation.

![DY Logo](static/images/logo.png)

## Features

- **High-quality downloads**: Get the best quality videos from YouTube
- **Multiple formats**: Choose from various resolutions or audio-only options
- **Custom save locations**: Select where to save your downloads
- **Guaranteed downloads**: Multiple fallback systems ensure you get your content
- **Beautiful UI**: Modern, glassy interface with animations and visual feedback
- **Ultra-reliable**: Uses yt-dlp for maximum compatibility with YouTube

## Screenshots

![Main Interface](static/images/screenshot1.jpg)
![Download in Progress](static/images/screenshot2.jpg)

## Getting Started

### Prerequisites

- Python 3.8+
- Flask
- yt-dlp
- Other dependencies listed in `requirements.txt`

### Installation

1. Clone the repository
```bash
git clone https://github.com/yourusername/dy-youtube-downloader.git
cd dy-youtube-downloader
```

2. Install required packages
```bash
pip install -r requirements.txt
```

3. Run the application
```bash
python main.py
```

4. Open a browser and navigate to `http://localhost:5000`

## Usage

1. Enter a valid YouTube URL in the input field
2. Click "Fetch Video" to load video information
3. Select your preferred quality/format from the dropdown
4. Choose a save location
5. Click "Download" and wait for the download to complete
6. Click the download link to save the file to your device

## Documentation

For more detailed information, check out:

- [User Guide](USEME.md) - Detailed instructions for end users
- [Technical Documentation](TECHNICAL.md) - Architecture and implementation details

## Built With

- [Flask](https://flask.palletsprojects.com/) - The web framework used
- [yt-dlp](https://github.com/yt-dlp/yt-dlp) - YouTube download library
- [Bootstrap](https://getbootstrap.com/) - Frontend styling
- [jQuery](https://jquery.com/) - JavaScript library for DOM manipulation

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- The yt-dlp team for their excellent YouTube download library
- Bootstrap team for the responsive UI framework
- Inspired by [youtube-dl-gui](https://github.com/StefanLobbenmeier/youtube-dl-gui)
- Everyone who contributed to this project directly or indirectly