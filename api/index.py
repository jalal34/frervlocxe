from __future__ import annotations

import re
import json
from typing import Any, Dict, Optional, Tuple, List

import yt_dlp
import httpx
from fastapi import FastAPI, Query, HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware


app = FastAPI()

# CORS (خليه مفتوح لأن الواجهة على نفس الدومين عادة، لكن هذا يمنع مشاكل)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

DEFAULT_UA = (
    "Mozilla/5.0 (Linux; Android 12) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/121.0.0.0 Mobile Safari/537.36"
)

TIKTOK_RE = re.compile(r"(tiktok\.com|vm\.tiktok\.com|vt\.tiktok\.com)", re.I)


def _ydl() -> yt_dlp.YoutubeDL:
    # ملاحظة: لا تنزيل على القرص نهائياً
    opts = {
        "quiet": True,
        "no_warnings": True,
        "nocheckcertificate": True,
        "geo_bypass": True,
        "noplaylist": True,
        "extract_flat": False,
        "http_headers": {
            "User-Agent": DEFAULT_UA,
            "Accept-Language": "en-US,en;q=0.9,ar;q=0.8",
        },
    }
    return yt_dlp.YoutubeDL(opts)


def _is_youtube(url: str) -> bool:
    u = url.lower()
    return ("youtube.com" in u) or ("youtu.be" in u)


def _pick_best_progressive_mp4(formats: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """
    يوتيوب: نختار MP4 فيه صوت+فيديو (progressive) لأننا لا نستطيع دمج صوت+فيديو على Vercel.
    """
    candidates = []
    for f in formats:
        if f.get("ext") != "mp4":
            continue
        if f.get("vcodec") in (None, "none"):
            continue
        if f.get("acodec") in (None, "none"):
            continue
        candidates.append(f)

    # الأفضل حسب الجودة/الارتفاع/البتريت
    def score(f: Dict[str, Any]) -> Tuple[int, int, float]:
        h = int(f.get("height") or 0)
        tbr = float(f.get("tbr") or 0.0)
        fps = int(f.get("fps") or 0)
        return (h, fps, tbr)

    candidates.sort(key=score, reverse=True)
    return candidates[0] if candidates else None


def _pick_best_audio(formats: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    audio = []
    for f in formats:
        if f.get("vcodec") not in (None, "none"):
            continue
        if f.get("acodec") in (None, "none"):
            continue
        audio.append(f)

    def score(f: Dict[str, Any]) -> float:
        abr = float(f.get("abr") or 0.0)
        tbr = float(f.get("tbr") or 0.0)
        return max(abr, tbr)

    audio.sort(key=score, reverse=True)
    return audio[0] if audio else None


def _pick_best_generic_video(formats: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    # لغير يوتيوب: غالبًا أفضل فيديو يكون رابط مباشر فيه صوت
    candidates = []
    for f in formats:
        # نفضّل mp4
        if f.get("ext") not in ("mp4", "m4a", "webm", "mov"):
            continue
        # نفضل اللي فيها فيديو (أو best)
        if f.get("vcodec") in (None, "none"):
            continue
        candidates.append(f)

    def score(f: Dict[str, Any]) -> Tuple[int, float]:
        h = int(f.get("height") or 0)
        tbr = float(f.get("tbr") or 0.0)
        return (h, tbr)

    candidates.sort(key=score, reverse=True)
    return candidates[0] if candidates else None


async def _tiktok_tikwm_direct(url: str, want_audio: bool) -> Optional[str]:
    """
    TikTok fallback عبر TikWM (عادة يعطي direct links)
    """
    api = "https://www.tikwm.com/api/"
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            r = await client.post(api, data={"url": url})
            r.raise_for_status()
            data = r.json()
            d = (data or {}).get("data") or {}
            if want_audio:
                return d.get("music")
            # بدون علامة مائية غالبًا:
            return d.get("play") or d.get("wmplay")
    except Exception:
        return None


def _safe_filename(name: str, fallback: str = "video") -> str:
    name = (name or "").strip()
    if not name:
        return fallback
    # تنظيف بسيط
    name = re.sub(r"[\\/:*?\"<>|]+", "", name)
    name = re.sub(r"\s+", " ", name).strip()
    # حد الطول
    if len(name) > 80:
        name = name[:80].strip()
    return name or fallback


def _extract_info(url: str) -> Dict[str, Any]:
    try:
        with _ydl() as ydl:
            return ydl.extract_info(url, download=False)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"فشل استخراج معلومات الرابط: {str(e)}")


def _normalize_info(info: Dict[str, Any]) -> Dict[str, Any]:
    title = info.get("title") or "Video"
    thumb = info.get("thumbnail") or ""
    duration = info.get("duration") or 0
    webpage_url = info.get("webpage_url") or info.get("original_url") or ""
    extractor = info.get("extractor_key") or info.get("extractor") or ""

    return {
        "title": title,
        "thumbnail": thumb,
        "duration": duration,
        "webpage_url": webpage_url,
        "platform": extractor or "Unknown",
        "formats_count": len(info.get("formats") or []),
    }


@app.get("/api/health")
def health():
    return {"ok": True}


@app.get("/api/info")
def info(url: str = Query(..., min_length=5)):
    info_dict = _extract_info(url)
    formats = info_dict.get("formats") or []

    base = _normalize_info(info_dict)

    # YouTube: رجّع قائمة صيغ “مدعومة” بدون دمج (Progressive MP4 + Audio)
    if _is_youtube(url):
        progressive = []
        audio_only = []

        for f in formats:
            ext = f.get("ext")
            fid = f.get("format_id")
            if not fid:
                continue

            vcodec = f.get("vcodec")
            acodec = f.get("acodec")
            height = f.get("height") or 0

            # progressive mp4 (صوت+فيديو)
            if ext == "mp4" and vcodec not in (None, "none") and acodec not in (None, "none"):
                progressive.append({
                    "format_id": fid,
                    "ext": ext,
                    "height": height,
                    "fps": f.get("fps") or 0,
                    "tbr": f.get("tbr") or 0,
                    "filesize": f.get("filesize") or f.get("filesize_approx") or 0,
                    "label": f"{height}p MP4 (صوت+فيديو)",
                })

            # audio only
            if vcodec in (None, "none") and acodec not in (None, "none"):
                audio_only.append({
                    "format_id": fid,
                    "ext": ext,
                    "abr": f.get("abr") or 0,
                    "tbr": f.get("tbr") or 0,
                    "filesize": f.get("filesize") or f.get("filesize_approx") or 0,
                    "label": f"Audio ({ext})",
                })

        # ترتيب
        progressive.sort(key=lambda x: (x["height"], x["tbr"]), reverse=True)
        audio_only.sort(key=lambda x: (x.get("abr", 0), x.get("tbr", 0)), reverse=True)

        base["youtube_formats"] = progressive
        base["audio_formats"] = audio_only
        return base

    # باقي المنصات: بس خيارين (فيديو/صوت)
    best_video = _pick_best_generic_video(formats)
    best_audio = _pick_best_audio(formats)

    base["simple"] = {
        "video_available": bool(best_video),
        "audio_available": bool(best_audio),
        "video_ext": best_video.get("ext") if best_video else None,
        "audio_ext": best_audio.get("ext") if best_audio else None,
    }
    return base


async def _stream_with_range(request: Request, direct_url: str, filename: str):
    """
    ستريم حقيقي من الرابط المباشر مع دعم Range عشان التحميل ما يفشل في الجوال.
    """
    range_header = request.headers.get("range")
    headers = {"User-Agent": DEFAULT_UA}
    if range_header:
        headers["Range"] = range_header

    timeout = httpx.Timeout(connect=15, read=60, write=60, pool=15)
    client = httpx.AsyncClient(timeout=timeout, follow_redirects=True)

    try:
        upstream = await client.get(direct_url, headers=headers)
        if upstream.status_code not in (200, 206):
            raise HTTPException(status_code=502, detail=f"Upstream ردّ: {upstream.status_code}")

        content_type = upstream.headers.get("content-type") or "application/octet-stream"
        content_length = upstream.headers.get("content-length")
        accept_ranges = upstream.headers.get("accept-ranges")
        content_range = upstream.headers.get("content-range")

        resp_headers = {
            "Content-Type": content_type,
            "Content-Disposition": f'attachment; filename="{filename}"',
        }
        if content_length:
            resp_headers["Content-Length"] = content_length
        if accept_ranges:
            resp_headers["Accept-Ranges"] = accept_ranges
        if content_range:
            resp_headers["Content-Range"] = content_range

        async def gen():
            async for chunk in upstream.aiter_bytes(chunk_size=1024 * 256):
                yield chunk

        return StreamingResponse(
            gen(),
            status_code=upstream.status_code,
            headers=resp_headers,
        )
    finally:
        await client.aclose()


@app.get("/api/proxy")
async def proxy(
    request: Request,
    url: str = Query(..., min_length=5),
    type: str = Query("video", pattern="^(video|audio)$"),
    format_id: Optional[str] = Query(None),
    stream: int = Query(1),  # 1=ستريم (مناسب لأسلوب fetch/blob عندك)
    filename: Optional[str] = Query(None),
):
    want_audio = (type == "audio")

    # TikTok fallback سريع لو yt-dlp فشل أو منع
    if TIKTOK_RE.search(url):
        direct = await _tiktok_tikwm_direct(url, want_audio=want_audio)
        if direct:
            name = _safe_filename(filename or ("tiktok_audio" if want_audio else "tiktok_video"))
            ext = "mp3" if want_audio else "mp4"
            final_name = f"{name}.{ext}"
            if stream == 1:
                return await _stream_with_range(request, direct, final_name)
            return RedirectResponse(direct, status_code=302)

    info_dict = _extract_info(url)
    title = info_dict.get("title") or "Video"
    formats = info_dict.get("formats") or []

    chosen: Optional[Dict[str, Any]] = None

    if _is_youtube(url):
        # يوتيوب: لو format_id موجود (من /api/info) نستخدمه بشرط يكون progressive mp4 أو audio
        if format_id:
            for f in formats:
                if str(f.get("format_id")) == str(format_id):
                    chosen = f
                    break
        if not chosen:
            if want_audio:
                chosen = _pick_best_audio(formats)
            else:
                chosen = _pick_best_progressive_mp4(formats)
    else:
        # باقي المنصات: فيديو/صوت فقط
        if want_audio:
            chosen = _pick_best_audio(formats)
        else:
            chosen = _pick_best_generic_video(formats)

    if not chosen:
        raise HTTPException(status_code=404, detail="لم أجد رابط تحميل مناسب لهذا الفيديو.")

    direct_url = chosen.get("url")
    if not direct_url:
        raise HTTPException(status_code=502, detail="لم أحصل على رابط مباشر من المصدر.")

    # اسم ملف محترم
    name = _safe_filename(filename or title)
    ext = chosen.get("ext") or ("mp3" if want_audio else "mp4")
    # لو audio ext مش mp3، نخليه كما هو (مثلاً m4a)
    final_name = f"{name}.{ext}"

    # أهم نقطة: ستريم من سيرفرلس → يعمل مع fetch(blob) في نفس الصفحة
    if stream == 1:
        return await _stream_with_range(request, direct_url, final_name)

    # بديل: redirect
    return RedirectResponse(direct_url, status_code=302)