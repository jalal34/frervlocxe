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


def _is_tiktok(url: str) -> bool:
    u = url.lower()
    return ("tiktok.com" in u) or ("vt.tiktok.com" in u) or ("vm.tiktok.com" in u)


def _sanitize_filename(name: str) -> str:
    name = (name or "download").strip()
    name = re.sub(r'[\\/*?:"<>|]+', "", name)
    name = re.sub(r"\s+", " ", name).strip()
    if not name:
        name = "download"
    return name[:120]


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
        if stream == 0:
            return RedirectResponse(url=direct)

        # Option 2: Stream as attachment (forces download in same tab typically)
        headers = {
            "Content-Disposition": f'attachment; filename="{final_name}"',
            "Cache-Control": "no-store",
        }
        return StreamingResponse(_stream_remote(direct), media_type="application/octet-stream", headers=headers)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
