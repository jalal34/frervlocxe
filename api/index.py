from __future__ import annotations

import os
import re
from typing import Literal, Optional, Tuple, Dict, Any, List

import httpx
import requests
import yt_dlp
from fastapi import FastAPI, Query, HTTPException
from fastapi.responses import JSONResponse, RedirectResponse, StreamingResponse

app = FastAPI()

MEDIA_TYPE = Literal["video", "audio"]

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9,ar;q=0.8",
}

# =========================
# Utils
# =========================

def _safe_filename(name: str, ext: str) -> str:
    name = (name or "download").strip()
    name = re.sub(r'[\\/:*?"<>|]+', "_", name)
    name = re.sub(r"\s+", " ", name).strip()
    if not name:
        name = "download"
    if ext and not ext.startswith("."):
        ext = "." + ext
    return f"{name}{ext}"

def _is_youtube(url: str) -> bool:
    u = (url or "").lower()
    return "youtube.com" in u or "youtu.be" in u

def _ydl_opts() -> dict:
    # IMPORTANT: لا تحميل على الدسك داخل Vercel
    return {
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
        "nocheckcertificate": True,
        "geo_bypass": True,
        "socket_timeout": 20,
        "http_headers": DEFAULT_HEADERS,
    }

async def _stream_remote(url: str):
    # streaming من نفس الدومين (يحل مشكلة CORS + تنزيل فوري)
    async with httpx.AsyncClient(headers=DEFAULT_HEADERS, follow_redirects=True, timeout=60) as client:
        async with client.stream("GET", url) as resp:
            resp.raise_for_status()
            async for chunk in resp.aiter_bytes(chunk_size=1024 * 256):
                if chunk:
                    yield chunk

def _pick_direct_urls_from_yt_dlp(info: dict) -> Tuple[Optional[dict], Optional[dict]]:
    """
    ترجع:
      - best_video: قدر الإمكان MP4 + صوت (progressive) في يوتيوب
      - best_audio: صوت فقط
    """
    formats = info.get("formats") or []
    if not formats:
        u = info.get("url")
        if u:
            return ({"url": u, "ext": info.get("ext") or "mp4"}, None)
        return (None, None)

    # audio only
    audio_candidates = [
        f for f in formats
        if f.get("url")
        and f.get("vcodec") in (None, "none")
        and f.get("acodec") not in (None, "none")
    ]
    best_audio = None
    if audio_candidates:
        best_audio = max(audio_candidates, key=lambda f: (f.get("abr") or 0, f.get("tbr") or 0, f.get("filesize") or 0))

    # video candidates
    webpage = info.get("webpage_url") or info.get("original_url") or ""
    if _is_youtube(webpage):
        # يوتيوب: حاول progressive (فيه صوت)
        video_candidates = [
            f for f in formats
            if f.get("url")
            and f.get("vcodec") not in (None, "none")
            and f.get("acodec") not in (None, "none")
        ]
        # إذا ما في progressive، خذ best[ext=mp4] (قد يطلع بدون صوت، لكن نحاول قدر الإمكان)
        if not video_candidates:
            video_candidates = [
                f for f in formats
                if f.get("url") and f.get("ext") == "mp4" and f.get("vcodec") not in (None, "none")
            ]
    else:
        # باقي المواقع غالبًا muxed
        video_candidates = [f for f in formats if f.get("url") and f.get("vcodec") not in (None, "none")]
        muxed = [f for f in video_candidates if f.get("acodec") not in (None, "none")]
        if muxed:
            video_candidates = muxed

    best_video = None
    if video_candidates:
        best_video = max(video_candidates, key=lambda f: (f.get("height") or 0, f.get("tbr") or 0, f.get("fps") or 0, f.get("filesize") or 0))

    return (best_video, best_audio)

# =========================
# TikWM (TikTok)
# =========================

def _extract_tiktok_tikwm(url: str) -> Optional[dict]:
    try:
        r = requests.post("https://www.tikwm.com/api/", data={"url": url}, timeout=15)
        j = r.json() if r.ok else {}
        data = j.get("data") or {}
        if not data:
            return None

        title = data.get("title") or "TikTok"
        thumb = data.get("cover") or data.get("origin_cover") or ""
        play = data.get("play")  # فيديو بدون علامة غالباً
        music = data.get("music")

        formats = []
        if play:
            formats.append({"url": play, "ext": "mp4", "type": "video", "quality": "video"})
        if music:
            formats.append({"url": music, "ext": "mp3", "type": "audio", "quality": "audio"})

        return {
            "title": title,
            "thumbnail": thumb,
            "duration": "",
            "webpage_url": url,
            "formats": formats,
            "extractor": "tikwm",
        }
    except Exception:
        return None

# =========================
# RapidAPI (الأكثر ثباتًا لمعظم المنصات)
# =========================

RAPID_KEY = os.getenv("RAPIDAPI_KEY", "").strip()
RAPID_HOST = os.getenv("RAPIDAPI_HOST", "social-download-all-in-one.p.rapidapi.com").strip()
RAPID_ENDPOINT = os.getenv("RAPIDAPI_ENDPOINT", "https://social-download-all-in-one.p.rapidapi.com/v1/social/autolink").strip()

def _extract_via_rapidapi(url: str) -> Optional[dict]:
    """
    يحتاج:
      RAPIDAPI_KEY في Vercel Environment Variables
    """
    if not RAPID_KEY:
        return None

    try:
        headers = {
            "Content-Type": "application/json",
            "x-rapidapi-key": RAPID_KEY,
            "x-rapidapi-host": RAPID_HOST,
        }
        payload = {"url": url}
        r = requests.post(RAPID_ENDPOINT, json=payload, headers=headers, timeout=25)
        if not r.ok:
            return None

        j = r.json() or {}
        if j.get("error") is True:
            return None

        title = j.get("title") or "Video"
        thumb = j.get("thumbnail") or ""
        duration = j.get("duration") or ""

        medias = j.get("medias") or []
        formats = []
        for m in medias:
            m_url = m.get("url")
            m_type = m.get("type")  # "video" / "audio"
            ext = (m.get("extension") or "").lower() or ("mp4" if m_type == "video" else "mp3")
            quality = m.get("quality") or ""
            if m_url and m_type in ("video", "audio"):
                formats.append({"url": m_url, "ext": ext, "type": m_type, "quality": quality})

        if not formats:
            return None

        return {
            "title": title,
            "thumbnail": thumb,
            "duration": str(duration) if duration else "",
            "webpage_url": url,
            "formats": formats,
            "extractor": "rapidapi",
            "raw": {"source": j.get("source")},
        }
    except Exception:
        return None

def _pick_from_generic_formats(formats: List[dict]) -> Tuple[Optional[dict], Optional[dict]]:
    """
    formats: list of {url, ext, type, quality}
    """
    videos = [f for f in formats if f.get("type") == "video" and f.get("url")]
    audios = [f for f in formats if f.get("type") == "audio" and f.get("url")]

    def v_score(f):
        q = (f.get("quality") or "").lower()
        # نفضل hd / no_watermark
        bonus = 0
        if "hd" in q:
            bonus += 3
        if "no_watermark" in q or "no-watermark" in q:
            bonus += 2
        if "watermark" in q:
            bonus -= 1
        return bonus

    best_video = max(videos, key=v_score) if videos else None
    best_audio = audios[0] if audios else None
    return best_video, best_audio

# =========================
# Main extractor (order مهم)
# =========================

def _extract_info(url: str) -> dict:
    u = (url or "").strip()
    if not u:
        raise HTTPException(status_code=400, detail="EMPTY_URL")

    # 1) TikTok via TikWM
    if "tiktok.com" in u.lower():
        tik = _extract_tiktok_tikwm(u)
        if tik:
            return tik

    # 2) RapidAPI (أفضل ثبات لكثير منصات)
    rap = _extract_via_rapidapi(u)
    if rap:
        return rap

    # 3) yt-dlp fallback (مفيد جدًا ليوتيوب وبعض المواقع)
    with yt_dlp.YoutubeDL(_ydl_opts()) as ydl:
        return ydl.extract_info(u, download=False)

# =========================
# Routes
# =========================

@app.get("/api/download")
def api_download(url: str = Query(..., description="Video URL")):
    """
    واجهة جلب المعلومات للـ Frontend
    """
    try:
        info = _extract_info(url)
        title = info.get("title") or "Video"
        thumb = info.get("thumbnail") or ""
        duration = info.get("duration") or ""

        platform = "unknown"
        if "tiktok.com" in url.lower():
            platform = "tiktok"
        elif "instagram.com" in url.lower():
            platform = "instagram"
        elif "facebook.com" in url.lower() or "fb.watch" in url.lower():
            platform = "facebook"
        elif "snapchat.com" in url.lower():
            platform = "snapchat"
        elif "pinterest" in url.lower():
            platform = "pinterest"
        elif "x.com" in url.lower() or "twitter.com" in url.lower():
            platform = "x"
        elif _is_youtube(url):
            platform = "youtube"

        return JSONResponse(
            {
                "success": True,
                "video_info": {
                    "title": title,
                    "thumbnail": thumb,
                    "duration": str(duration) if duration else "",
                    "platform": platform,
                    "download_url": url,
                },
            }
        )
    except HTTPException as he:
        return JSONResponse({"success": False, "error": "FAILED_TO_FETCH", "details": str(he.detail)}, status_code=he.status_code)
    except Exception as e:
        return JSONResponse({"success": False, "error": "FAILED_TO_FETCH", "details": str(e)}, status_code=400)

@app.get("/api/proxy")
async def api_proxy(
    url: str = Query(..., description="Original video URL"),
    type: MEDIA_TYPE = Query("video", description="video|audio"),
    stream: int = Query(1, description="1=stream (ينفع للموبايل) / 0=redirect"),
    filename: Optional[str] = Query(None, description="Preferred filename"),
):
    """
    تنزيل:
      - stream=1: يرجّع الملف كبايتات من نفس الدومين (أفضل للموبايل + بدون CORS)
      - stream=0: Redirect للرابط المباشر (أسرع لكن قد يفتح صفحة)
    """
    try:
        info = _extract_info(url)

        direct_url = None
        ext = "mp4"

        # إذا كان مصدر RapidAPI/TikWM (formats فيها type)
        if isinstance(info.get("formats"), list) and info.get("formats") and isinstance(info["formats"][0], dict) and "type" in info["formats"][0]:
            best_v, best_a = _pick_from_generic_formats(info["formats"])
            chosen = best_v if type == "video" else best_a
            if not chosen or not chosen.get("url"):
                raise HTTPException(status_code=404, detail="NO_DIRECT_URL")
            direct_url = chosen["url"]
            ext = chosen.get("ext") or ("mp3" if type == "audio" else "mp4")
        else:
            # yt-dlp formats
            best_v, best_a = _pick_direct_urls_from_yt_dlp(info)
            chosen = best_v if type == "video" else best_a
            if not chosen or not chosen.get("url"):
                raise HTTPException(status_code=404, detail="NO_DIRECT_URL")
            direct_url = chosen["url"]
            ext = chosen.get("ext") or ("mp3" if type == "audio" else "mp4")

        base_title = filename or info.get("title") or "download"
        final_name = _safe_filename(base_title, ext)

        if stream == 0:
            return RedirectResponse(url=direct_url)

        headers = {
            "Content-Disposition": f'attachment; filename="{final_name}"',
            "Cache-Control": "no-store",
        }
        return StreamingResponse(_stream_remote(direct_url), media_type="application/octet-stream", headers=headers)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))