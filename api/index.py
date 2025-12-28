from __future__ import annotations

import re
import time
from typing import Any, Dict, Optional, Tuple

import httpx
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse

import yt_dlp


app = FastAPI()

# CORS (نفس الدومين على Vercel عادة ما يحتاج، لكن نخليه واسع لتجنب مشاكل الجلب)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Helpers ---------------------------------------------------------

def _is_youtube(url: str) -> bool:
    u = url.lower()
    return "youtube.com" in u or "youtu.be" in u

def _safe_filename(name: str, max_len: int = 120) -> str:
    name = name.strip()
    name = re.sub(r"[\\/:*?\"<>|]+", "", name)
    name = re.sub(r"\s+", " ", name)
    if not name:
        name = "download"
    if len(name) > max_len:
        name = name[:max_len].rstrip()
    return name

def _ydl_common_opts() -> Dict[str, Any]:
    return {
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
        "extract_flat": False,
        "nocheckcertificate": True,
        "cachedir": False,
        # هيدرز عامة تقلل فشل بعض المواقع
        "http_headers": {
            "User-Agent": (
                "Mozilla/5.0 (Linux; Android 13) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/124.0.0.0 Mobile Safari/537.36"
            ),
            "Accept": "*/*",
            "Accept-Language": "en-US,en;q=0.9,ar;q=0.8",
        },
    }

def _extract_info(url: str) -> Dict[str, Any]:
    opts = _ydl_common_opts()
    with yt_dlp.YoutubeDL(opts) as ydl:
        return ydl.extract_info(url, download=False)

def _pick_youtube_progressive_formats(info: Dict[str, Any]) -> list[Dict[str, Any]]:
    """
    نختار فقط Progressive (صوت+فيديو معًا) عشان "ينزل مع الصوت" بدون ffmpeg.
    """
    fmts = info.get("formats") or []
    good = []
    for f in fmts:
        # progressive: فيه audio+video
        if f.get("vcodec") != "none" and f.get("acodec") != "none":
            # نفضل mp4
            ext = (f.get("ext") or "").lower()
            proto = (f.get("protocol") or "").lower()
            url = f.get("url")
            if not url:
                continue
            # استبعد dash/m3u8 قد ما نقدر
            if "m3u8" in proto or "dash" in proto:
                continue
            good.append(f)
    # رتب من الأعلى للأقل (height ثم tbr)
    good.sort(key=lambda x: (x.get("height") or 0, x.get("tbr") or 0), reverse=True)
    return good

def _pick_best_non_youtube_video(info: Dict[str, Any]) -> Dict[str, Any]:
    """
    لغير اليوتيوب: نختار "best" فيديو (غالبًا mp4).
    """
    fmts = info.get("formats") or []
    candidates = []
    for f in fmts:
        if f.get("vcodec") != "none":
            url = f.get("url")
            if not url:
                continue
            ext = (f.get("ext") or "").lower()
            proto = (f.get("protocol") or "").lower()
            # نفضل mp4 ونبعد m3u8
            score = 0
            if ext == "mp4":
                score += 50
            if "m3u8" in proto:
                score -= 50
            score += int(f.get("height") or 0)
            score += int(f.get("tbr") or 0) // 10
            candidates.append((score, f))
    if not candidates:
        raise HTTPException(status_code=400, detail="No downloadable video format found.")
    candidates.sort(key=lambda x: x[0], reverse=True)
    return candidates[0][1]

def _pick_best_audio(info: Dict[str, Any]) -> Dict[str, Any]:
    fmts = info.get("formats") or []
    candidates = []
    for f in fmts:
        if f.get("acodec") != "none" and f.get("vcodec") == "none":
            url = f.get("url")
            if not url:
                continue
            ext = (f.get("ext") or "").lower()
            abr = f.get("abr") or 0
            score = 0
            if ext in ("m4a", "mp3", "aac", "webm", "opus"):
                score += 20
            score += int(abr or 0)
            candidates.append((score, f))
    if not candidates:
        # fallback: أحيانًا يكون best فيه صوت+فيديو فقط
        for f in fmts:
            if f.get("acodec") != "none":
                url = f.get("url")
                if url:
                    return f
        raise HTTPException(status_code=400, detail="No downloadable audio format found.")
    candidates.sort(key=lambda x: x[0], reverse=True)
    return candidates[0][1]

def _resolve_download_target(url: str, kind: str, format_id: Optional[str]) -> Tuple[str, str, str]:
    """
    يرجع: (direct_url, filename, content_type)
    """
    info = _extract_info(url)

    title = info.get("title") or "download"
    title = _safe_filename(title)

    if kind == "audio":
        f = _pick_best_audio(info)
        direct = f.get("url")
        ext = (f.get("ext") or "m4a").lower()
        filename = f"{title}.{ext}"
        ctype = "audio/mpeg" if ext == "mp3" else "audio/mp4" if ext == "m4a" else "application/octet-stream"
        return direct, filename, ctype

    # video
    if _is_youtube(url):
        progressive = _pick_youtube_progressive_formats(info)
        if not progressive:
            raise HTTPException(
                status_code=400,
                detail="YouTube: no progressive (audio+video) MP4 found. Some videos require DASH/ffmpeg.",
            )

        chosen = None
        if format_id:
            for f in progressive:
                if str(f.get("format_id")) == str(format_id):
                    chosen = f
                    break
        if not chosen:
            chosen = progressive[0]

        direct = chosen.get("url")
        ext = (chosen.get("ext") or "mp4").lower()
        height = chosen.get("height") or ""
        tag = f"_{height}p" if height else ""
        filename = f"{title}{tag}.{ext}"
        return direct, filename, "video/mp4" if ext == "mp4" else "application/octet-stream"

    # Non-YouTube video
    chosen = _pick_best_non_youtube_video(info)
    direct = chosen.get("url")
    ext = (chosen.get("ext") or "mp4").lower()
    filename = f"{title}.{ext}"
    return direct, filename, "video/mp4" if ext == "mp4" else "application/octet-stream"


# --- Routes ----------------------------------------------------------

@app.get("/api/health")
def health():
    return {"ok": True, "ts": int(time.time())}

@app.get("/api/info")
def info(url: str = Query(..., min_length=5)):
    try:
        data = _extract_info(url)

        base = {
            "title": data.get("title"),
            "thumbnail": data.get("thumbnail"),
            "extractor": data.get("extractor"),
            "duration": data.get("duration"),
            "webpage_url": data.get("webpage_url") or url,
            "is_youtube": _is_youtube(url),
        }

        # YouTube: رجّع قائمة صيغ progressive فقط (عشان كلها تنزل مع الصوت)
        if _is_youtube(url):
            fmts = _pick_youtube_progressive_formats(data)
            out = []
            for f in fmts[:40]:
                out.append({
                    "format_id": f.get("format_id"),
                    "ext": f.get("ext"),
                    "height": f.get("height"),
                    "filesize": f.get("filesize") or f.get("filesize_approx"),
                    "tbr": f.get("tbr"),
                    "fps": f.get("fps"),
                    "acodec": f.get("acodec"),
                    "vcodec": f.get("vcodec"),
                })
            base["formats"] = out
        else:
            # باقي المنصات: خيارين فقط (فيديو/صوت)
            base["formats"] = [
                {"id": "video", "label": "video"},
                {"id": "audio", "label": "audio"},
            ]

        return base
    except Exception as e:
        return JSONResponse(status_code=400, content={"error": str(e)})

@app.get("/api/download")
def download(
    url: str = Query(..., min_length=5),
    kind: str = Query("video", pattern="^(video|audio)$"),
    format_id: Optional[str] = Query(None),
):
    """
    تحميل مباشر بنفس الصفحة (Streaming Proxy) بدون حفظ على الديسك.
    - kind=video|audio
    - format_id: لليوتيوب فقط (اختياري)
    """
    direct_url, filename, content_type = _resolve_download_target(url, kind, format_id)

    # Stream من المصدر للعميل
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Linux; Android 13) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/124.0.0.0 Mobile Safari/537.36"
        ),
        "Accept": "*/*",
        "Accept-Language": "en-US,en;q=0.9,ar;q=0.8",
        # بعض السيرفرات تحتاج Referer - نخليه نفس الدومين الأصلي إن أمكن
        "Referer": url,
    }

    client = httpx.Client(follow_redirects=True, timeout=60.0, headers=headers)

    try:
        upstream = client.stream("GET", direct_url)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Upstream connection failed: {e}")

    def iter_bytes():
        with upstream:
            try:
                for chunk in upstream.iter_bytes(chunk_size=1024 * 256):
                    if chunk:
                        yield chunk
            finally:
                client.close()

    resp_headers = {
        "Content-Disposition": f'attachment; filename="{filename}"',
        "Cache-Control": "no-store",
    }

    return StreamingResponse(iter_bytes(), media_type=content_type, headers=resp_headers)