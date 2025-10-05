# routes_media.py
import os, io, requests
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont
from flask import Blueprint, render_template, request, redirect, url_for, send_file, current_app

media_bp = Blueprint("media", __name__)

# --- Paths / Config ---
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")
OUTPUT_DIR = os.path.join(STATIC_DIR, "outputs")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# --- Aspect presets (ίδια λογική με app.py) ---
ASPECT_SIZES = {
    "1:1":       (1024, 1024),
    "9:16":      (1024, 1820),
    "4:5":       (1024, 1280),
    "16:9":      (1280, 720),
    "Facebook":  (1200, 628),
    "Pinterest": (1000, 1500),
}
ASPECT_PRESETS = [
    {"value":"1:1",       "w":1024, "h":1024, "label":"Square — Instagram Grid, Facebook, Ads"},
    {"value":"9:16",      "w":1024, "h":1820, "label":"Vertical 9:16 — TikTok, Reels, Shorts"},
    {"value":"4:5",       "w":1024, "h":1280, "label":"Portrait 4:5 — Instagram Feed"},
    {"value":"16:9",      "w":1280, "h":720,  "label":"Wide 16:9 — YouTube, Website Banners"},
    {"value":"Facebook",  "w":1200, "h":628,  "label":"Facebook Link/Feed Ads"},
    {"value":"Pinterest", "w":1000, "h":1500, "label":"Pinterest Pins"},
]

# --- Cloudinary (προαιρετικό) ---
import cloudinary, cloudinary.uploader
CLOUDINARY_URL = os.getenv("CLOUDINARY_URL") or ""
CLOUDINARY_FOLDER = (os.getenv("CLOUDINARY_FOLDER") or "ai-content-studio").strip("/")
if CLOUDINARY_URL:
    cloudinary.config(cloudinary_url=CLOUDINARY_URL)

# --- Helpers ---
def add_watermark(pil_img, text="Sneakerness.eu", style="soft"):
    if style == "none" or not text:
        return pil_img
    img = pil_img.convert("RGBA")
    w, h = img.size
    overlay = Image.new("RGBA", img.size, (0,0,0,0))
    draw = ImageDraw.Draw(overlay)
    try:
        font = ImageFont.truetype("arial.ttf", max(18, w // 40))
    except:
        font = ImageFont.load_default()
    bbox = draw.textbbox((0,0), text, font=font)
    text_w, text_h = bbox[2], bbox[3]
    pad = max(8, w // 200)
    if style == "badge":
        box_w = text_w + pad*3
        box_h = text_h + pad*2
        x1 = w - box_w - pad
        y1 = h - box_h - pad
        radius = max(10, box_h // 2)
        draw.rounded_rectangle([x1, y1, x1+box_w, y1+box_h], radius=radius, fill=(0,0,0,120))
        draw.text((x1 + pad*1.5, y1 + pad), text, font=font, fill=(255,255,255,230))
    else:
        x = w - text_w - pad
        y = h - text_h - pad
        draw.text((x+1, y+1), text, font=font, fill=(0,0,0,120))
        draw.text((x, y), text, font=font, fill=(255,255,255,220))
    return Image.alpha_composite(img, overlay).convert("RGB")

def upload_pil_to_cloudinary(pil_img, public_id, fmt="jpg", tags=None):
    if not CLOUDINARY_URL:
        return None
    buf = io.BytesIO()
    fmt = fmt.lower()
    if fmt in ("jpg","jpeg"):
        pil_img = pil_img.convert("RGB")
        pil_img.save(buf, format="JPEG", quality=92)
    else:
        if pil_img.mode != "RGBA": pil_img = pil_img.convert("RGBA")
        pil_img.save(buf, format="PNG")
    buf.seek(0)
    res = cloudinary.uploader.upload(
        buf,
        folder=CLOUDINARY_FOLDER,
        public_id=public_id,
        overwrite=True,
        resource_type="image",
        tags=tags or []
    )
    return res.get("secure_url")

def save_local(pil_img, out_path, quality=92, as_png=False):
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    if as_png:
        if pil_img.mode != "RGBA": pil_img = pil_img.convert("RGBA")
        pil_img.save(out_path)
    else:
        pil_img = pil_img.convert("RGB")
        pil_img.save(out_path, quality=quality)
    return out_path

# ---------- /upload ----------
@media_bp.route("/upload", methods=["GET","POST"])
def upload():
    error = None
    src_url = (request.args.get("src") or request.form.get("src") or "").strip()
    if request.method == "POST":
        wm_style = (request.form.get("wm_style") or "soft").strip()
        quality = int(request.form.get("quality") or 92)
        aspect  = (request.form.get("aspect") or "1:1").strip()

        try:
            if src_url:
                r = requests.get(src_url, timeout=30)
                r.raise_for_status()
                img = Image.open(io.BytesIO(r.content)).convert("RGB")
            else:
                f = request.files.get("file")
                if not f or not f.filename:
                    error = "Διάλεξε αρχείο ή βάλε URL."
                    return render_template("upload.html", error=error,
                                           src=src_url, aspects=list(ASPECT_SIZES.keys()), presets=ASPECT_PRESETS)
                img = Image.open(f.stream).convert("RGB")

            if aspect in ASPECT_SIZES:
                w, h = ASPECT_SIZES[aspect]
                if img.size != (w, h):
                    img = img.resize((w, h))

            img = add_watermark(img, style=wm_style)

            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_aspect = aspect.replace(":", "x")
            public_id = f"upload_{safe_aspect}_{ts}"

            cloud_url = None
            if CLOUDINARY_URL:
                cloud_url = upload_pil_to_cloudinary(
                    img, public_id=public_id, fmt="jpg",
                    tags=[f"aspect:{safe_aspect}", "type:upload", f"wm:{wm_style}"]
                )

            out_path = os.path.join(OUTPUT_DIR, f"{public_id}.jpg")
            save_local(img, out_path, quality=quality, as_png=False)

            return redirect(url_for("gallery"))
        except Exception as e:
            error = f"{e}"

    return render_template("upload.html",
                           error=error, src=src_url,
                           aspects=list(ASPECT_SIZES.keys()), presets=ASPECT_PRESETS)

# ---------- /cse (Pro) ----------
@media_bp.route("/cse", methods=["GET","POST"])
def cse():
    results, error, q = [], None, ""

    # keys: προτίμησε app.config, αλλιώς .env
    key = current_app.config.get("GOOGLE_CSE_KEY") or os.getenv("GOOGLE_CSE_KEY")
    cx  = current_app.config.get("GOOGLE_CSE_ID")  or os.getenv("GOOGLE_CSE_ID")

    # UI defaults
    aspect   = (request.form.get("aspect") or request.args.get("aspect") or "any").strip()
    img_type = (request.form.get("img_type") or request.args.get("img_type") or "").strip()
    img_size = (request.form.get("img_size") or request.args.get("img_size") or "").strip()
    safe     = (request.form.get("safe")     or request.args.get("safe")     or "off").strip()

    if request.method == "POST":
        q        = (request.form.get("q") or "").strip()
        aspect   = (request.form.get("aspect") or "any").strip()
        img_type = (request.form.get("img_type") or "").strip()
        img_size = (request.form.get("img_size") or "").strip()
        safe     = (request.form.get("safe") or "off").strip()

        if not q:
            error = "Γράψε όρο αναζήτησης."
        elif not key or not cx:
            error = "Ρύθμισε GOOGLE_CSE_KEY και GOOGLE_CSE_ID στο .env"
        else:
            try:
                params = {"key": key, "cx": cx, "q": q, "num": 10, "searchType": "image"}
                if img_type: params["imgType"] = img_type
                if img_size: params["imgSize"] = img_size
                if safe:     params["safe"]    = safe

                r = requests.get("https://www.googleapis.com/customsearch/v1", params=params, timeout=20)
                data = r.json()

                # Aspect filter
                target_ratio = None
                tol = 0.06
                if aspect != "any" and aspect in ASPECT_SIZES:
                    tw, th = ASPECT_SIZES[aspect]
                    target_ratio = tw / th

                for it in data.get("items", []):
                    im = it.get("image", {}) or {}
                    w = im.get("width")
                    h = im.get("height")
                    ok = True
                    if target_ratio and w and h:
                        ratio = float(w) / float(h)
                        if abs(ratio - target_ratio) > target_ratio * tol:
                            ok = False
                    if ok:
                        results.append({
                            "title": it.get("title"),
                            "link": it.get("link"),
                            "thumbnail": im.get("thumbnailLink"),
                            "width": w, "height": h
                        })
            except Exception as e:
                error = f"{e}"

    return render_template("cse.html",
                           results=results, error=error, q=q,
                           aspect=aspect,
                           aspects=list(ASPECT_SIZES.keys()),
                           img_type=img_type, img_size=img_size, safe=safe)

# ---------- /media/import (από CSE) ----------
@media_bp.route("/media/import", methods=["POST"])
def import_remote():
    src = (request.form.get("src") or "").strip()
    aspect = (request.form.get("aspect") or "1:1").strip()
    wm_style = (request.form.get("wm_style") or "soft").strip()
    try:
        quality = int(request.form.get("quality") or 92)
    except:
        quality = 92

    if not src:
        return redirect(url_for("media.cse"))

    try:
        r = requests.get(src, timeout=30)
        r.raise_for_status()
        img = Image.open(io.BytesIO(r.content)).convert("RGB")

        if aspect in ASPECT_SIZES:
            w, h = ASPECT_SIZES[aspect]
            if img.size != (w, h):
                img = img.resize((w, h))

        img = add_watermark(img, style=wm_style)

        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_aspect = aspect.replace(":", "x")
        public_id = f"import_{safe_aspect}_{ts}"

        if CLOUDINARY_URL:
            _ = upload_pil_to_cloudinary(
                img, public_id=public_id, fmt="jpg",
                tags=[f"aspect:{safe_aspect}", "type:import", f"wm:{wm_style}"]
            )

        out_path = os.path.join(OUTPUT_DIR, f"{public_id}.jpg")
        save_local(img, out_path, quality=quality, as_png=False)

        return redirect(url_for("gallery"))
    except Exception as e:
        return f"<pre>Import failed: {e}</pre>", 500
