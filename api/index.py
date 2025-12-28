from __future__ import annotations

import re
from typing import Any, Dict, Optional, Tuple

import httpx
import requests
import yt_dlp
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse, StreamingResponse

app = FastAPI()

<<<<<<< HEAD
# -----------------------------
# Helpers
# -----------------------------


def _is_tiktok(url: str) -> bool:
    u = url.lower()
    return ("tiktok.com" in u) or ("vt.tiktok.com" in u) or ("vm.tiktok.com" in u)


def _sanitize_filename(name: str) -> str:
    name = (name or "download").strip()
    name = re.sub(r'[\\/*?:"<>|]+', "", name)
=======
# ----------------------------
# Utils
# ----------------------------

UA = (
    "Mozilla/5.0 (Linux; Android 13) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36"
)

def _is_tiktok(url: str) -> bool:
    return bool(re.search(r"(?:^|\/\/)(?:www\.)?(?:tiktok\.com|vt\.tiktok\.com)", url))

def _clean_filename(name: str) -> str:
    name = (name or "download").strip()
    name = re.sub(r'[\\/*?:"<>|]', "", name)
>>>>>>> 6293580 (Fix API downloader + fix proxy download urls)
    name = re.sub(r"\s+", " ", name).strip()
    if not name:
        name = "download"
    return name[:120]

<<<<<<< HEAD

def _pick_best_youtube_with_audio(info: dict) -> Optional[str]:
    """
    YouTube: Prefer a progressive MP4 (video+audio) when possible.
    If none exists, return None and let /proxy pick a merged format fallback strategy.
    """
    formats = info.get("formats") or []
    progressive = []
    for f in formats:
        # progressive usually has both acodec and vcodec not "none"
        v = f.get("vcodec")
        a = f.get("acodec")
        url = f.get("url")
        ext = f.get("ext")
        if not url:
            continue
        if v and v != "none" and a and a != "none":
            progressive.append(f)

    # Prefer mp4 progressive with highest resolution/bitrate
    mp4_prog = [f for f in progressive if (f.get("ext") == "mp4")]
    pool = mp4_prog or progressive
    if not pool:
        return None

    def score(f):
        h = f.get("height") or 0
        tbr = f.get("tbr") or 0
        return (h, tbr)

    pool.sort(key=score, reverse=True)
    return pool[0].get("url")


def _pick_best_audio(info: dict) -> Optional[str]:
    formats = info.get("formats") or []
    audios = []
    for f in formats:
        url = f.get("url")
        if not url:
            continue
        if f.get("vcodec") == "none":
            audios.append(f)

    if not audios:
        return None

    def score(f):
        abr = f.get("abr") or 0
        asr = f.get("asr") or 0
        return (abr, asr)

    audios.sort(key=score, reverse=True)
    return audios[0].get("url")


async def _stream_remote(url: str):
    """
    Stream bytes from remote URL without saving to disk.
    """
    async with httpx.AsyncClient(follow_redirects=True, timeout=60.0) as client:
        async with client.stream("GET", url) as r:
            r.raise_for_status()
            async for chunk in r.aiter_bytes(chunk_size=1024 * 256):
                yield chunk


def _yt_dlp_extract(url: str) -> dict:
    """
    Extract metadata without downloading.
    """
    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "noplaylist": True,
        # Reduce bans: set a common UA + headers
        "http_headers": {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            )
        },
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        return ydl.extract_info(url, download=False)


def _normalize_info(info: dict) -> dict:
    """
    Return only what frontend needs.
    """
    title = info.get("title") or "download"
    thumb = info.get("thumbnail")
    extractor = info.get("extractor_key") or info.get("extractor") or ""
    webpage_url = info.get("webpage_url") or info.get("original_url") or info.get("url")

    return {
        "title": title,
        "thumbnail": thumb,
        "extractor": extractor,
        "webpage_url": webpage_url,
        "formats_count": len(info.get("formats") or []),
    }


# -----------------------------
# TikTok via TikWM
# -----------------------------


def _tikwm_info(url: str) -> dict:
    """
    TikTok: Use TikWM API to avoid bans / rate limits.
    """
    api = "https://www.tikwm.com/api/"
    try:
        r = requests.post(api, data={"url": url}, timeout=20)
        r.raise_for_status()
        payload = r.json()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"TikTok API error: {e}")

    data = payload.get("data") or {}
    if not data:
        raise HTTPException(status_code=400, detail="TikTok API returned no data")

    # direct links
    video_no_watermark = data.get("play")  # usually no watermark
    video_watermark = data.get("wmplay")
    music = data.get("music")

    title = data.get("title") or "tiktok"
    cover = data.get("cover") or data.get("origin_cover") or data.get("ai_dynamic_cover")

    return {
        "title": title,
        "thumbnail": cover,
        "video": video_no_watermark or video_watermark,
        "audio": music,
        "extractor": "TikTok",
        "webpage_url": url,
    }


# -----------------------------
# Endpoints
# -----------------------------


@app.get("/api/health")
def health():
    return {"ok": True}


@app.get("/api/info")
def info(url: str = Query(..., min_length=4)):
    """
    Get metadata for UI: title, thumbnail.
    For TikTok, use TikWM, else yt-dlp.
    """
    try:
        if _is_tiktok(url):
            t = _tikwm_info(url)
            return JSONResponse(
                {
                    "title": t["title"],
                    "thumbnail": t["thumbnail"],
                    "extractor": t["extractor"],
                    "webpage_url": t["webpage_url"],
                    "tiktok": True,
                }
            )

        info_dict = _yt_dlp_extract(url)
        return JSONResponse({**_normalize_info(info_dict), "tiktok": False})
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/proxy")
async def proxy(
    url: str = Query(..., min_length=4),
    kind: Literal["video", "audio"] = Query("video"),
    stream: int = Query(
        1,
        description="1=stream as attachment (download instantly), 0=redirect to direct CDN link",
    ),
):
    """
    Generate a direct download behavior without writing files to disk.

    - For TikTok: via TikWM (video/audio direct).
    - For YouTube:
        - video: prefer progressive mp4 with audio, otherwise let yt-dlp provide best merged target URL if available
        - audio: pick best audio-only
    - For others (IG/FB/Twitter/etc): use yt-dlp extracted direct URL for best match.
    """
    try:
        final_name = "download.bin"
        direct = None

        if _is_tiktok(url):
            t = _tikwm_info(url)
            title = _sanitize_filename(t.get("title"))
            if kind == "audio":
                direct = t.get("audio")
                final_name = f"{title}.mp3"
            else:
                direct = t.get("video")
                final_name = f"{title}.mp4"

            if not direct:
                raise HTTPException(status_code=400, detail="No direct TikTok link found")

        else:
            info_dict = _yt_dlp_extract(url)
            title = _sanitize_filename(info_dict.get("title") or "download")

            # YouTube special preference
            is_youtube = (info_dict.get("extractor_key") or "").lower() in ("youtube", "youtube:tab", "youtube:shorts")
            if is_youtube:
                if kind == "audio":
                    direct = _pick_best_audio(info_dict)
                    final_name = f"{title}.m4a"
                else:
                    direct = _pick_best_youtube_with_audio(info_dict)
                    # If no progressive exists, fall back to the best single url (may be video-only for some cases)
                    if not direct:
                        # fallback: best format url from yt-dlp's selected best
                        direct = info_dict.get("url")
                    final_name = f"{title}.mp4"
            else:
                # Generic: pick best based on kind
                if kind == "audio":
                    direct = _pick_best_audio(info_dict) or info_dict.get("url")
                    final_name = f"{title}.m4a"
                else:
                    # Prefer non-audio-only format
                    formats = info_dict.get("formats") or []
                    candidates = []
                    for f in formats:
                        if not f.get("url"):
                            continue
                        if kind == "video" and f.get("vcodec") and f.get("vcodec") != "none":
                            candidates.append(f)

                    if candidates:
                        def score(f):
                            h = f.get("height") or 0
                            tbr = f.get("tbr") or 0
                            return (h, tbr)

                        candidates.sort(key=score, reverse=True)
                        direct = candidates[0].get("url")
                    else:
                        direct = info_dict.get("url")
                    final_name = f"{title}.mp4"

            if not direct:
                raise HTTPException(status_code=400, detail="No direct link found for this URL")

        # Option 1: Redirect to direct CDN link (some browsers open new tab)
=======
def _human_duration(seconds: Optional[int]) -> str:
    if not seconds or seconds <= 0:
        return ""
    m, s = divmod(int(seconds), 60)
    h, m = divmod(m, 60)
    if h:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m}:{s:02d}"

def _pick_best_video_with_audio(info: Dict[str, Any]) -> Tuple[Optional[str], Dict[str, str]]:
    """
    Pick a direct media URL that already contains audio (no merging).
    Prefer MP4 with audio.
    Returns (url, headers)
    """
    formats = info.get("formats") or []
    best = None
    best_score = -1

    for f in formats:
        u = f.get("url")
        if not u:
            continue
        vcodec = (f.get("vcodec") or "").lower()
        acodec = (f.get("acodec") or "").lower()
        if vcodec == "none" or acodec == "none":
            continue  # must contain both video+audio
        ext = (f.get("ext") or "").lower()
        height = f.get("height") or 0
        tbr = f.get("tbr") or 0.0

        # Score: prefer mp4, then higher resolution, then bitrate
        score = 0
        if ext == "mp4":
            score += 100000
        score += int(height) * 100
        score += int(tbr)

        if score > best_score:
            best_score = score
            best = f

    if best and best.get("url"):
        headers = info.get("http_headers") or {}
        return best["url"], headers

    # Fallback: sometimes info has a direct "url"
    u = info.get("url")
    if u:
        headers = info.get("http_headers") or {}
        return u, headers

    return None, {}

def _pick_best_audio(info: Dict[str, Any]) -> Tuple[Optional[str], Dict[str, str]]:
    formats = info.get("formats") or []
    best = None
    best_score = -1

    for f in formats:
        u = f.get("url")
        if not u:
            continue
        vcodec = (f.get("vcodec") or "").lower()
        acodec = (f.get("acodec") or "").lower()
        if vcodec != "none":
            continue  # audio only
        if acodec == "none":
            continue

        ext = (f.get("ext") or "").lower()
        abr = f.get("abr") or 0.0

        score = 0
        # Prefer m4a then mp3 then anything
        if ext == "m4a":
            score += 100000
        elif ext == "mp3":
            score += 90000
        score += int(abr)

        if score > best_score:
            best_score = score
            best = f

    if best and best.get("url"):
        headers = info.get("http_headers") or {}
        return best["url"], headers

    return None, {}

def _yt_dlp_extract(url: str) -> Dict[str, Any]:
    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
        "skip_download": True,
        "nocheckcertificate": True,
        # Some platforms need a modern UA
        "http_headers": {"User-Agent": UA},
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        return ydl.extract_info(url, download=False)

async def _tikwm_info(url: str) -> Dict[str, Any]:
    """
    TikTok fallback via TikWM (helps reduce TikTok blocks).
    """
    api = "https://www.tikwm.com/api/"
    async with httpx.AsyncClient(timeout=20.0, headers={"User-Agent": UA}) as client:
        r = await client.get(api, params={"url": url})
        r.raise_for_status()
        j = r.json()

    data = j.get("data") or {}
    title = data.get("title") or "TikTok"
    thumb = data.get("cover") or data.get("origin_cover") or ""
    play = data.get("play") or ""   # video direct
    music = data.get("music") or "" # audio direct

    return {
        "title": title,
        "thumbnail": thumb,
        "duration": "",
        "direct_video": play,
        "direct_audio": music,
        "http_headers": {"User-Agent": UA, "Referer": "https://www.tiktok.com/"},
    }

def _stream_remote(url: str, headers: Optional[Dict[str, str]] = None):
    """
    Stream remote file -> client (works on Vercel without writing to disk)
    """
    h = {"User-Agent": UA}
    if headers:
        # merge but keep a UA
        h.update(headers)
        h.setdefault("User-Agent", UA)

    with requests.get(url, headers=h, stream=True, timeout=30) as r:
        r.raise_for_status()
        for chunk in r.iter_content(chunk_size=1024 * 256):
            if chunk:
                yield chunk

def _attachment_headers(filename: str) -> Dict[str, str]:
    safe = _clean_filename(filename)
    # We don’t force extension here because platforms vary (mp4/m4a etc.)
    return {
        "Content-Disposition": f'attachment; filename="{safe}"',
        "Cache-Control": "no-store",
    }

# ----------------------------
# Routes (both /api/* and /* to be safe on Vercel)
# ----------------------------

@app.get("/api/health")
@app.get("/health")
def health():
    return {"ok": True}

@app.get("/api/download")
@app.get("/download")
def download_info(url: str = Query(..., min_length=5)):
    """
    Returns basic metadata for the frontend
    """
    try:
        if _is_tiktok(url):
            # TikTok: use TikWM first (more stable)
            # (If it fails, fallback to yt-dlp)
            try:
                info = httpx.run  # just to satisfy static check (unused)
            except Exception:
                pass

        # Try TikTok via TikWM (async) in a sync endpoint:
        if _is_tiktok(url):
            try:
                tik = httpx.AsyncClient  # dummy for type
            except Exception:
                pass

            # run async in sync safely
            try:
                import anyio
                tikinfo = anyio.run(_tikwm_info, url)
                return JSONResponse(
                    {
                        "status": "success",
                        "data": {
                            "title": tikinfo.get("title", "TikTok"),
                            "thumbnail": tikinfo.get("thumbnail", ""),
                            "duration": tikinfo.get("duration", ""),
                            "download_url": url,
                        },
                    }
                )
            except Exception:
                # fallback to yt-dlp
                pass

        info = _yt_dlp_extract(url)
        title = info.get("title") or "Video"
        thumb = info.get("thumbnail") or ""
        duration = _human_duration(info.get("duration"))

        return JSONResponse(
            {
                "status": "success",
                "data": {
                    "title": title,
                    "thumbnail": thumb,
                    "duration": duration,
                    "download_url": url,
                },
            }
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/proxy")
@app.get("/proxy")
def proxy_download(
    url: str = Query(..., min_length=5),
    type: str = Query("video", pattern="^(video|audio)$"),
    stream: int = Query(1),
    filename: str = Query("download"),
):
    """
    Streams the final media back to browser so the download happens directly (no new page).
    Frontend uses fetch() -> blob -> save.
    """
    try:
        # TikTok: try TikWM direct links
        if _is_tiktok(url):
            try:
                import anyio
                tik = anyio.run(_tikwm_info, url)
                direct_video = tik.get("direct_video")
                direct_audio = tik.get("direct_audio")
                headers = tik.get("http_headers") or {"User-Agent": UA}

                direct = direct_video if type == "video" else direct_audio
                if not direct:
                    raise Exception("TikTok direct link not found")

                final_name = _clean_filename(filename)
                headers_out = _attachment_headers(final_name)
                return StreamingResponse(
                    _stream_remote(direct, headers=headers),
                    media_type="application/octet-stream",
                    headers=headers_out,
                )
            except Exception:
                # fallback to yt-dlp below
                pass

        info = _yt_dlp_extract(url)

        if type == "audio":
            direct, h = _pick_best_audio(info)
        else:
            direct, h = _pick_best_video_with_audio(info)

        if not direct:
            raise HTTPException(status_code=400, detail="Could not find a direct downloadable stream for this link.")

        final_name = _clean_filename(filename)
        headers_out = _attachment_headers(final_name)

        # stream=1 always streams; kept for compatibility
>>>>>>> 6293580 (Fix API downloader + fix proxy download urls)
        if stream == 0:
            # still stream to keep same behavior (no redirects)
            pass

<<<<<<< HEAD
        # Option 2: Stream as attachment (forces download in same tab typically)
        headers = {
            "Content-Disposition": f'attachment; filename="{final_name}"',
            "Cache-Control": "no-store",
        }
        return StreamingResponse(_stream_remote(direct), media_type="application/octet-stream", headers=headers)
=======
        return StreamingResponse(
            _stream_remote(direct, headers=h),
            media_type="application/octet-stream",
            headers=headers_out,
        )
>>>>>>> 6293580 (Fix API downloader + fix proxy download urls)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))