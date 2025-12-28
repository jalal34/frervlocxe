from fastapi import FastAPI, Query, HTTPException
from fastapi.responses import JSONResponse, RedirectResponse
import yt_dlp
import requests
import re
import urllib.parse

app = FastAPI()

# Headers ثابتة لتقليل الحظر
UA = "Mozilla/5.0 (Linux; Android 13; Mobile) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0 Safari/537.36"
COMMON_HEADERS = {
    "User-Agent": UA,
    "Accept": "*/*",
    "Accept-Language": "en-US,en;q=0.9,ar;q=0.8",
    "Cache-Control": "no-cache",
    "Pragma": "no-cache",
}

def is_tiktok(url: str) -> bool:
    u = url.lower()
    return ("tiktok.com" in u) or ("vm.tiktok.com" in u) or ("vt.tiktok.com" in u)

def is_youtube(url: str) -> bool:
    u = url.lower()
    return ("youtube.com" in u) or ("youtu.be" in u)

def safe_filename(name: str) -> str:
    # اسم ملف نظيف
    name = re.sub(r"[\\/*?:\"<>|]+", "", name)
    name = name.strip()
    if not name:
        name = "download"
    return name[:120]

def tikwm_resolve(url: str, want: str):
    """
    TikWM API (عادة يعطي فيديو بدون علامة + رابط صوت)
    """
    try:
        api = "https://www.tikwm.com/api/"
        r = requests.get(api, params={"url": url}, headers=COMMON_HEADERS, timeout=20)
        r.raise_for_status()
        j = r.json()
        if not j or j.get("code") != 0:
            return None

        data = j.get("data") or {}
        title = data.get("title") or "tiktok"
        cover = data.get("cover") or data.get("origin_cover") or ""
        # TikWM غالبًا:
        # play = بدون واترمارك
        # music = mp3
        video_link = data.get("play") or data.get("wmplay") or data.get("hdplay")
        audio_link = data.get("music")

        if want == "audio":
            if audio_link:
                return {
                    "direct_url": audio_link,
                    "title": title,
                    "thumbnail": cover,
                    "ext": "mp3",
                }
        else:
            if video_link:
                return {
                    "direct_url": video_link,
                    "title": title,
                    "thumbnail": cover,
                    "ext": "mp4",
                }
        return None
    except Exception:
        return None

def ytdlp_extract(url: str):
    opts = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "noplaylist": True,
        "nocheckcertificate": True,
        "geo_bypass": True,
        "http_headers": COMMON_HEADERS,
        # تقلّل مشاكل بعض المواقع
        "extractor_args": {
            "youtube": {"player_client": ["android", "web"]},
        },
    }
    with yt_dlp.YoutubeDL(opts) as ydl:
        return ydl.extract_info(url, download=False)

def pick_best_non_youtube(info, want: str):
    """
    لغير اليوتيوب: نختار أفضل رابط مباشر من formats
    """
    formats = info.get("formats") or []
    if not formats:
        # أحيانًا url مباشر يكون في info['url']
        if info.get("url"):
            return info["url"], "mp4"
        return None, None

    if want == "audio":
        # أفضل صوت
        aud = [f for f in formats if f.get("acodec") and f.get("acodec") != "none" and (f.get("vcodec") in (None, "none"))]
        if not aud:
            # fallback: أي شيء فيه صوت
            aud = [f for f in formats if f.get("acodec") and f.get("acodec") != "none"]
        aud.sort(key=lambda x: (x.get("abr") or 0, x.get("filesize") or 0), reverse=True)
        f = aud[0] if aud else None
        if not f or not f.get("url"):
            return None, None
        ext = f.get("ext") or "m4a"
        return f["url"], ext

    # فيديو: نفضّل mp4 وفيه صوت إن وجد (progressive)
    vids = [f for f in formats if f.get("vcodec") and f.get("vcodec") != "none"]
    # نفضّل اللي فيه صوت (acodec != none) عشان يكون "ينزل ويشتغل"
    with_audio = [f for f in vids if f.get("acodec") and f.get("acodec") != "none"]
    cand = with_audio if with_audio else vids

    # نفضّل mp4
    mp4 = [f for f in cand if (f.get("ext") == "mp4")]
    cand2 = mp4 if mp4 else cand

    cand2.sort(key=lambda x: (x.get("height") or 0, x.get("tbr") or 0, x.get("filesize") or 0), reverse=True)
    f = cand2[0] if cand2 else None
    if not f or not f.get("url"):
        return None, None
    ext = f.get("ext") or "mp4"
    return f["url"], ext

def youtube_format_list(info):
    """
    نرجّع فقط صيغ "فيديو وفيه صوت" (progressive) حتى يشتغل على طول
    + خيار صوت فقط
    """
    formats = info.get("formats") or []
    result = []

    # فيديو + صوت (acodec != none AND vcodec != none)
    av = [
        f for f in formats
        if f.get("vcodec") not in (None, "none")
        and f.get("acodec") not in (None, "none")
        and f.get("url")
    ]

    # نرتّب حسب الجودة
    av.sort(key=lambda x: (x.get("height") or 0, x.get("tbr") or 0), reverse=True)

    for f in av:
        fid = f.get("format_id")
        height = f.get("height")
        ext = f.get("ext") or "mp4"
        fps = f.get("fps")
        label = f"{height}p" if height else "video"
        if fps:
            label += f" {fps}fps"
        result.append({
            "format_id": fid,
            "type": "video",
            "ext": ext,
            "label": label,
        })

    # صوت فقط
    aud = [
        f for f in formats
        if f.get("vcodec") in (None, "none")
        and f.get("acodec") not in (None, "none")
        and f.get("url")
    ]
    aud.sort(key=lambda x: (x.get("abr") or 0), reverse=True)
    for f in aud[:6]:
        fid = f.get("format_id")
        abr = f.get("abr") or ""
        ext = f.get("ext") or "m4a"
        result.append({
            "format_id": fid,
            "type": "audio",
            "ext": ext,
            "label": f"audio {abr}kbps".strip(),
        })

    # لو ما لقينا progressive (أحيانًا)، نخلي best كحل أخير
    if not av:
        result.insert(0, {"format_id": "best", "type": "video", "ext": "mp4", "label": "best (auto)"})

    if not aud:
        result.append({"format_id": "bestaudio", "type": "audio", "ext": "m4a", "label": "audio (auto)"})

    return result

def youtube_pick_url(info, want: str, format_id: str):
    formats = info.get("formats") or []
    if format_id in ("best", "bestaudio"):
        # نختار تلقائي من القائمة أعلاه
        if want == "audio":
            for f in formats:
                if f.get("vcodec") in (None, "none") and f.get("acodec") not in (None, "none") and f.get("url"):
                    return f["url"], (f.get("ext") or "m4a")
            return None, None
        else:
            # progressive أولاً
            av = [f for f in formats if f.get("vcodec") not in (None, "none") and f.get("acodec") not in (None, "none") and f.get("url")]
            av.sort(key=lambda x: (x.get("height") or 0, x.get("tbr") or 0), reverse=True)
            if av:
                f = av[0]
                return f["url"], (f.get("ext") or "mp4")
            # fallback لأي فيديو
            v = [f for f in formats if f.get("vcodec") not in (None, "none") and f.get("url")]
            v.sort(key=lambda x: (x.get("height") or 0, x.get("tbr") or 0), reverse=True)
            if v:
                f = v[0]
                return f["url"], (f.get("ext") or "mp4")
            return None, None

    # اختيار format_id بعينه
    for f in formats:
        if str(f.get("format_id")) == str(format_id) and f.get("url"):
            ext = f.get("ext") or ("mp4" if want == "video" else "m4a")
            return f["url"], ext

    return None, None

@app.get("/api/health")
def health():
    return {"ok": True}

@app.get("/api/info")
def info(url: str = Query(..., min_length=5)):
    try:
        # TikTok via TikWM
        if is_tiktok(url):
            resolved_v = tikwm_resolve(url, "video")
            resolved_a = tikwm_resolve(url, "audio")
            if not (resolved_v or resolved_a):
                raise HTTPException(status_code=400, detail="TikTok resolve failed")

            title = (resolved_v or resolved_a).get("title", "tiktok")
            thumb = (resolved_v or resolved_a).get("thumbnail", "")
            return JSONResponse({
                "title": title,
                "thumbnail": thumb,
                "platform": "tiktok",
                "duration": "",
                "views": "",
                "formats": [
                    {"type": "video", "label": "Video", "format_id": "direct", "ext": "mp4"},
                    {"type": "audio", "label": "Audio", "format_id": "direct", "ext": "mp3"},
                ]
            })

        info_dict = ytdlp_extract(url)
        title = info_dict.get("title") or "video"
        thumb = info_dict.get("thumbnail") or ""
        platform = (info_dict.get("extractor_key") or "unknown").lower()

        if is_youtube(url):
            formats = youtube_format_list(info_dict)
            return JSONResponse({
                "title": title,
                "thumbnail": thumb,
                "platform": "youtube",
                "duration": str(info_dict.get("duration") or ""),
                "views": str(info_dict.get("view_count") or ""),
                "formats": formats
            })

        # باقي المواقع: فقط خيارين
        return JSONResponse({
            "title": title,
            "thumbnail": thumb,
            "platform": platform,
            "duration": str(info_dict.get("duration") or ""),
            "views": str(info_dict.get("view_count") or ""),
            "formats": [
                {"type": "video", "label": "Video", "format_id": "auto", "ext": "mp4"},
                {"type": "audio", "label": "Audio", "format_id": "auto", "ext": "m4a"},
            ]
        })

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"info failed: {str(e)}")

@app.get("/api/proxy")
def proxy(
    url: str = Query(..., min_length=5),
    type: str = Query("video", pattern="^(video|audio)$"),
    format_id: str = Query("", description="YouTube format_id (optional)"),
    filename: str = Query("", description="suggested filename")
):
    """
    Redirect مباشر للرابط النهائي.
    - لتيك توك: TikWM
    - لليوتيوب: format_id يدعم (وإلا auto)
    - لغيره: auto (أفضل فيديو/صوت)
    """
    want = type
    try:
        suggested = safe_filename(filename) if filename else "download"

        # TikTok
        if is_tiktok(url):
            resolved = tikwm_resolve(url, want)
            if not resolved:
                raise HTTPException(status_code=400, detail="TikTok resolve failed")
            direct = resolved["direct_url"]
            return RedirectResponse(direct, status_code=302)

        info_dict = ytdlp_extract(url)

        # YouTube
        if is_youtube(url):
            fid = format_id.strip() if format_id else ("bestaudio" if want == "audio" else "best")
            direct, ext = youtube_pick_url(info_dict, want, fid)
            if not direct:
                raise HTTPException(status_code=400, detail="YouTube format not found")
            return RedirectResponse(direct, status_code=302)

        # Other platforms
        direct, ext = pick_best_non_youtube(info_dict, want)
        if not direct:
            raise HTTPException(status_code=400, detail="No direct URL found")
        return RedirectResponse(direct, status_code=302)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"proxy failed: {str(e)}")