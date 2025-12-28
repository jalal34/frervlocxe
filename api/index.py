from fastapi import FastAPI, Query
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
import yt_dlp
import re
import requests
import time
import urllib.parse

app = FastAPI()

# CORS (اختياري لكنه مفيد للـ fetch)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

UA = "Mozilla/5.0 (Linux; Android 13) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0 Mobile Safari/537.36"

def guess_platform(url: str) -> str:
    u = url.lower()
    if "tiktok.com" in u or "vt.tiktok.com" in u:
        return "TikTok"
    if "youtube.com" in u or "youtu.be" in u:
        return "YouTube"
    if "instagram.com" in u:
        return "Instagram"
    if "facebook.com" in u or "fb.watch" in u:
        return "Facebook"
    if "twitter.com" in u or "x.com" in u:
        return "Twitter/X"
    if "snapchat.com" in u:
        return "Snapchat"
    if "pinterest." in u:
        return "Pinterest"
    if "vimeo.com" in u:
        return "Vimeo"
    return "Unknown"

def safe_filename(name: str, default: str = "video") -> str:
    if not name:
        name = default
    name = re.sub(r"[\\/:*?\"<>|]+", "", name)
    name = re.sub(r"\s+", " ", name).strip()
    if len(name) > 120:
        name = name[:120]
    return name or default

def secs_to_hhmmss(sec: int) -> str:
    if not sec:
        return ""
    h = sec // 3600
    m = (sec % 3600) // 60
    s = sec % 60
    return f"{h:02d}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"

def ydl_base_opts():
    return {
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
        "nocheckcertificate": True,
        "geo_bypass": True,
        "http_headers": {
            "User-Agent": UA,
            "Accept-Language": "en-US,en;q=0.9,ar;q=0.8",
        },
        # مهم: لا تحميل على القرص
        "skip_download": True,
    }

def extract_info(url: str):
    opts = ydl_base_opts()
    with yt_dlp.YoutubeDL(opts) as ydl:
        return ydl.extract_info(url, download=False)

def pick_best_format(info: dict, want_audio: bool):
    """
    يرجع (direct_url, ext, is_audio_only)
    """
    # إذا yt-dlp أعطى url مباشر على مستوى root (أحيانًا)
    if info.get("url") and isinstance(info.get("url"), str):
        return info["url"], (info.get("ext") or ""), want_audio

    fmts = info.get("formats") or []
    if not fmts:
        return None, "", want_audio

    def score(f):
        # نفضل https + وجود filesize/height
        s = 0
        if (f.get("protocol") or "").startswith("https"):
            s += 5
        if f.get("filesize") or f.get("filesize_approx"):
            s += 2
        if f.get("tbr"):
            s += 1
        return s

    if want_audio:
        # أفضل صوت فقط
        audios = [f for f in fmts if f.get("vcodec") == "none" and f.get("url")]
        # نفضل m4a/mp3/aac
        def audio_rank(f):
            ext = (f.get("ext") or "").lower()
            abr = f.get("abr") or 0
            r = score(f) + (abr / 64)
            if ext in ["m4a", "mp3", "aac", "opus", "webm"]:
                r += 3
            return r
        audios.sort(key=audio_rank, reverse=True)
        if audios:
            f = audios[0]
            return f["url"], (f.get("ext") or ""), True

    # فيديو: نفضل progressive mp4 (صوت+فيديو) أولاً لأنه أسهل للتحميل المباشر
    progressive = [f for f in fmts if f.get("acodec") != "none" and f.get("vcodec") != "none" and f.get("url")]
    def prog_rank(f):
        ext = (f.get("ext") or "").lower()
        h = f.get("height") or 0
        r = score(f) + h / 240
        if ext == "mp4":
            r += 4
        return r
    progressive.sort(key=prog_rank, reverse=True)
    if progressive:
        f = progressive[0]
        return f["url"], (f.get("ext") or ""), False

    # إذا ما فيه progressive، نأخذ أفضل فيديو فقط (قد يكون بدون صوت)
    videos = [f for f in fmts if f.get("vcodec") != "none" and f.get("url")]
    def video_rank(f):
        ext = (f.get("ext") or "").lower()
        h = f.get("height") or 0
        r = score(f) + h / 240
        if ext == "mp4":
            r += 2
        return r
    videos.sort(key=video_rank, reverse=True)
    if videos:
        f = videos[0]
        return f["url"], (f.get("ext") or ""), False

    # fallback
    anyf = [f for f in fmts if f.get("url")]
    anyf.sort(key=score, reverse=True)
    if anyf:
        f = anyf[0]
        return f["url"], (f.get("ext") or ""), want_audio

    return None, "", want_audio

def tiktok_fallback_tikwm(url: str, want_audio: bool):
    """
    fallback محترم لـ TikTok في حال yt-dlp فشل.
    TikWM يعطينا روابط مباشرة.
    """
    api = "https://www.tikwm.com/api/"
    params = {"url": url}
    r = requests.get(api, params=params, timeout=15, headers={"User-Agent": UA})
    r.raise_for_status()
    data = r.json()
    if not data or "data" not in data:
        return None

    d = data["data"]
    if want_audio:
        # music (mp3 غالباً)
        return d.get("music")

    # فيديو بدون علامة مائية غالباً
    # بعض الأحيان key = play
    return d.get("play") or d.get("wmplay")

@app.get("/api/health")
def health():
    return {"ok": True, "ts": int(time.time())}

@app.get("/api/info")
def info(url: str = Query(..., description="Video URL")):
    platform = guess_platform(url)
    try:
        info_dict = extract_info(url)
        title = info_dict.get("title") or "video"
        thumb = info_dict.get("thumbnail") or ""
        duration = secs_to_hhmmss(info_dict.get("duration") or 0)

        return JSONResponse({
            "title": title,
            "thumbnail": thumb,
            "duration": duration,
            "platform": platform,
            "views": str(info_dict.get("view_count")) if info_dict.get("view_count") else None
        })
    except Exception as e:
        # TikTok fallback for info too
        if platform == "TikTok":
            try:
                api = "https://www.tikwm.com/api/"
                r = requests.get(api, params={"url": url}, timeout=15, headers={"User-Agent": UA})
                r.raise_for_status()
                data = r.json().get("data", {})
                title = data.get("title") or "TikTok video"
                thumb = data.get("cover") or ""
                return JSONResponse({
                    "title": title,
                    "thumbnail": thumb,
                    "duration": "",
                    "platform": platform,
                    "views": None
                })
            except:
                pass

        return JSONResponse({"error": "تعذر جلب الفيديو. جرّب رابط آخر أو أعد المحاولة."}, status_code=400)

@app.get("/api/proxy")
def proxy(
    url: str = Query(...),
    type: str = Query("video", regex="^(video|audio)$"),
    stream: int = Query(1),
    filename: str = Query("video")
):
    want_audio = (type == "audio")
    platform = guess_platform(url)

    # اسم ملف نظيف
    base_name = safe_filename(filename, "video")
    # امتداد افتراضي
    default_ext = "mp3" if want_audio else "mp4"
    download_name = f"{base_name}.{default_ext}"

    try:
        # YouTube: نختار format يدعم صوت+فيديو إذا ممكن
        info_dict = extract_info(url)

        direct_url, ext, is_audio_only = pick_best_format(info_dict, want_audio)
        if not direct_url:
            raise RuntimeError("No direct URL found")

        # امتداد أدق
        if ext:
            download_name = f"{base_name}.{ext}"

        # Redirect مباشر
        resp = RedirectResponse(direct_url, status_code=302)

        # يجبر المتصفح ينزّل (قد تتجاهله بعض CDNs لكن يفيد كثير)
        quoted = urllib.parse.quote(download_name)
        resp.headers["Content-Disposition"] = f"attachment; filename*=UTF-8''{quoted}"
        resp.headers["Cache-Control"] = "no-store"
        return resp

    except Exception:
        # TikTok fallback
        if platform == "TikTok":
            try:
                direct = tiktok_fallback_tikwm(url, want_audio)
                if direct:
                    download_name = f"{base_name}.mp3" if want_audio else f"{base_name}.mp4"
                    resp = RedirectResponse(direct, status_code=302)
                    quoted = urllib.parse.quote(download_name)
                    resp.headers["Content-Disposition"] = f"attachment; filename*=UTF-8''{quoted}"
                    resp.headers["Cache-Control"] = "no-store"
                    return resp
            except:
                pass

        return JSONResponse(
            {"error": "فشل التحميل: المنصة منعت الوصول أو الرابط غير مدعوم حاليا على Vercel."},
            status_code=400
        )