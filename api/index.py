from __future__ import annotations

import re
from typing import Optional, Literal, Tuple, Dict, Any, List

import httpx
import yt_dlp
from fastapi import FastAPI, Query, HTTPException
from fastapi.responses import JSONResponse, StreamingResponse, RedirectResponse

app = FastAPI()

# =========================
# Basic settings
# =========================

DEFAULT_HEADERS = {
    # موبايل UA يساعد أحيانًا
    "User-Agent": (
        "Mozilla/5.0 (Linux; Android 13; Mobile) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36"
    ),
    "Accept": "*/*",
    "Accept-Language": "en-US,en;q=0.9,ar;q=0.8",
    "Connection": "keep-alive",
}

FILENAME_SAFE_RE = re.compile(r'[^A-Za-z0-9\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF _\-\.\(\)\[\]]+')

def _safe_filename(name: str, ext: str) -> str:
    base = (name or "video").strip()
    base = base[:160]
    base = FILENAME_SAFE_RE.sub("", base).strip()
    if not base:
        base = "video"
    if not ext:
        ext = "mp4"
    ext = ext.lstrip(".")
    return f"{base}.{ext}"

def _is_youtube(url: str) -> bool:
    u = (url or "").lower()
    return "youtube.com" in u or "youtu.be" in u

def _is_m3u8_format(f: Dict[str, Any]) -> bool:
    # يستبعد HLS
    proto = (f.get("protocol") or "").lower()
    ext = (f.get("ext") or "").lower()
    url = (f.get("url") or "").lower()
    if ext == "m3u8":
        return True
    if "m3u8" in proto:
        return True
    if ".m3u8" in url:
        return True
    return False

def _ydl_opts() -> Dict[str, Any]:
    return {
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
        "cachedir": False,
        "nocheckcertificate": True,
        "http_headers": DEFAULT_HEADERS,
        # يحسن بعض الحالات
        "extractor_retries": 2,
        "retries": 2,
        "socket_timeout": 15,
    }

def _extract_info(url: str) -> Dict[str, Any]:
    with yt_dlp.YoutubeDL(_ydl_opts()) as ydl:
        return ydl.extract_info(url, download=False)

def _pick_best_audio(formats: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    audio = [
        f for f in formats
        if f.get("url")
        and f.get("acodec") not in (None, "none")
        and f.get("vcodec") in (None, "none")
        and not _is_m3u8_format(f)
    ]
    if not audio:
        # أحياناً الصوت يكون muxed داخل mp4 (بدون audio-only واضح)
        return None
    return max(
        audio,
        key=lambda f: (
            f.get("abr") or 0,
            f.get("tbr") or 0,
            f.get("filesize") or 0,
        ),
    )

def _pick_best_video_with_audio(info: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    formats = info.get("formats") or []
    if not formats:
        u = info.get("url")
        if u:
            return {"url": u, "ext": info.get("ext") or "mp4"}
        return None

    page = info.get("webpage_url") or info.get("original_url") or ""
    yt = _is_youtube(page)

    # 1) نفضل mp4 + صوت (progressive)
    progressive = [
        f for f in formats
        if f.get("url")
        and f.get("vcodec") not in (None, "none")
        and f.get("acodec") not in (None, "none")
        and not _is_m3u8_format(f)
        and (not yt or (f.get("ext") or "").lower() in ("mp4", "m4v"))
    ]
    if progressive:
        return max(
            progressive,
            key=lambda f: (
                f.get("height") or 0,
                f.get("tbr") or 0,
                f.get("fps") or 0,
                f.get("filesize") or 0,
            ),
        )

    # 2) لو ما في progressive: نختار أفضل فيديو (mp4) حتى لو بدون صوت (قد يفشل لو يحتاج دمج)
    # لكن نحاول نستبعد m3u8
    video_only = [
        f for f in formats
        if f.get("url")
        and f.get("vcodec") not in (None, "none")
        and not _is_m3u8_format(f)
    ]
    if video_only:
        return max(
            video_only,
            key=lambda f: (
                f.get("height") or 0,
                f.get("tbr") or 0,
                f.get("fps") or 0,
                f.get("filesize") or 0,
            ),
        )

    return None

async def _stream_remote(url: str):
    # Streaming مباشر بدون تخزين على disk
    async with httpx.AsyncClient(headers=DEFAULT_HEADERS, follow_redirects=True, timeout=30) as client:
        async with client.stream("GET", url) as resp:
            resp.raise_for_status()
            async for chunk in resp.aiter_bytes(chunk_size=1024 * 256):
                if chunk:
                    yield chunk

# =========================
# API
# =========================

@app.get("/api/download")
def api_download(url: str = Query(..., description="Video URL")):
    """
    Frontend metadata endpoint.
    """
    try:
        info = _extract_info(url)

        title = info.get("title") or "Video"
        thumb = info.get("thumbnail") or ""
        dur = info.get("duration") or ""

        # platform name (اختياري)
        extractor = info.get("extractor_key") or info.get("extractor") or ""
        platform = (extractor or "").strip() or "Unknown"

        return JSONResponse({
            "success": True,
            "title": title,
            "thumbnail": thumb,
            "duration": str(dur) if dur is not None else "",
            "platform": platform,
            "url": url,
        })
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"download/info failed: {str(e)}")

@app.get("/api/proxy")
def api_proxy(
    url: str = Query(..., description="Video URL"),
    type: Literal["video", "audio"] = Query("video"),
    stream: int = Query(1, description="1=stream via server, 0=redirect"),
    filename: Optional[str] = Query(None, description="Preferred filename without extension"),
):
    """
    - stream=1: يرجّع 200 + Content-Disposition (أفضل للموبايل لتنزيل مباشر بدون صفحة ثانية)
    - stream=0: Redirect للرابط المباشر (أسرع، لكن قد يفتح صفحة/تبويب)
    """
    try:
        info = _extract_info(url)
        formats = info.get("formats") or []

        best_video = _pick_best_video_with_audio(info)
        best_audio = _pick_best_audio(formats)

        chosen = best_video if type == "video" else best_audio

        # لو طلب صوت وما لقينا audio-only، نحاول نأخذ من progressive (الصوت داخل mp4)
        if chosen is None and type == "audio":
            # آخر حل: خذ best progressive mp4 (صوت داخل الفيديو)
            chosen = best_video

        if chosen is None or not chosen.get("url"):
            # هذا غالباً يعني: المنصة ما تعطي رابط مباشر (أو تتطلب cookies/DRM)
            raise HTTPException(
                status_code=400,
                detail="No direct downloadable file found (mp4). This link may require login/cookies or provides HLS only.",
            )

        direct_url = chosen["url"]
        ext = (chosen.get("ext") or ("mp3" if type == "audio" else "mp4")).lower()

        base_title = filename or (info.get("title") or "video")
        final_name = _safe_filename(base_title, "mp3" if type == "audio" else ext)

        if stream == 0:
            return RedirectResponse(url=direct_url)

        headers = {
            "Content-Disposition": f'attachment; filename="{final_name}"',
            "Cache-Control": "no-store",
            # يفيد لو احتجت تقرأ headers من الفرونت
            "Access-Control-Expose-Headers": "Content-Disposition",
        }
        return StreamingResponse(_stream_remote(direct_url), media_type="application/octet-stream", headers=headers)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"proxy failed: {str(e)}")