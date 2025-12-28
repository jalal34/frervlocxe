import re
import json
import urllib.parse
from typing import Optional, Dict, Any, List

import requests
from fastapi import FastAPI, Query, HTTPException
from fastapi.responses import JSONResponse, RedirectResponse
from yt_dlp import YoutubeDL

app = FastAPI()

DEFAULT_UA = (
    "Mozilla/5.0 (Linux; Android 13; Mobile) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Mobile Safari/537.36"
)

def is_youtube(url: str) -> bool:
    return bool(re.search(r"(youtube\.com|youtu\.be)", url, re.I))

def is_tiktok(url: str) -> bool:
    return bool(re.search(r"(tiktok\.com|vt\.tiktok\.com)", url, re.I))

def clean_filename(name: str) -> str:
    name = re.sub(r'[\\/:*?"<>|]+', "_", name)
    name = re.sub(r"\s+", " ", name).strip()
    return name[:150] if len(name) > 150 else name

def fmt_duration(seconds: Optional[int]) -> str:
    if not seconds:
        return ""
    m, s = divmod(int(seconds), 60)
    h, m = divmod(m, 60)
    if h:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m}:{s:02d}"

def extract_with_ytdlp(url: str) -> Dict[str, Any]:
    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
        "skip_download": True,
        "extract_flat": False,
        "http_headers": {"User-Agent": DEFAULT_UA},
    }
    with YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
    return info

def tiktok_via_tikwm(url: str) -> Dict[str, Any]:
    # TikWM API (بدون تنزيل على السيرفر)
    api = "https://www.tikwm.com/api/"
    params = {"url": url}
    r = requests.get(api, params=params, timeout=20, headers={"User-Agent": DEFAULT_UA})
    r.raise_for_status()
    data = r.json()
    if not data or data.get("code") != 0:
        raise HTTPException(status_code=400, detail="TikTok fetch failed (TikWM).")
    d = data.get("data") or {}

    # روابط مباشرة
    play = d.get("play") or ""   # فيديو بدون علامة مائية غالباً
    music = d.get("music") or "" # الصوت

    title = d.get("title") or "tiktok"
    cover = d.get("cover") or d.get("origin_cover") or ""

    return {
        "platform": "TikTok",
        "title": title,
        "thumbnail": cover,
        "duration": "",
        "views": "",
        "direct_video": play,
        "direct_audio": music,
    }

def pick_youtube_progressive_formats(info: Dict[str, Any]) -> List[Dict[str, Any]]:
    fmts = info.get("formats") or []
    out = []
    for f in fmts:
        vcodec = (f.get("vcodec") or "none")
        acodec = (f.get("acodec") or "none")
        # نريد فيديو+صوت معاً
        if vcodec != "none" and acodec != "none":
            # غالباً progressive mp4/webm
            out.append({
                "format_id": f.get("format_id"),
                "ext": f.get("ext"),
                "resolution": f.get("resolution") or f"{f.get('width','')}x{f.get('height','')}",
                "filesize": f.get("filesize") or f.get("filesize_approx"),
                "url": f.get("url"),
            })
    # ترتيب من الأعلى جودة تقريباً
    def score(x):
        res = x.get("resolution") or ""
        m = re.search(r"(\d+)\s*x\s*(\d+)", res)
        if m:
            return int(m.group(2))
        m2 = re.search(r"(\d+)p", res)
        if m2:
            return int(m2.group(1))
        return 0

    out.sort(key=score, reverse=True)
    # نرجّع عدد معقول
    return out[:15]

@app.get("/api/health")
def health():
    return {"ok": True}

@app.get("/api/info")
def info(url: str = Query(..., min_length=5)):
    url = url.strip()

    # TikTok مسار خاص
    if is_tiktok(url):
        t = tiktok_via_tikwm(url)
        return {
            "title": t["title"],
            "thumbnail": t["thumbnail"],
            "duration": t["duration"],
            "platform": t["platform"],
            "views": t["views"],
            "youtube_formats": [],
        }

    # باقي المواقع عبر yt-dlp
    try:
        data = extract_with_ytdlp(url)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"extract_info failed: {str(e)}")

    title = data.get("title") or "video"
    thumbnail = data.get("thumbnail") or ""
    duration = fmt_duration(data.get("duration"))
    extractor = (data.get("extractor_key") or data.get("extractor") or "").lower()
    platform = extractor.upper() if extractor else "UNKNOWN"

    youtube_formats = []
    if is_youtube(url):
        youtube_formats = pick_youtube_progressive_formats(data)

    return {
        "title": title,
        "thumbnail": thumbnail,
        "duration": duration,
        "platform": platform,
        "youtube_formats": youtube_formats,
    }

@app.get("/api/proxy")
def proxy(
    url: str = Query(..., min_length=5),
    type: str = Query("video"),
    format_id: Optional[str] = Query(None),
    filename: Optional[str] = Query(None),
):
    url = url.strip()
    type = (type or "video").lower()
    if type not in ("video", "audio"):
        type = "video"

    # TikTok via TikWM direct
    if is_tiktok(url):
        t = tiktok_via_tikwm(url)
        direct = t["direct_video"] if type == "video" else t["direct_audio"]
        if not direct:
            raise HTTPException(status_code=400, detail="No direct TikTok link found.")
        return RedirectResponse(direct, status_code=302)

    # YouTube / Others via yt-dlp
    try:
        data = extract_with_ytdlp(url)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"extract_info failed: {str(e)}")

    # لو يوتيوب + format_id محدد: نوجّه له مباشرة بشرط يكون فيه صوت+فيديو
    if is_youtube(url):
        fmts = data.get("formats") or []
        if format_id:
            chosen = None
            for f in fmts:
                if str(f.get("format_id")) == str(format_id):
                    # لازم audio+video
                    if (f.get("vcodec") != "none") and (f.get("acodec") != "none") and f.get("url"):
                        chosen = f
                        break
            if not chosen:
                raise HTTPException(status_code=400, detail="Invalid YouTube format_id (must include audio+video).")
            return RedirectResponse(chosen["url"], status_code=302)

        # لو ماحدد format_id:
        if type == "audio":
            # صوت بدون تحويل (m4a/webm audio) – بدون ffmpeg
            # نختار bestaudio
            for f in fmts:
                if f.get("acodec") != "none" and f.get("vcodec") == "none" and f.get("url"):
                    return RedirectResponse(f["url"], status_code=302)
            raise HTTPException(status_code=400, detail="No audio format found for YouTube.")

        # video: نختار أفضل progressive (صوت+فيديو)
        progressive = pick_youtube_progressive_formats(data)
        if not progressive:
            raise HTTPException(status_code=400, detail="No progressive (audio+video) formats found for YouTube.")
        return RedirectResponse(progressive[0]["url"], status_code=302)

    # باقي المواقع (انستا/فيس/تويتر/سناب/بنترست...) :
    fmts = data.get("formats") or []
    if not fmts:
        raise HTTPException(status_code=400, detail="No formats found.")

    # audio:
    if type == "audio":
        # اختر أول مسار صوتي مباشر
        for f in fmts:
            if f.get("vcodec") == "none" and f.get("acodec") != "none" and f.get("url"):
                return RedirectResponse(f["url"], status_code=302)
        # fallback: أحياناً ما في صوت منفصل، نحاول نرجع فيديو فيه صوت
        for f in fmts:
            if f.get("vcodec") != "none" and f.get("acodec") != "none" and f.get("url"):
                return RedirectResponse(f["url"], status_code=302)
        raise HTTPException(status_code=400, detail="No audio link found.")

    # video:
    # اختر فيديو فيه صوت (أفضل للمستخدم) بدل bestvideo-only
    for f in fmts:
        if f.get("vcodec") != "none" and f.get("acodec") != "none" and f.get("url"):
            return RedirectResponse(f["url"], status_code=302)

    # fallback لأي فيديو حتى لو بدون صوت
    for f in fmts:
        if f.get("vcodec") != "none" and f.get("url"):
            return RedirectResponse(f["url"], status_code=302)

    raise HTTPException(status_code=400, detail="No video link found.")