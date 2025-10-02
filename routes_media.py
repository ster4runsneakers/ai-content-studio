# routes_media.py
import os
import io
import requests
from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, current_app
from PIL import Image, ImageDraw, ImageFont

# Προαιρετικό Cloudinary (αν έχεις CLOUDINARY_URL)
try:
    import cloudinary
    import cloudinary.uploader
except Exception:
    cloudinary = None

media_bp = Blueprint("media", __name__)

# --------- Presets / Aspects ----------
ASPECT_SIZES = {
    "1:1":   (1024, 1024),
    "9:16":  (1080, 1920),
    "4:5":   (1080, 1350),
    "16:9":  (1920, 1080),
    "Facebook":  (1200, 628),
    "Pinterest": (1000, 1500),
}

ASPECT_PRESETS = {
    "TikTok 9:16": "9:16",
    "Instagram 4:5": "4:5",
    "Square 1:1": "1:1",
    "YouTube 16:9": "16:9",
    "Facebook Link": "Facebook",
    "Pinterest Tall": "Pinterest",
}

def _presets_map(p):
    return p if isinstance(p, dict) else {str(x): str(x) for x in (p or [])}

# --------- Helpers (self-contained) ----------
def _output_dir():
    # Αν έχεις app.config["OUTPUT_DIR"], χρησιμοποίησέ το — αλλιώς default.
    out = current_app.config.get("OUTPUT_DIR") or os.path.join("static", "outputs")
    os.makedirs(out, exist_ok=True)
    return out

def save_local(img: Image.Image, out_path: str, quality: int = 92, as_png: bool = False):
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    if as_png:
        img.save(out_path, format="PNG")
    else:
        img.save(out_path, format="JPEG", quality=quality, optimize=True, progressive=True)

def upload_pil_to_cloudinary(img: Image.Image, public_id: str, fmt: str = "jpg", tags=None):
    if not cloudinary or not os.getenv("CLOUDINARY_URL"):
        return None, None
    if not cloudinary.config().cloud_name:
        # αρχικοποίηση από CLOUDINARY_URL
        cloudinary.config(cloudinary_url=os.getenv("CLOUDINARY_URL"))
    folder = os.getenv("CLOUDINARY_FOLDER", "ai-content-studio")
    buf = io.BytesIO()
    fmt_u = fmt.upper()
    img.save(buf, format="PNG" if fmt_u == "PNG" else "JPEG", quality=95)
    buf.seek(0)
    resp = cloudinary.uploader.upload(
        file=buf,
        public_id=public_id,
        folder=folder,
        overwrite=True,
        resource_type="image",
        tags=tags or ["upload"]
    )
    return resp.get("secure_url"), resp

def add_watermark(img: Image.Image, style: str = "soft") -> Image.Image:
    if style == "none":
        return img
    # απλό “soft” υδατογράφημα κάτω δεξιά
    txt = "AI Content Studio"
    base = img.convert("RGBA")
    overlay = Image.new("RGBA", base.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    # μέγεθος γραμματοσειράς αναλογικά
    w, h = base.size
    fontsize = max(18, int(min(w, h) * 0.035))
    try:
        # default: θα πέσει σε PIL default αν δεν βρει TTF
        font = ImageFont.truetype("arial.ttf", fontsize)
    except Exception:
        font = ImageFont.load_default()

    text_w, text_h = draw.textbbox((0, 0), txt, font=font)[2:]
    pad = max(10, fontsize // 2)
    x = w - text_w - pad
    y = h - text_h - pad

    # ημιδιαφανές “badge”
    draw.rectangle([x - pad//2, y - pad//4, x + text_w + pad//2, y + text_h + pad//4],
                   fill=(0, 0, 0, 90))
    draw.text((x, y), txt, font=font, fill=(255, 255, 255, 190))

    return Image.alpha_composite(base, overlay).convert("RGB")

# --------- Routes ----------
@media_bp.route("/upload", methods=["GET", "POST"])
def upload():
    error = None
    aspects = list(ASPECT_SIZES.keys())
    presets_map = _presets_map(ASPECT_PRESETS)

    if request.method == "POST":
        f = request.files.get("file")
        wm_style = (request.form.get("wm_style") or "soft").strip()
        quality = int(request.form.get("quality") or 92)
        aspect = (request.form.get("aspect") or "original").strip()

        if not f or not f.filename:
            error = "Διάλεξε αρχείο εικόνας."
            return render_template("upload.html", error=error,
                                   aspects=aspects, presets=presets_map)

        try:
            img = Image.open(f.stream).convert("RGB")

            # Resize σε προκαθορισμένες διαστάσεις αν ζητήθηκε aspect
            if aspect != "original" and aspect in ASPECT_SIZES:
                w, h = ASPECT_SIZES[aspect]
                if img.size != (w, h):
                    img = img.resize((w, h))

            # Watermark
            img = add_watermark(img, style=wm_style)

            # Save/Cloud
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            public_id = f"upload_{ts}"
            out_dir = _output_dir()
            out_path = os.path.join(out_dir, f"{public_id}.jpg")

            cloud_url = None
            if os.getenv("CLOUDINARY_URL"):
                cloud_url, _ = upload_pil_to_cloudinary(img, public_id=public_id, fmt="jpg", tags=["upload"])

            save_local(img, out_path, quality=quality, as_png=False)
            # Αν έχεις δικό σου logger, πρόσθεσε τον εδώ
            # append_log({...})

            return redirect(url_for("gallery"))

        except Exception as e:
            error = f"{e}"

    return render_template("upload.html", error=error,
                           aspects=aspects, presets=presets_map)

@media_bp.route("/cse", methods=["GET", "POST"])
def cse():
    results, error = [], None
    q = ""
    aspect = "any"
    aspects = list(ASPECT_SIZES.keys())
    presets_map = _presets_map(ASPECT_PRESETS)

    key = os.getenv("GOOGLE_CSE_KEY")
    cx = os.getenv("GOOGLE_CSE_ID")

    if request.method == "POST":
        q = (request.form.get("q") or "").strip()
        aspect = (request.form.get("aspect") or "any").strip()

        if not q:
            error = "Γράψε όρο αναζήτησης."
        elif not key or not cx:
            error = "Ρύθμισε GOOGLE_CSE_KEY και GOOGLE_CSE_ID στο .env"
        else:
            try:
                params = {"key": key, "cx": cx, "q": q, "num": 10, "searchType": "image"}
                r = requests.get("https://www.googleapis.com/customsearch/v1", params=params, timeout=20)
                data = r.json()

                # Φιλτράρισμα aspect ratio με ±6% ανοχή
                target_ratio = None
                tol = 0.06
                if aspect != "any" and aspect in ASPECT_SIZES:
                    tw, th = ASPECT_SIZES[aspect]
                    target_ratio = tw / th

                for it in (data.get("items") or []):
                    im = it.get("image", {}) or {}
                    w = im.get("width")
                    h = im.get("height")
                    ok = True
                    if target_ratio and w and h:
                        ratio = float(w) / float(h)
                        if abs(ratio - target_ratio) > (target_ratio * tol):
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
                           aspect=aspect, aspects=aspects, presets=presets_map)
