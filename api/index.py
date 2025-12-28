from __future__ import annotations

import re
from typing import Literal, Optional

import httpx
import requests
import yt_dlp
from fastapi import FastAPI, Query, Response, HTTPException
from fastapi.responses import JSONResponse, RedirectResponse, StreamingResponse

app = FastAPI()

# -----------------------------
# Helpers
# -----------------------------
MEDIA_TYPE = Literal["video", "audio"]

DEFAULT_HEADERS = {
    # A fairly common desktop UA helps with some extractors
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9,ar;q=0.8",
}

def _safe_filename(name: str, ext: str) -> str:
    name = (name or "download").strip()
    name = re.sub(r'[\\/:*?"<>|]+', "_", name)
    name = re.sub(r"\s+", " ", name).strip()
    if not name:
        name = "download"
    if ext and not ext.startswith("."):
        ext = "." + ext
    return f"{name}{ext}"

def _ydl_opts() -> dict:
    # NOTE: We do NOT write to disk. We only extract direct CDN URLs.
    # We also avoid formats that require server-side merging (ffmpeg not available on Vercel).
    return {
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
        "nocheckcertificate": True,
        "geo_bypass": True,
        "socket_timeout": 15,
        "http_headers": DEFAULT_HEADERS,
        # Some sites need this to avoid slow checks
        "consoletitle": False,
    }

def _is_youtube(url: str) -> bool:
    u = url.lower()
    return "youtube.com" in u or "youtu.be" in u

def _pick_direct_urls(info: dict) -> tuple[Optional[dict], Optional[dict]]:
    """
    Returns (best_video_with_audio, best_audio_only) format dicts.
    For YouTube we prefer *progressive* formats that already include audio (acodec != none).
    """
    formats = info.get("formats") or []
    if not formats:
        # some extractors provide a single direct url
        u = info.get("url")
        if u:
            return ({"url": u, "ext": info.get("ext") or "mp4"}, None)
        return (None, None)

    # audio-only candidates
    audio_candidates = [
        f for f in formats
        if f.get("url") and f.get("acodec") not in (None, "none") and f.get("vcodec") in (None, "none")
    ]
    best_audio = None
    if audio_candidates:
        best_audio = max(
            audio_candidates,
            key=lambda f: (
                f.get("abr") or 0,
                f.get("tbr") or 0,
                f.get("filesize") or 0,
            ),
        )

    # video candidates
    if _is_youtube(info.get("webpage_url") or info.get("original_url") or ""):
        # YouTube: choose progressive formats with audio included
        video_candidates = [
            f for f in formats
            if f.get("url")
            and f.get("vcodec") not in (None, "none")
            and f.get("acodec") not in (None, "none")
        ]
    else:
        # Other sites: often already muxed; prefer those with audio, fallback to best video
        video_candidates = [
            f for f in formats
            if f.get("url") and f.get("vcodec") not in (None, "none")
        ]
        muxed = [f for f in video_candidates if f.get("acodec") not in (None, "none")]
        if muxed:
            video_candidates = muxed

    best_video = None
    if video_candidates:
        best_video = max(
            video_candidates,
            key=lambda f: (
                f.get("height") or 0,
                f.get("tbr") or 0,
                f.get("fps") or 0,
                f.get("filesize") or 0,
            ),
        )

    return (best_video, best_audio)

def _extract_info(url: str) -> dict:
    # TikTok fallback: TikWM API (often more reliable on serverless IPs)
    if "tiktok.com" in url.lower():
        try:
            r = requests.post("https://www.tikwm.com/api/", data={"url": url}, timeout=10)
            data = r.json().get("data") or {}
            # Normalize TikWM into an info-like structure
            return {
                "title": data.get("title") or "TikTok",
                "thumbnail": data.get("cover") or data.get("origin_cover") or "",
                "duration": "",
                "webpage_url": url,
                "formats": [
                    {"url": data.get("play"), "ext": "mp4", "vcodec": "h264", "acodec": "aac", "height": 720, "tbr": 0},
                    {"url": data.get("music"), "ext": "mp3", "vcodec": "none", "acodec": "mp3", "abr": 128, "tbr": 0},
                ],
            }
        except Exception:
            # Fall back to yt-dlp below
            pass

    with yt_dlp.YoutubeDL(_ydl_opts()) as ydl:
        return ydl.extract_info(url, download=False)

async def _stream_remote(url: str):
    async with httpx.AsyncClient(headers=DEFAULT_HEADERS, follow_redirects=True, timeout=30) as client:
        async with client.stream("GET", url) as resp:
            resp.raise_for_status()
            async for chunk in resp.aiter_bytes(chunk_size=1024 * 256):
                if chunk:
                    yield chunk

# -----------------------------
# API
# -----------------------------

@app.get("/api/download")
def get_video_info(url: str = Query(..., description="Video URL")):
    """
    Returns metadata (title/thumbnail/duration) used by the frontend UI.
    """
    try:
        info = _extract_info(url)
        title = info.get("title") or "Video"
        thumbnail = info.get("thumbnail") or ""
        duration = info.get("duration") or ""

        # keep compatibility with current frontend
        return JSONResponse(
            {
                "success": True,
                "video_info": {
                    "title": title,
                    "thumbnail": thumbnail,
                    "duration": str(duration) if duration else "",
                    "download_url": url,
                },
            }
        )
    except Exception as e:
        return JSONResponse(
            {"success": False, "error": "FAILED_TO_FETCH", "details": str(e)},
            status_code=400,
        )

@app.get("/api/proxy")
async def proxy_download(
    url: str = Query(..., description="Original video URL"),
    type: MEDIA_TYPE = Query("video", description="video|audio"),
    stream: int = Query(1, description="1 = stream through server (recommended for mobile); 0 = redirect"),
    filename: Optional[str] = Query(None, description="Preferred filename without extension"),
):
    """
    Provides a downloadable response without storing on disk.
    - stream=1: streams the remote file via Vercel function and sets Content-Disposition.
    - stream=0: redirects to the direct CDN link (fastest, but may navigate).
    """
    try:
        info = _extract_info(url)
        best_video, best_audio = _pick_direct_urls(info)

        chosen = best_video if type == "video" else best_audio
        if not chosen or not chosen.get("url"):
            raise HTTPException(status_code=404, detail="NO_DIRECT_URL")

        direct = chosen["url"]
        ext = chosen.get("ext") or ("mp3" if type == "audio" else "mp4")

        base_title = filename or info.get("title") or "download"
        final_name = _safe_filename(base_title, ext)

        if stream == 0:
            return RedirectResponse(url=direct)

        headers = {
            "Content-Disposition": f'attachment; filename="{final_name}"',
            "Cache-Control": "no-store",
        }
        return StreamingResponse(_stream_remote(direct), media_type="application/octet-stream", headers=headers)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
