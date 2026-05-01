#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FastAPI Backend Server for URL Downloader

Provides REST API endpoints for:
- Video information extraction
- Video/Audio downloading
- File serving

Run with: uvicorn server:app --reload --host 0.0.0.0 --port 8000
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, HttpUrl
from typing import Optional, Literal
import uvicorn
import os
from pathlib import Path

# Add ffmpeg and deno to PATH if installed via winget
def setup_paths():
    local_app_data = os.environ.get('LOCALAPPDATA', '')
    user_profile = os.environ.get('USERPROFILE', '')

    # FFmpeg path (winget installation)
    ffmpeg_base = Path(local_app_data) / 'Microsoft/WinGet/Packages'
    for pkg_dir in ffmpeg_base.glob('Gyan.FFmpeg*'):
        for ffmpeg_dir in pkg_dir.glob('ffmpeg-*/bin'):
            if ffmpeg_dir.exists():
                os.environ['PATH'] = str(ffmpeg_dir) + os.pathsep + os.environ.get('PATH', '')
                break

    # Deno path
    deno_path = Path(user_profile) / '.deno/bin'
    if deno_path.exists():
        os.environ['PATH'] = str(deno_path) + os.pathsep + os.environ.get('PATH', '')

setup_paths()

from downloader import (
    get_video_info,
    download_video,
    download_audio,
    search_videos,
    cleanup_old_files,
    DOWNLOAD_DIR,
)

# Initialize FastAPI app
app = FastAPI(
    title="URL Downloader API",
    description="Backend API for downloading videos and audio from various platforms",
    version="1.0.0"
)

# CORS middleware - allow requests from any origin (Vercel, localhost, etc.)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Disposition"],
)

# Request models
class VideoInfoRequest(BaseModel):
    url: str

class DownloadRequest(BaseModel):
    url: str
    format: Literal['mp4', 'mp3'] = 'mp4'
    quality: str = '1080'  # For video: 1080, 720, 480, etc. For audio: 320, 192, 128

class SearchRequest(BaseModel):
    query: str
    max_results: int = 10


# Response models
class VideoInfoResponse(BaseModel):
    success: bool
    title: Optional[str] = None
    description: Optional[str] = None
    uploader: Optional[str] = None
    duration: Optional[int] = None
    view_count: Optional[int] = None
    like_count: Optional[int] = None
    thumbnail: Optional[str] = None
    webpage_url: Optional[str] = None
    available_qualities: Optional[dict] = None
    error: Optional[str] = None


# Store download tasks
download_tasks = {}


@app.get("/")
async def root():
    """Root endpoint - API information."""
    return {
        "message": "URL Downloader API",
        "version": "1.0.0",
        "endpoints": {
            "POST /api/video-info": "Get video information",
            "POST /api/download": "Download video or audio",
            "GET /api/download/{task_id}": "Check download status",
            "GET /api/file/{filename}": "Download file",
            "POST /api/search": "Search for videos",
            "GET /api/health": "Health check",
        }
    }


@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "url-downloader"}


@app.post("/api/video-info", response_model=VideoInfoResponse)
async def video_info(request: VideoInfoRequest):
    """
    Get video information without downloading.

    Args:
        request: VideoInfoRequest with URL

    Returns:
        Video metadata including title, description, available qualities
    """
    try:
        info = get_video_info(request.url)
        return info
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/download")
async def download(request: DownloadRequest, background_tasks: BackgroundTasks):
    """
    Download video or audio.

    Args:
        request: DownloadRequest with URL, format, and quality

    Returns:
        Download task ID and status
    """
    import uuid

    # Generate task ID
    task_id = str(uuid.uuid4())

    # Initialize task status
    download_tasks[task_id] = {
        'status': 'pending',
        'progress': 0,
        'url': request.url,
        'format': request.format,
        'quality': request.quality,
        'file_path': None,
        'filename': None,
        'error': None,
    }

    # Start download in background (sync function for background tasks)
    def do_download():
        try:
            download_tasks[task_id]['status'] = 'downloading'

            if request.format == 'mp4':
                result = download_video(request.url, request.quality)
            else:
                result = download_audio(request.url, request.quality)

            if result.get('success'):
                download_tasks[task_id].update({
                    'status': 'completed',
                    'progress': 100,
                    'file_path': result['file_path'],
                    'filename': result['filename'],
                    'file_size': result.get('file_size_mb', 0),
                    'title': result.get('title', 'Unknown'),
                })
            else:
                download_tasks[task_id].update({
                    'status': 'failed',
                    'error': result.get('error', 'Unknown error'),
                })
        except Exception as e:
            download_tasks[task_id].update({
                'status': 'failed',
                'error': str(e),
            })

    # Run download in background
    background_tasks.add_task(do_download)

    return {
        'task_id': task_id,
        'status': 'pending',
        'message': 'Download started',
    }


@app.get("/api/download/{task_id}")
async def download_status(task_id: str):
    """
    Check download task status.

    Args:
        task_id: Task ID from download endpoint

    Returns:
        Task status and progress
    """
    if task_id not in download_tasks:
        raise HTTPException(status_code=404, detail="Task not found")

    task = download_tasks[task_id]

    return {
        'task_id': task_id,
        'status': task['status'],
        'progress': task['progress'],
        'filename': task.get('filename'),
        'file_size': task.get('file_size'),
        'title': task.get('title'),
        'error': task.get('error'),
    }


@app.get("/api/file/{filename}")
async def download_file(filename: str):
    """
    Download a file.

    Args:
        filename: Name of the file to download

    Returns:
        File response
    """
    file_path = DOWNLOAD_DIR / filename

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")

    # Security check - ensure file is in DOWNLOAD_DIR
    try:
        file_path = file_path.resolve()
        DOWNLOAD_DIR.resolve()

        if not str(file_path).startswith(str(DOWNLOAD_DIR.resolve())):
            raise HTTPException(status_code=403, detail="Access denied")
    except Exception as e:
        raise HTTPException(status_code=403, detail="Invalid file path")

    return FileResponse(
        path=file_path,
        filename=filename,
        media_type='application/octet-stream'
    )


@app.post("/api/search")
async def search(request: SearchRequest):
    """
    Search for videos on YouTube.

    Args:
        request: SearchRequest with query

    Returns:
        Search results
    """
    try:
        results = search_videos(request.query, request.max_results)
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/cleanup")
async def cleanup():
    """
    Clean up old downloaded files (older than 24 hours).

    Returns:
        Cleanup status
    """
    try:
        cleanup_old_files(max_age_hours=24)
        return {'success': True, 'message': 'Cleanup completed'}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Startup event
@app.on_event("startup")
async def startup_event():
    """Initialize on startup."""
    # Ensure download directory exists
    DOWNLOAD_DIR.mkdir(exist_ok=True)
    print(f"Download directory: {DOWNLOAD_DIR.absolute()}")


if __name__ == "__main__":
    uvicorn.run(
        "server:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
