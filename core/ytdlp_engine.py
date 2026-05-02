import os
import yt_dlp
import asyncio
import uuid
from core.progress import ProgressUpdater

def yt_dlp_download_sync(url: str, quality: str, updater: ProgressUpdater, tmp_dir: str, cookies_txt: str = None):
    format_map = {
        "best": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best/all",
        "720p": "bestvideo[ext=mp4][height<=720]+bestaudio[ext=m4a]/best[ext=mp4][height<=720]/best/all",
        "480p": "bestvideo[ext=mp4][height<=480]+bestaudio[ext=m4a]/best[ext=mp4][height<=480]/best/all",
        "360p": "bestvideo[ext=mp4][height<=360]+bestaudio[ext=m4a]/best[ext=mp4][height<=360]/best/all",
        "audio": "bestaudio/best"
    }

    ydl_format = format_map.get(quality, format_map["best"])
    def my_hook(d):
        if d['status'] == 'downloading':
            try:
                percent_str = d.get('_percent_str', '0%').replace('\x1b[0;94m', '').replace('\x1b[0m', '').strip()
                speed_str = d.get('_speed_str', 'N/A').replace('\x1b[0;32m', '').replace('\x1b[0m', '').strip()
                eta_str = d.get('_eta_str', 'N/A').replace('\x1b[0;33m', '').replace('\x1b[0m', '').strip()
                percent = float(percent_str.replace('%', ''))
                updater.update_sync(percent, speed_str, eta_str)
            except Exception:
                pass

    ydl_opts = {
        'format': ydl_format,
        'outtmpl': os.path.join(tmp_dir, '%(title)s.%(ext)s'),
        'merge_output_format': 'mp4' if quality != "audio" else None,
        'postprocessors':[{'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3'}] if quality == "audio" else [],
        'progress_hooks':[my_hook],
        'quiet': True,
        'nocheckcertificate': True,

        'extractor_args': {'youtube': {'player_client':['web']}}
    }

    if cookies_txt:
        ydl_opts['cookiefile'] = cookies_txt

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        filename = ydl.prepare_filename(info)
        if quality == "audio":
            filename = filename.rsplit('.', 1)[0] + '.mp3'
        return filename

async def download_media(url: str, quality: str, updater: ProgressUpdater, user_cookies: str = None):
    tmp_dir = "tmp_downloads"
    os.makedirs(tmp_dir, exist_ok=True)

    cookies_file = None
    if user_cookies:
        cookies_file = os.path.join(tmp_dir, f"cookies_{uuid.uuid4().hex[:6]}.txt")
        with open(cookies_file, "w", encoding="utf-8") as f:
            f.write(user_cookies)

    loop = asyncio.get_running_loop()
    try:
        downloaded_file = await loop.run_in_executor(
            None, yt_dlp_download_sync, url, quality, updater, tmp_dir, cookies_file
        )
    finally:
        if cookies_file and os.path.exists(cookies_file):
            os.remove(cookies_file)

    return downloaded_file