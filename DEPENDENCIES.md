# DY - Dependencies

This document lists all the dependencies required for the DY YouTube Downloader application.

## Core Dependencies

- **flask** - Web framework for building the application
- **flask-sqlalchemy** - ORM for database operations
- **gunicorn** - WSGI HTTP Server for UNIX
- **email-validator** - Email validation library
- **psycopg2-binary** - PostgreSQL adapter
- **pytube** - YouTube download library (fallback)
- **requests** - HTTP library for making requests
- **trafilatura** - Web scraping and text extraction
- **werkzeug** - WSGI utility library
- **yt-dlp** - YouTube download library (primary)

## Secondary Dependencies

- **beautifulsoup4** - HTML parsing library
- **lxml** - XML and HTML processing library
- **certifi** - Root certificates for validating SSL certificates
- **charset-normalizer** - Character encoding detector
- **click** - Command-line interface creation kit
- **idna** - Internationalized Domain Names support
- **itsdangerous** - Security-related helpers
- **Jinja2** - Template engine
- **MarkupSafe** - Escapes characters for HTML safety
- **mutagen** - Audio metadata handling
- **pycryptodomex** - Cryptographic library
- **urllib3** - HTTP client for Python
- **websockets** - WebSocket implementation

## Installation

To install these dependencies, you would typically use:

```bash
pip install flask flask-sqlalchemy gunicorn email-validator psycopg2-binary pytube requests trafilatura werkzeug yt-dlp beautifulsoup4 lxml
```

Or, if a requirements.txt file is available:

```bash
pip install -r requirements.txt
```

## Version Compatibility

This application has been tested with the following versions:

- Python 3.8+
- yt-dlp 2023.11.16
- Flask 2.3.3

For optimal performance and compatibility, it's recommended to use these versions or newer.

## System Dependencies

In addition to Python packages, the application requires:

- **ffmpeg** - For audio extraction and format conversion
- **Python 3.8+** - Base programming language

## Development Dependencies (Optional)

For development purposes, these additional packages may be useful:

- **pytest** - Testing framework
- **black** - Code formatter
- **flake8** - Linter
- **pre-commit** - Git hook scripts

## Updating Dependencies

YouTube frequently updates their interface, which might break downloading functionality. To ensure the application continues working properly, regularly update yt-dlp:

```bash
pip install -U yt-dlp
```