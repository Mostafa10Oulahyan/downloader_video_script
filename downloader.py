#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
URL Downloader Backend - Python Script using yt-dlp

This script handles:
1. Video/Audio information extraction
2. Direct downloading (MP4/MP3)
3. File serving to frontend

Usage:
    python downloader.py --url "https://youtube.com/watch?v=..." --format mp4 --quality 1080p
"""

import sys
import os
import json
import argparse
import subprocess
from pathlib import Path

# Configure cookies if file exists
COOKIES_FILE = Path('cookies.txt')
COOKIE_OPTS = {'cookiefile': str(COOKIES_FILE)} if COOKIES_FILE.exists() else {}
from datetime import datetime
from typing import Dict, Any, Optional, List

try:
    import yt_dlp
except ImportError:
    print("ERROR: yt-dlp not installed. Run: pip install yt-dlp")
    sys.exit(1)


# Configuration
DOWNLOAD_DIR = Path("downloads")
TEMP_DIR = Path("temp")
MAX_FILE_SIZE_MB = 500  # Maximum file size to download


def ensure_directories():
    """Create necessary directories."""
    DOWNLOAD_DIR.mkdir(exist_ok=True)
    TEMP_DIR.mkdir(exist_ok=True)


def get_video_info(url: str) -> Dict[str, Any]:
    """
    Extract video information without downloading.

    Args:
        url: Video URL

    Returns:
        Dictionary containing video metadata
    """
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'extract_flat': False,
        **COOKIE_OPTS,
}

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)

            # Extract available formats
            formats = []
            if 'formats' in info:
                for f in info['formats']:
                    if f.get('vcodec') != 'none' or f.get('acodec') != 'none':
                        formats.append({
                            'format_id': f.get('format_id'),
                            'ext': f.get('ext'),
                            'quality': f.get('format_note', 'unknown'),
                            'resolution': f.get('resolution'),
                            'filesize': f.get('filesize'),
                            'vcodec': f.get('vcodec'),
                            'acodec': f.get('acodec'),
                            'fps': f.get('fps'),
                            'tbr': f.get('tbr'),  # Total bitrate
                        })

            return {
                'success': True,
                'title': info.get('title', 'Unknown'),
                'description': info.get('description', ''),
                'uploader': info.get('uploader', 'Unknown'),
                'duration': info.get('duration', 0),
                'view_count': info.get('view_count', 0),
                'like_count': info.get('like_count', 0),
                'upload_date': info.get('upload_date', ''),
                'thumbnail': info.get('thumbnail', ''),
                'webpage_url': info.get('webpage_url', url),
                'extractor': info.get('extractor', 'unknown'),
                'formats': formats,
                'available_qualities': get_available_qualities(formats),
            }
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
        }


def get_available_qualities(formats: List[Dict]) -> Dict[str, List[str]]:
    """Extract unique quality options from formats."""
    video_qualities = set()
    audio_qualities = set()

    for f in formats:
        if f.get('vcodec') and f['vcodec'] != 'none':
            resolution = f.get('resolution', '')
            if resolution and 'x' in resolution:
                height = resolution.split('x')[1]
                if height.isdigit():
                    video_qualities.add(f"{height}p")

        if f.get('acodec') and f['acodec'] != 'none':
            tbr = f.get('tbr')
            if tbr:
                audio_qualities.add(f"{int(tbr)}kbps")

    return {
        'video': sorted(list(video_qualities), key=lambda x: int(x.replace('p', '')), reverse=True),
        'audio': sorted(list(audio_qualities), key=lambda x: int(x.replace('kbps', '')), reverse=True),
    }


def download_video(url: str, quality: str = '1080', output_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Download video in MP4 format.

    Args:
        url: Video URL
        quality: Quality (e.g., '1080', '720', '480')
        output_path: Optional custom output path

    Returns:
        Dictionary with download status and file path
    """
    ensure_directories()

    # Generate output filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    if output_path is None:
        output_template = str(DOWNLOAD_DIR / f"{timestamp}_%(title)s.%(ext)s")
    else:
        output_template = output_path

    ydl_opts = {
        **COOKIE_OPTS,
        'format': f'bestvideo[height<={quality}]+bestaudio/best[height<={quality}]/bestvideo+bestaudio/best',
        'outtmpl': output_template,
        'merge_output_format': 'mp4',
        'postprocessors': [{
            'key': 'FFmpegVideoConvertor',
            'preferedformat': 'mp4',
        }],
        'quiet': False,
        'no_warnings': False,
        'progress_hooks': [progress_hook],
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)

            # Find the downloaded file
            downloaded_file = ydl.prepare_filename(info)

            # Check if file exists
            if not os.path.exists(downloaded_file):
                # Try with .mp4 extension
                downloaded_file = os.path.splitext(downloaded_file)[0] + '.mp4'

            if os.path.exists(downloaded_file):
                file_size = os.path.getsize(downloaded_file)

                return {
                    'success': True,
                    'file_path': downloaded_file,
                    'filename': os.path.basename(downloaded_file),
                    'file_size': file_size,
                    'file_size_mb': round(file_size / (1024 * 1024), 2),
                    'title': info.get('title', 'Unknown'),
                    'duration': info.get('duration', 0),
                }
            else:
                return {
                    'success': False,
                    'error': 'Downloaded file not found',
                }
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
        }


def download_audio(url: str, quality: str = '320', output_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Download audio in MP3 format.

    Args:
        url: Video URL
        quality: Audio quality in kbps (e.g., '320', '256', '192', '128')
        output_path: Optional custom output path

    Returns:
        Dictionary with download status and file path
    """
    ensure_directories()

    # Generate output filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    if output_path is None:
        output_template = str(DOWNLOAD_DIR / f"{timestamp}_%(title)s.%(ext)s")
    else:
        output_template = output_path

    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': output_template,
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': quality,
            **COOKIE_OPTS,
}],
        'quiet': False,
        'no_warnings': False,
        'progress_hooks': [progress_hook],
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)

            # Find the downloaded file (it should be .mp3)
            downloaded_file = ydl.prepare_filename(info)
            downloaded_file = os.path.splitext(downloaded_file)[0] + '.mp3'

            if os.path.exists(downloaded_file):
                file_size = os.path.getsize(downloaded_file)

                return {
                    'success': True,
                    'file_path': downloaded_file,
                    'filename': os.path.basename(downloaded_file),
                    'file_size': file_size,
                    'file_size_mb': round(file_size / (1024 * 1024), 2),
                    'title': info.get('title', 'Unknown'),
                    'duration': info.get('duration', 0),
                }
            else:
                return {
                    'success': False,
                    'error': 'Downloaded file not found',
                }
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
        }


def progress_hook(d):
    """Progress hook for yt-dlp downloads."""
    if d['status'] == 'downloading':
        percent = d.get('_percent_str', '0%')
        speed = d.get('_speed_str', 'N/A')
        eta = d.get('_eta_str', 'N/A')
        print(f"\rDownloading: {percent} | Speed: {speed} | ETA: {eta}", end='', flush=True)
    elif d['status'] == 'finished':
        print("\nDownload complete! Processing...")


def search_videos(query: str, max_results: int = 10) -> Dict[str, Any]:
    """
    Search for videos on YouTube.

    Args:
        query: Search query
        max_results: Maximum number of results

    Returns:
        Dictionary with search results
    """
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'extract_flat': True,
        'default_search': 'ytsearch',
        **COOKIE_OPTS,
}

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            result = ydl.extract_info(f"ytsearch{max_results}:{query}", download=False)

            videos = []
            if 'entries' in result:
                for entry in result['entries']:
                    videos.append({
                        'title': entry.get('title', 'Unknown'),
                        'url': entry.get('url', ''),
                        'id': entry.get('id', ''),
                        'duration': entry.get('duration', 0),
                        'uploader': entry.get('uploader', 'Unknown'),
                        'thumbnail': entry.get('thumbnail', ''),
                    })

            return {
                'success': True,
                'query': query,
                'results': videos,
            }
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
        }


def cleanup_old_files(max_age_hours: int = 24):
    """
    Delete old downloaded files.

    Args:
        max_age_hours: Maximum age in hours before deletion
    """
    import time

    current_time = time.time()
    max_age_seconds = max_age_hours * 3600

    for directory in [DOWNLOAD_DIR, TEMP_DIR]:
        if not directory.exists():
            continue

        for file_path in directory.glob('*'):
            if file_path.is_file():
                file_age = current_time - file_path.stat().st_mtime
                if file_age > max_age_seconds:
                    try:
                        file_path.unlink()
                        print(f"Deleted old file: {file_path.name}")
                    except Exception as e:
                        print(f"Failed to delete {file_path.name}: {e}")


def main():
    """CLI interface for the downloader."""
    parser = argparse.ArgumentParser(description='URL Downloader using yt-dlp')
    parser.add_argument('--url', type=str, help='Video URL')
    parser.add_argument('--action', type=str, choices=['info', 'download-video', 'download-audio', 'search', 'cleanup'],
                        default='info', help='Action to perform')
    parser.add_argument('--format', type=str, choices=['mp4', 'mp3'], default='mp4', help='Output format')
    parser.add_argument('--quality', type=str, default='1080', help='Quality (1080, 720, 480 for video; 320, 192, 128 for audio)')
    parser.add_argument('--query', type=str, help='Search query (for search action)')
    parser.add_argument('--output', type=str, help='Output file path')
    parser.add_argument('--json', action='store_true', help='Output in JSON format')

    args = parser.parse_args()

    # Perform action
    result = None

    if args.action == 'info':
        if not args.url:
            print("ERROR: --url is required for info action")
            sys.exit(1)
        result = get_video_info(args.url)

    elif args.action == 'download-video':
        if not args.url:
            print("ERROR: --url is required for download-video action")
            sys.exit(1)
        result = download_video(args.url, args.quality, args.output)

    elif args.action == 'download-audio':
        if not args.url:
            print("ERROR: --url is required for download-audio action")
            sys.exit(1)
        result = download_audio(args.url, args.quality, args.output)

    elif args.action == 'search':
        if not args.query:
            print("ERROR: --query is required for search action")
            sys.exit(1)
        result = search_videos(args.query)

    elif args.action == 'cleanup':
        cleanup_old_files()
        result = {'success': True, 'message': 'Cleanup completed'}

    # Output result
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        if result:
            print("\n" + "="*60)
            if result.get('success'):
                print("SUCCESS!")
                for key, value in result.items():
                    if key != 'success' and key != 'formats':
                        print(f"  {key}: {value}")
            else:
                print("FAILED!")
                print(f"  Error: {result.get('error', 'Unknown error')}")
            print("="*60)


if __name__ == '__main__':
    main()
