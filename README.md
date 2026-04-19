# URL Downloader - Python Backend Setup

This backend provides REST API endpoints for downloading videos and audio from various platforms using yt-dlp.

## Features
- **Video Information Extraction**: Get title, description, thumbnail, duration, views, etc.
- **Direct Download**: Download videos (MP4) or audio (MP3) in various qualities
- **Search**: Search for videos on YouTube
- **File Serving**: Download completed files through the API
- **Auto Cleanup**: Automatically delete old files after 24 hours

## Installation

### Prerequisites
1. **Python 3.8+** installed
2. **ffmpeg** installed (required for yt-dlp conversions)

#### Install ffmpeg:
```bash
# Windows (using winget)
winget install ffmpeg

# macOS (using Homebrew)
brew install ffmpeg

# Linux (Ubuntu/Debian)
sudo apt install ffmpeg

# Linux (Fedora/RHEL)
sudo dnf install ffmpeg
```

### Setup Steps

1. **Navigate to backend directory**:
```bash
cd python_backend
```

2. **Create virtual environment** (recommended):
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS/Linux
python3 -m venv venv
source venv/bin/activate
```

3. **Install dependencies**:
```bash
pip install -r requirements.txt
```

4. **Verify installation**:
```bash
# Check yt-dlp
yt-dlp --version

# Check ffmpeg
ffmpeg -version
```

## Usage

### Running the Server

**Development mode** (with auto-reload):
```bash
python server.py
```

Or using uvicorn directly:
```bash
uvicorn server:app --reload --host 0.0.0.0 --port 8000
```

**Production mode**:
```bash
uvicorn server:app --host 0.0.0.0 --port 8000 --workers 4
```

The server will start on `http://localhost:8000`

### API Documentation

Once the server is running, visit:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### API Endpoints

#### 1. Get Video Information
```bash
POST http://localhost:8000/api/video-info
Content-Type: application/json

{
  "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
}
```

**Response**:
```json
{
  "success": true,
  "title": "Video Title",
  "description": "Video description...",
  "uploader": "Channel Name",
  "duration": 213,
  "view_count": 1000000,
  "like_count": 50000,
  "thumbnail": "https://...",
  "available_qualities": {
    "video": ["2160p", "1440p", "1080p", "720p", "480p", "360p"],
    "audio": ["320kbps", "192kbps", "128kbps"]
  }
}
```

#### 2. Download Video/Audio
```bash
POST http://localhost:8000/api/download
Content-Type: application/json

{
  "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
  "format": "mp4",
  "quality": "1080"
}
```

**Response**:
```json
{
  "task_id": "123e4567-e89b-12d3-a456-426614174000",
  "status": "pending",
  "message": "Download started"
}
```

#### 3. Check Download Status
```bash
GET http://localhost:8000/api/download/{task_id}
```

**Response**:
```json
{
  "task_id": "123e4567-e89b-12d3-a456-426614174000",
  "status": "completed",
  "progress": 100,
  "filename": "20240105_120000_Video_Title.mp4",
  "file_size": 25.5,
  "title": "Video Title"
}
```

#### 4. Download File
```bash
GET http://localhost:8000/api/file/{filename}
```

This returns the actual file for download.

#### 5. Search Videos
```bash
POST http://localhost:8000/api/search
Content-Type: application/json

{
  "query": "cats playing piano",
  "max_results": 10
}
```

### CLI Usage (standalone)

You can also use the downloader script directly:

**Get video info**:
```bash
python downloader.py --url "https://youtube.com/watch?v=..." --action info --json
```

**Download video**:
```bash
python downloader.py --url "https://youtube.com/watch?v=..." --action download-video --quality 1080
```

**Download audio**:
```bash
python downloader.py --url "https://youtube.com/watch?v=..." --action download-audio --quality 320
```

**Search videos**:
```bash
python downloader.py --action search --query "funny cats" --json
```

**Cleanup old files**:
```bash
python downloader.py --action cleanup
```

## Configuration

### Download Directory
By default, files are saved to `./downloads/`. You can modify this in `downloader.py`:

```python
DOWNLOAD_DIR = Path("downloads")
```

### CORS Settings
To allow requests from your Next.js frontend, the server is configured to accept requests from:
- http://localhost:3000
- http://localhost:3001
- http://127.0.0.1:3000
- http://127.0.0.1:3001

Modify `server.py` to add more origins if needed.

### File Auto-Cleanup
Downloaded files are automatically deleted after 24 hours. Adjust in the cleanup function:

```python
cleanup_old_files(max_age_hours=24)
```

## Supported Platforms

yt-dlp supports 1000+ sites including:
- YouTube
- TikTok
- Instagram
- Twitter/X
- Facebook
- Vimeo
- SoundCloud
- Twitch
- Reddit
- Dailymotion
- Bilibili
- And many more...

Full list: https://github.com/yt-dlp/yt-dlp/blob/master/supportedsites.md

## Troubleshooting

### Error: "yt-dlp not installed"
```bash
pip install yt-dlp
```

### Error: "ffmpeg not found"
Install ffmpeg using the instructions above.

### Port already in use
Change the port in `server.py`:
```python
uvicorn.run("server:app", host="0.0.0.0", port=8001)
```

### Download fails with "Unable to extract"
Some sites require cookies or authentication. Use yt-dlp's `--cookies` option.

### Slow downloads
- Check your internet connection
- Some platforms rate-limit downloads
- Try a different quality/format

## Security Notes

1. **File Access**: The server validates file paths to prevent directory traversal attacks
2. **CORS**: Only allowed origins can access the API
3. **File Cleanup**: Old files are automatically deleted to save disk space
4. **No Authentication**: This server has no authentication. Add authentication before deploying to production.

## License

This project uses yt-dlp which is licensed under the Unlicense.
