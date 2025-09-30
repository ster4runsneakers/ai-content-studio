import os, io, base64, json, time, requests
from flask import Flask, render_template, request, redirect, url_for
from openai import OpenAI
from dotenv import load_dotenv
from PIL import Image, ImageDraw, ImageFont
from datetime import datetime

# ── ENV ─────────────────────────────────────────
load_dotenv()
OPENAI_KEY = os.getenv("OPENAI_API_KEY") or ""
print("DEBUG OPENAI:", (OPENAI_KEY[:8] + "...") if OPENAI_KEY else "MISSING")
client = OpenAI(api_key=OPENAI_KEY) if OPENAI_KEY else None

# ── DEBUG SWITCH ────────────────────────────────
DEBUG_LOG = False
def log(*args):
    if DEBUG_LOG:
        print(*args)

# ── FLASK ───────────────────────────────────────
app = Flask(__name__)
OUTPUT_DIR = os.path.join("static", "outputs")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ── PRESETS ─────────────────────────────────────
ASPECT_SIZES = {
    "1:1":       (1024, 1024),
    "9:16":      (1024, 1820),
    "4:5":       (1024, 1280),
    "16:9":      (1280, 720),
    "Facebook":  (1200, 628),    # ~1.91:1
    "Pinterest": (1000, 1500),   # 2:3
}
WATERMARK_DEFAULT_TEXT = "Sneakerness.eu"

# ── HELPERS ─────────────────────────────────────
def add_watermark(pil_img, text=WATERMARK_DEFAULT_TEXT, style="soft"):
    """ style: 'none'|'soft'|'badge' """
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

def white_to_transparent(pil_img, threshold=245):
    """ Λογότυπα: λευκό φόντο → διαφάνεια """
    img = pil_img.convert("RGBA")
    datas = img.getdata()
    new_data = []
    for r, g, b, a in datas:
        if r > threshold and g > threshold and b > threshold:
            new_data.append((r, g, b, 0))
        else:
            new_data.append((r, g, b, a))
    img.putdata(new_data)
    return img

def save_from_url(url, prefix="gen", quality=92, as_png=False, wm_style="soft"):
    resp = requests.get(url, timeout=120)
    resp.raise_for_status()
    img = Image.open(io.BytesIO(resp.content))

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    ext = "png" if as_png else "jpg"
    out_path = os.path.join(OUTPUT_DIR, f"{prefix}_{ts}.{ext}")

    if as_png:
        if img.mode != "RGBA": img = img.convert("RGBA")
        img.save(out_path)
    else:
        img = img.convert("RGB")
        img = add_watermark(img, style=wm_style)
        img.save(out_path, quality=quality)

    if not os.path.exists(out_path):
        raise RuntimeError(f"save_from_url failed: {out_path}")
    log("DEBUG SAVED (url) →", out_path)
    return out_path

def save_from_b64(b64_data, prefix="gen", out_format="png"):
    """ Αποθήκευση base64 με ΣΩΣΤΟ extension. """
    raw = base64.b64decode(b64_data)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    ext = (out_format or "png").lower()
    if ext not in {"png", "jpg", "jpeg"}:
        ext = "png"
    out_path = os.path.join(OUTPUT_DIR, f"{prefix}_{ts}.{ext}")
    with open(out_path, "wb") as f:
        f.write(raw)
    if not os.path.exists(out_path) or os.path.getsize(out_path) == 0:
        raise RuntimeError(f"save_from_b64 failed (empty): {out_path}")
    log("DEBUG SAVED (b64) →", out_path, "| size:", os.path.getsize(out_path))
    return out_path

def with_retries(fn, attempts=3, delay=1.5):
    last_err = None
    for i in range(attempts):
        try:
            return fn()
        except Exception as e:
            last_err = e
            time.sleep(delay * (i+1))
    if last_err: raise last_err

def generate_with_openai(prompt, size_str="1024x1024"):
    if not client:
        raise RuntimeError("OPENAI_API_KEY is missing from .env")
    def _call():
        return client.images.generate(model="gpt-image-1", prompt=prompt, size=size_str)
    resp = with_retries(_call, attempts=3, delay=2.0)

    log("DEBUG RAW RESPONSE:", resp)
    first = resp.data[0]
    url = getattr(first, "url", None)
    b64 = getattr(first, "b64_json", None)
    out_fmt = getattr(resp, "output_format", None) or getattr(first, "output_format", None) or "png"
    log("DEBUG URL:", url)
    log("DEBUG B64:", "YES" if b64 else "NO", "| format:", out_fmt)

    return {"url": url, "b64": b64, "format": out_fmt}

def write_metadata(out_path, payload:dict):
    with open(out_path.rsplit('.',1)[0] + ".json", "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

# ── ROUTES ──────────────────────────────────────
@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        log("DEBUG FORM DATA:", request.form)

        user_prompt  = (request.form.get("prompt") or "").strip()
        aspect       = (request.form.get("aspect") or "1:1").strip()
        quality      = int(request.form.get("quality") or 92)
        content_type = (request.form.get("content_type") or "image").strip()  # image|logo
        wm_style     = (request.form.get("wm_style") or "soft").strip()       # soft|badge|none

        if not user_prompt:
            log("DEBUG: Missing prompt!")
            return "<pre>Missing prompt</pre>", 400

        width, height = ASPECT_SIZES.get(aspect, (1024,1024))
        # DALL·E: για non-square στέλνουμε 1024x1024 και κάνουμε resize μετά
        size_str = f"{width}x{height}" if width==height else "1024x1024"

        final_prompt = user_prompt
        if content_type == "logo":
            final_prompt = ("Minimalist flat vector logo, modern clean typography, "
                            "high contrast, solid shapes, no photo realism. " + user_prompt)

        try:
            result = generate_with_openai(final_prompt, size_str=size_str)

            # SAFE prefix για Windows/URLs (π.χ. 1:1 -> 1x1)
            safe_aspect = aspect.replace(":", "x")
            prefix = f"{'logo' if (content_type == 'logo') else 'gen'}_{safe_aspect}"

            if result["url"]:
                out_path = save_from_url(
                    result["url"], prefix=prefix, quality=quality,
                    as_png=(content_type == "logo"),
                    wm_style=("none" if content_type == "logo" else wm_style)
                )
            elif result["b64"]:
                out_fmt = "png" if content_type == "logo" else (result.get("format") or "png")
                out_path = save_from_b64(result["b64"], prefix=prefix, out_format=out_fmt)
            else:
                return "<pre>No image returned from OpenAI (check verification/limits).</pre>", 500

            # Post-process
            img = Image.open(out_path)
            if content_type == "logo":
                if img.mode != "RGBA": img = img.convert("RGBA")
                img = white_to_transparent(img, threshold=245)
                if (width, height) != img.size:
                    img = img.resize((width, height))
                img.save(out_path)  # PNG
            else:
                img = img.convert("RGB")
                if (width, height) != img.size:
                    img = img.resize((width, height))
                img = add_watermark(img, style=wm_style)
                img.save(out_path, quality=quality)

            log("DEBUG FINAL SAVE →", out_path, "| size:", os.path.getsize(out_path))

            payload = {
                "prompt": user_prompt,
                "final_prompt": final_prompt,
                "aspect": aspect,
                "width": width, "height": height,
                "engine": "openai:gpt-image-1",
                "content_type": content_type,
                "watermark_style": ("none" if content_type == "logo" else wm_style),
                "created_at": datetime.now().isoformat(),
                "file": out_path.replace("\\", "/")
            }
            write_metadata(out_path, payload)

            return redirect(url_for("gallery"))

        except Exception as e:
            log("DEBUG ERROR:", e)
            return f"<pre>Image generation failed:\n{e}</pre>", 500

    return render_template(
        "index.html",
        aspects=list(ASPECT_SIZES.keys()),
        wm_styles=["soft", "badge", "none"]
    )

@app.route("/gallery")
def gallery():
    # Ταξινόμηση με βάση mtime (νεότερα πρώτα)
    files = [f for f in os.listdir(OUTPUT_DIR) if f.lower().endswith((".jpg", ".png"))]
    files.sort(key=lambda fn: os.path.getmtime(os.path.join(OUTPUT_DIR, fn)), reverse=True)
    files = [f"/static/outputs/{f}" for f in files]
    return render_template("gallery.html", files=files)

if __name__ == "__main__":
    app.run(debug=True)
