from __future__ import annotations

import re
from typing import Any, Dict, Optional, Tuple
from urllib.parse import quote

import httpx
import yt_dlp
from fastapi import FastAPI, HTTPException, Query, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse


app = FastAPI()

# CORS (لـ /api/info وطلبات الفرونت)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


UA = (
    "Mozilla/5.0 (Linux; Android 13; Mobile) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36"
)

# فلترة اسم الملف
def safe_filename(name: str, default: str = "download") -> str:
    name = (name or "").strip()
    name = re.sub(r"[\\/*?:\"<>|]", "", name)
    name = re.sub(r"\s+", " ", name).strip()
    if not name:
        name = default
    if len(name) > 120:
        name = name[:120]
    return name


def ydl_opts() -> Dict[str, Any]:
    # ملاحظة: لا تنزيل على القرص (Vercel readonly) — فقط extract_info
    return {
        "quiet": True,
        "no_warnings": True,
        "nocheckcertificate": True,
        "noplaylist": True,
        "user_agent": UA,
        "http_headers": {"User-Agent": UA, "Accept-Language": "en-US,en;q=0.9"},
        # مهم لبعض المنصات
        "extractor_args": {
            "youtube": {"skip": ["dash", "hls"]},
        },
    }


def detect_platform(url: str) -> str:
    u = url.lower()
    if "tiktok.com" in u:
        return "tiktok"
    if "youtube.com" in u or "youtu.be" in u:
        return "youtube"
    if "instagram.com" in u:
        return "instagram"
    if "facebook.com" in u or "fb.watch" in u:
        return "facebook"
    if "snapchat.com" in u:
        return "snapchat"
    if "pinterest." in u:
        return "pinterest"
    if "x.com" in u or "twitter.com" in u:
        return "x/twitter"
    return "generic"


async def tiktok_direct(url: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """
    محاولة استخراج روابط تيك توك عبر TikWM (أحياناً أنجح من yt-dlp على سيرفرليس).
    يعيد: (video_url, audio_url, title)
    """
    api = f"https://www.tikwm.com/api/?url={quote(url)}"
    try:
        async with httpx.AsyncClient(timeout=20, headers={"User-Agent": UA}) as client:
            r = await client.get(api)
            if r.status_code != 200:
                return None, None, None
            data = r.json()
            d = (data or {}).get("data") or {}
            v = d.get("play") or d.get("wmplay")
            a = d.get("music")
            title = d.get("title")
            return v, a, title
    except Exception:
        return None, None, None


def pick_youtube_format(info: Dict[str, Any], kind: str) -> Tuple[str, str]:
    """
    YouTube:
    - kind=video => أفضل mp4 مع صوت (قدر الإمكان)
    - kind=audio => أفضل صوت
    """
    formats = info.get("formats") or []
    title = info.get("title") or "youtube"

    if kind == "audio":
        # أفضل صوت
        audio = None
        for f in formats:
            if f.get("vcodec") == "none" and f.get("url"):
                abr = f.get("abr") or 0
                if not audio or abr > (audio.get("abr") or 0):
                    audio = f
        if audio and audio.get("url"):
            return audio["url"], title
        raise HTTPException(status_code=404, detail="No audio format found")

    # فيديو مع صوت: نفضّل progressive (فيه صوت+صورة)
    progressive = None
    for f in formats:
        if f.get("acodec") != "none" and f.get("vcodec") != "none" and f.get("ext") == "mp4" and f.get("url"):
            h = f.get("height") or 0
            if not progressive or h > (progressive.get("height") or 0):
                progressive = f
    if progressive and progressive.get("url"):
        return progressive["url"], title

    # fallback: أفضل فيديو (بدون صوت) — كثير الأحيان اليوتيوب يحتاج دمج (غير ممكن في Vercel)
    video_only = None
    for f in formats:
        if f.get("acodec") == "none" and f.get("vcodec") != "none" and f.get("url"):
            h = f.get("height") or 0
            if not video_only or h > (video_only.get("height") or 0):
                video_only = f

    if video_only and video_only.get("url"):
        # بنرجع فيديو فقط كحل أخير (على Vercel لا نستطيع دمج صوت+فيديو)
        return video_only["url"], title

    raise HTTPException(status_code=404, detail="No video format found")


def pick_generic_format(info: Dict[str, Any], kind: str) -> Tuple[str, str]:
    """
    للمنصات الأخرى: غالباً yt-dlp يعطينا url مباشر جاهز.
    """
    title = info.get("title") or "video"
    if kind == "audio":
        # ابحث عن bestaudio
        for f in (info.get("formats") or [])[::-1]:
            if f.get("vcodec") == "none" and f.get("url"):
                return f["url"], title
        # fallback: لو أعطى url واحد فقط
        if info.get("url"):
            return info["url"], title
        raise HTTPException(status_code=404, detail="No audio found")

    # فيديو
    if info.get("url"):
        return info["url"], title
    # fallback من formats
    fmts = info.get("formats") or []
    best = None
    for f in fmts:
        if f.get("url") and f.get("vcodec") != "none":
            h = f.get("height") or 0
            if not best or h > (best.get("height") or 0):
                best = f
    if best and best.get("url"):
        return best["url"], title

    raise HTTPException(status_code=404, detail="No video found")


@app.get("/api/health")
def health():
    return {"ok": True}


@app.get("/api/info")
def info(url: str = Query(..., min_length=5)):
    """
    معلومات بسيطة لعرضها في الواجهة.
    """
    platform = detect_platform(url)

    # TikTok: جرّب TikWM أولاً
    if platform == "tiktok":
        # نرسل معلومات بسيطة (بدون formats معقدة)
        # الفيديو/الصوت النهائي يتم عبر /api/proxy
        return {
            "title": "TikTok",
            "thumbnail": "",
            "duration": "",
            "platform": "TikTok",
        }

    try:
        with yt_dlp.YoutubeDL(ydl_opts()) as ydl:
            data = ydl.extract_info(url, download=False)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"info_error: {str(e)}")

    return {
        "title": data.get("title") or "Video",
        "thumbnail": data.get("thumbnail") or "",
        "duration": str(data.get("duration") or ""),
        "platform": platform,
        "views": str(data.get("view_count") or "") if data.get("view_count") else "",
    }


@app.get("/api/proxy")
async def proxy(
    url: str = Query(..., min_length=5),
    type: str = Query("video", pattern="^(video|audio)$"),
    stream: int = Query(1),  # 1 = streaming through our server (حل مشكلة CORS)
    filename: str = Query("download"),
):
    platform = detect_platform(url)
    wanted = "audio" if type == "audio" else "video"

    direct_url: Optional[str] = None
    title: str = filename

    # TikTok handling
    if platform == "tiktok":
        v, a, t = await tiktok_direct(url)
        title = t or filename or "tiktok"
        direct_url = a if wanted == "audio" else v
        if not direct_url:
            # fallback yt-dlp
            try:
                with yt_dlp.YoutubeDL(ydl_opts()) as ydl:
                    data = ydl.extract_info(url, download=False)
                direct_url, title = pick_generic_format(data, wanted)
            except Exception as e:
                raise HTTPException(status_code=400, detail=f"tiktok_error: {str(e)}")

    else:
        # Generic via yt-dlp
        try:
            with yt_dlp.YoutubeDL(ydl_opts()) as ydl:
                data = ydl.extract_info(url, download=False)

            if platform == "youtube":
                direct_url, title = pick_youtube_format(data, wanted)
            else:
                direct_url, title = pick_generic_format(data, wanted)

        except Exception as e:
            raise HTTPException(status_code=400, detail=f"proxy_error: {str(e)}")

    if not direct_url:
        raise HTTPException(status_code=404, detail="No direct url")

    # اسم ملف نهائي
    base = safe_filename(filename or title or "download")
    ext = ".mp3" if wanted == "audio" else ".mp4"
    out_name = f"{base}{ext}"

    # لو المستخدم اختار stream=0 نرجّع redirect (قد يسبب CORS مع fetch)
    if stream == 0:
        # ملاحظة: لا يمكن فرض attachment عبر redirect
        return Response(status_code=307, headers={"Location": direct_url})

    # Streaming through our domain (أفضل حل لـ "فشل التحميل")
    headers = {
        "User-Agent": UA,
        "Accept": "*/*",
        "Referer": url,
        "Origin": "https://example.com",
    }

    async def iter_bytes():
        async with httpx.AsyncClient(timeout=None, follow_redirects=True, headers=headers) as client:
            async with client.stream("GET", direct_url) as r:
                if r.status_code >= 400:
                    raise HTTPException(status_code=502, detail=f"upstream_status:{r.status_code}")
                async for chunk in r.aiter_bytes(chunk_size=1024 * 256):
                    yield chunk

    resp_headers = {
        "Content-Disposition": f'attachment; filename="{out_name}"',
        "Cache-Control": "no-store",
    }

    return StreamingResponse(iter_bytes(), media_type="application/octet-stream", headers=resp_headers)