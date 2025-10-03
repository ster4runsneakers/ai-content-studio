# ==== CAPTIONS SUPPORT (do not edit) ====
import os
from typing import List, Dict

# Πολύ χοντρική ανίχνευση αν το θέμα είναι τρόφιμο/ποτό
FOOD_MARKERS = ["φαγη", "γεύσ", "γευση", "σνακ", "ποτό", "ποτα", "καφέ", "κουζί", "μπουκιά", "συνταγ", "πιάτ"]
BAN_WORDS = ["γεύση","γεύσεις","ουρανίσκο","μπουκιά","γαστρονομ","νόστιμο","λαχταρισ","μαγειρ",
             "συνταγ","πιάτο","κουζίνα","φαγητ","ποτό","ποτά"]

PLATFORM_RULES = {
    "TikTok": "Very short, punchy; youth vibe; 1 short line each.",
    "Instagram": "Short, aspirational; can include product/brand; 1 line each.",
    "Facebook": "Short and clear; friendly; 1 line each.",
    "YouTube Shorts": "Hook-friendly; energetic; 1 line each.",
    "Pinterest": "Inspirational, descriptive; 1 line each."
}

def _lang_label(lang: str) -> str:
    return "Greek" if (lang or "el").lower().startswith("el") else "English"

def _mode_instructions(mode: str, lang: str) -> str:
    if mode == "hooks":
        return "Write only HOOKS: ultra-short attention grabbers that make users want to read/watch."
    if mode == "ctas":
        return "Write only CALLS TO ACTION: direct, compelling prompts to act (buy, click, follow, learn more)."
    return "Write only CAPTIONS: short social-ready lines that fit the platform."

def generate_social_lines(topic: str, tone: str, n: int,
                          platform: str, mode: str, lang: str, keywords: str = "",
                          use_emojis: bool = False, use_hashtags: bool = False) -> List[str]:
    """
    Παράγει n γραμμές για συγκεκριμένο platform/mode/lang με επιλογές emojis/hashtags.
    Παίζει με νέο ή παλιό OpenAI SDK. Επιστρέφει καθαρές γραμμές (χωρίς bullets/αρίθμηση).
    """
    key = os.getenv("OPENAI_API_KEY")
    if not key:
        raise RuntimeError("Λείπει το OPENAI_API_KEY (βάλε το στο .env ή στο Render → Environment).")

    is_food = any(m in (topic or "").lower() for m in FOOD_MARKERS)
    lang_label = _lang_label(lang)
    platform_rules = PLATFORM_RULES.get(platform, PLATFORM_RULES["Instagram"])
    mode_rules = _mode_instructions(mode, lang)

    # Φρουρός για άσχετο λεξιλόγιο (φαγητό) όταν δεν είναι το θέμα
    guard = ""
    if not is_food:
        guard = ("The topic is NOT about food or drinks. STRICTLY FORBIDDEN vocabulary related to food/taste: "
                 + ", ".join(BAN_WORDS) + ".")

    kw_note = ""
    if (keywords or "").strip():
        kw_note = f"Include naturally these keywords or ideas: {keywords}."

    # Emojis / Hashtags κανόνες
    if use_emojis:
        emoji_rule = "You MAY use at most 1 emoji per line (optional)."
    else:
        emoji_rule = "Do NOT use any emojis."

    if use_hashtags:
        # Γενικός κανόνας + ειδική χαλάρωση ανά πλατφόρμα
        if platform in ("Instagram", "TikTok", "YouTube Shorts", "Pinterest"):
            hashtag_rule = "Add 2-4 relevant hashtags at the END of each line (no spaces in tags)."
        elif platform == "Facebook":
            hashtag_rule = "Optionally add up to 2 relevant hashtags at the END of each line."
        else:
            hashtag_rule = "Add 2-4 relevant hashtags at the END of each line."
    else:
        hashtag_rule = "Do NOT include any hashtags."

    system = (
        "You are a senior social-media copywriter. "
        "Return EXACTLY one line per item, no numbering, no bullets. "
        "Stay strictly on topic; be vivid and concrete. "
        "Avoid generic fluff."
    )

    user = (
        f"Language: {lang_label}. Platform: {platform}. Tone: {tone}. "
        f"Topic/product: {topic}. {kw_note} {guard} {platform_rules} {mode_rules} "
        f"{emoji_rule} {hashtag_rule} "
        f"Generate {n} different lines. Output: one line per line, no extra text."
    )

    # --- ΝΕΟ SDK (openai>=1.x) ---
    try:
        from openai import OpenAI
        client = OpenAI(api_key=key)
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            temperature=0.8,
            messages=[{"role": "system", "content": system},
                      {"role": "user",   "content": user}],
        )
        text = (resp.choices[0].message.content or "").strip()
    except Exception as e_new:
        # --- ΠΑΛΙΟ SDK (openai==0.28.x) ---
        try:
            import openai as openai_legacy
            openai_legacy.api_key = key
            resp = openai_legacy.ChatCompletion.create(
                model="gpt-3.5-turbo",
                temperature=0.8,
                messages=[{"role": "system", "content": system},
                          {"role": "user",   "content": user}],
            )
            text = (resp["choices"][0]["message"]["content"] or "").strip()
        except Exception as e_old:
            raise RuntimeError(f"OpenAI captions error (new='{e_new}', legacy='{e_old}')")

    # Καθάρισμα: σπάσε σε γραμμές και αφαίρεσε bullets/αρίθμηση
    lines = [ln.strip().lstrip("•-").lstrip("0123456789. ").strip() for ln in (text.splitlines() or [])]
    lines = [ln for ln in lines if ln]
    return lines[:max(1, n)]

def generate_social_bundle(topic: str, tone: str, n: int,
                           platform: str, mode: str, lang: str, keywords: str = "",
                           use_emojis: bool = False, use_hashtags: bool = False) -> Dict[str, List[str]]:
    """
    Αν mode == 'all' παράγει τρεις λίστες (hooks, captions, ctas) μοιράζοντας το n.
    Αλλιώς παράγει μόνο τη ζητούμενη λίστα.
    """
    if mode != "all":
        return { mode: generate_social_lines(topic, tone, n, platform, mode, lang, keywords,
                                             use_emojis, use_hashtags) }

    # Μοίρασμα n σε 3 κατηγορίες (τουλάχιστον 1 σε κάθε)
    h = max(1, n // 3)
    c = max(1, (n - h) // 2)
    a = max(1, n - h - c)
    return {
        "hooks":    generate_social_lines(topic, tone, h, platform, "hooks",    lang, keywords, use_emojis, use_hashtags),
        "captions": generate_social_lines(topic, tone, c, platform, "captions", lang, keywords, use_emojis, use_hashtags),
        "ctas":     generate_social_lines(topic, tone, a, platform, "ctas",     lang, keywords, use_emojis, use_hashtags),
    }
# ==== /CAPTIONS SUPPORT ====


import os, io, base64, json, time, requests, shutil, tempfile
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, send_file, abort
from dotenv import load_dotenv
from PIL import Image, ImageDraw, ImageFont
from openai import OpenAI

# ── ENV ─────────────────────────────────────────
load_dotenv()
OPENAI_KEY = os.getenv("OPENAI_API_KEY") or ""
print("DEBUG OPENAI:", (OPENAI_KEY[:8] + "...") if OPENAI_KEY else "MISSING")
client = OpenAI(api_key=OPENAI_KEY) if OPENAI_KEY else None

# Cloudinary (προαιρετικό)
import cloudinary, cloudinary.uploader, cloudinary.api
CLOUDINARY_URL = os.getenv("CLOUDINARY_URL") or ""
CLOUDINARY_FOLDER = (os.getenv("CLOUDINARY_FOLDER") or "ai-content-studio").strip("/")
if CLOUDINARY_URL:
    cloudinary.config(cloudinary_url=CLOUDINARY_URL)
    print("Cloudinary: ON → folder:", CLOUDINARY_FOLDER)
else:
    print("Cloudinary: OFF (no CLOUDINARY_URL)")

# ── DEBUG SWITCH ────────────────────────────────
DEBUG_LOG = False
def log(*args):
    if DEBUG_LOG: print(*args)

# ── FLASK ───────────────────────────────────────
app = Flask(__name__)
# ===== NAV CONFIG (pinned + more) =====
from flask import current_app

NAV_ITEMS = [
    {"label": "Home",          "candidates": ["index"],                         "pinned": True},
    {"label": "Gallery",       "candidates": ["gallery"],                       "pinned": True},
    {"label": "Captions",      "candidates": ["captions"],                      "pinned": True},

    {"label": "Upload",        "candidates": ["upload"],                        "pinned": False},
    {"label": "CSE",           "candidates": ["cse"],                           "pinned": False},
    {"label": "A/B Tests",     "candidates": ["ab.index"],                      "pinned": False},
    {"label": "A/B Captions",  "candidates": ["ab.create_test"],                "pinned": False},
    {"label": "Logs",          "candidates": ["logs"],                          "pinned": False},
    {"label": "Backup (ZIP)",  "candidates": ["backup"],                        "pinned": False},
]

def _resolve_endpoint(candidates):
    for ep in candidates:
        if ep in current_app.view_functions:
            return ep
    return None

@app.context_processor
def inject_nav():
    resolved = []
    for it in NAV_ITEMS:
        ep = _resolve_endpoint(it["candidates"])
        if ep:
            resolved.append({"label": it["label"], "endpoint": ep, "pinned": it.get("pinned", False)})
    nav_pinned = [i for i in resolved if i["pinned"]]
    nav_more   = [i for i in resolved if not i["pinned"]]
    return {"nav_pinned": nav_pinned, "nav_more": nav_more}
# ===== /NAV CONFIG =====

OUTPUT_DIR = os.path.join("static", "outputs")
DATA_DIR   = os.path.join("data")
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(DATA_DIR, exist_ok=True)
LOG_PATH = os.path.join(DATA_DIR, "logs.jsonl")

# ── PRESETS ─────────────────────────────────────
ASPECT_SIZES = {
    "1:1":       (1024, 1024),
    "9:16":      (1024, 1820),
    "4:5":       (1024, 1280),
    "16:9":      (1280, 720),
    "Facebook":  (1200, 628),    # ~1.91:1
    "Pinterest": (1000, 1500),   # 2:3
}
ASPECT_PRESETS = [
    {"value":"1:1",       "w":1024, "h":1024, "label":"Square — Instagram Grid, Facebook, Ads"},
    {"value":"9:16",      "w":1024, "h":1820, "label":"Vertical 9:16 — TikTok, Reels, Shorts"},
    {"value":"4:5",       "w":1024, "h":1280, "label":"Portrait 4:5 — Instagram Feed"},
    {"value":"16:9",      "w":1280, "h":720,  "label":"Wide 16:9 — YouTube, Website Banners"},
    {"value":"Facebook",  "w":1200, "h":628,  "label":"Facebook Link/Feed Ads"},
    {"value":"Pinterest", "w":1000, "h":1500, "label":"Pinterest Pins"},
]
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
    new_data = []
    for r, g, b, a in img.getdata():
        if r > threshold and g > threshold and b > threshold:
            new_data.append((r, g, b, 0))
        else:
            new_data.append((r, g, b, a))
    img.putdata(new_data)
    return img

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
    first = resp.data[0]
    return {
        "url":  getattr(first, "url", None),
        "b64":  getattr(first, "b64_json", None),
        "format": getattr(resp, "output_format", None) or getattr(first, "output_format", None) or "png"
    }

def upload_pil_to_cloudinary(pil_img, public_id, fmt="png", tags=None):
    """Ανεβάζει PIL εικόνα απευθείας στο Cloudinary (χωρίς τοπικό save)."""
    if not CLOUDINARY_URL:
        return None, None
    buf = io.BytesIO()
    fmt = fmt.lower()
    if fmt in ("jpg", "jpeg"):
        pil_img = pil_img.convert("RGB")
        pil_img.save(buf, format="JPEG", quality=92)
    else:
        if pil_img.mode != "RGBA":
            pil_img = pil_img.convert("RGBA")
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
    return res.get("secure_url"), res

def save_local(pil_img, out_path, quality=92, as_png=False):
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    if as_png:
        if pil_img.mode != "RGBA": pil_img = pil_img.convert("RGBA")
        pil_img.save(out_path)
    else:
        pil_img = pil_img.convert("RGB")
        pil_img.save(out_path, quality=quality)
    if not os.path.exists(out_path):
        raise RuntimeError(f"Local save failed: {out_path}")
    return out_path

def write_metadata(out_path, payload:dict):
    meta_path = out_path.rsplit('.',1)[0] + ".json"
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

def append_log(entry: dict):
    """Προσθέτει γραμμή σε data/logs.jsonl (JSON Lines)."""
    entry = dict(entry)
    entry["logged_at"] = datetime.now().isoformat()
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")



# ── ROUTES ──────────────────────────────────────
@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        user_prompt  = (request.form.get("prompt") or "").strip()
        aspect       = (request.form.get("aspect") or "1:1").strip()
        quality      = int(request.form.get("quality") or 92)
        content_type = (request.form.get("content_type") or "image").strip()  # image|logo
        wm_style     = (request.form.get("wm_style") or "soft").strip()       # soft|badge|none
        cloud_only   = (request.form.get("cloud_only") == "1")

        if not user_prompt:
            return "<pre>Missing prompt</pre>", 400

        width, height = ASPECT_SIZES.get(aspect, (1024,1024))
        size_str = f"{width}x{height}" if width==height else "1024x1024"

        final_prompt = user_prompt
        if content_type == "logo":
            final_prompt = ("Minimalist flat vector logo, modern clean typography, "
                            "high contrast, solid shapes, no photo realism. " + user_prompt)

        try:
            result = generate_with_openai(final_prompt, size_str=size_str)

            # OpenAI → PIL
            if result["url"]:
                resp = requests.get(result["url"], timeout=120)
                resp.raise_for_status()
                img = Image.open(io.BytesIO(resp.content))
            elif result["b64"]:
                raw = base64.b64decode(result["b64"])
                img = Image.open(io.BytesIO(raw))
            else:
                return "<pre>No image returned from OpenAI (check verification/limits).</pre>", 500

            # Post-process
            safe_aspect = aspect.replace(":", "x")
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            prefix = f"{'logo' if (content_type == 'logo') else 'gen'}_{safe_aspect}"
            public_id = f"{prefix}_{ts}"

            if content_type == "logo":
                if img.mode != "RGBA": img = img.convert("RGBA")
                img = white_to_transparent(img, threshold=245)
                if (width, height) != img.size:
                    img = img.resize((width, height))
                final_fmt = "png"
            else:
                img = img.convert("RGB")
                if (width, height) != img.size:
                    img = img.resize((width, height))
                img = add_watermark(img, style=wm_style)
                final_fmt = "jpg"

            # Cloud upload (αν υπάρχει CLOUDINARY_URL)
            cloud_url = None
            if CLOUDINARY_URL:
                tags = [f"aspect:{safe_aspect}", f"type:{content_type}"]
                if content_type != "logo":
                    tags += [f"wm:{wm_style}", f"q:{quality}"]
                cloud_url, _res = upload_pil_to_cloudinary(img, public_id=public_id, fmt=final_fmt, tags=tags)
                if cloud_url:
                    print("Cloud URL:", cloud_url)

            # Local save (εκτός αν είναι cloud_only)
            out_web_path = None
            if not cloud_only:
                ext = "png" if (final_fmt == "png") else "jpg"
                out_path = os.path.join(OUTPUT_DIR, f"{public_id}.{ext}")
                save_local(img, out_path, quality=quality, as_png=(final_fmt == "png"))
                print("FINAL SAVE:", os.path.abspath(out_path), "SIZE:", os.path.getsize(out_path))
                payload = {
                    "prompt": user_prompt,
                    "final_prompt": final_prompt,
                    "aspect": aspect,
                    "width": width, "height": height,
                    "engine": "openai:gpt-image-1",
                    "content_type": content_type,
                    "watermark_style": ("none" if content_type == "logo" else wm_style),
                    "created_at": datetime.now().isoformat(),
                    "file": out_path.replace("\\", "/"),
                    "cloudinary_url": cloud_url,
                    "cloud_only": cloud_only
                }
                write_metadata(out_path, payload)
                # γράψε log
                append_log({
                    "prompt": user_prompt,
                    "aspect": aspect,
                    "type": content_type,
                    "size": f"{width}x{height}",
                    "wm": ("none" if content_type == "logo" else wm_style),
                    "quality": (None if content_type == "logo" else quality),
                    "local_file": payload["file"],
                    "cloud_url": cloud_url,
                    "cloud_only": cloud_only,
                })
                out_web_path = f"/static/outputs/{os.path.basename(out_path)}"
            else:
                # cloud-only: δεν γράφουμε τοπικό αρχείο, μόνο log
                append_log({
                    "prompt": user_prompt,
                    "aspect": aspect,
                    "type": content_type,
                    "size": f"{width}x{height}",
                    "wm": ("none" if content_type == "logo" else wm_style),
                    "quality": (None if content_type == "logo" else quality),
                    "local_file": None,
                    "cloud_url": cloud_url,
                    "cloud_only": cloud_only,
                })

            return redirect(url_for("gallery"))

        except Exception as e:
            return f"<pre>Image generation failed:\n{e}</pre>", 500

    return render_template(
        "index.html",
        aspects=list(ASPECT_SIZES.keys()),
        wm_styles=["soft", "badge", "none"],
        presets=ASPECT_PRESETS
    )

@app.route("/gallery")
def gallery():
    """Συνδυαστική gallery: Cloudinary (αν υπάρχει) + τοπικά αρχεία."""
    items = []

    # 1) Cloudinary assets
    if CLOUDINARY_URL:
        try:
            res = cloudinary.api.resources(
                type="upload",
                prefix=CLOUDINARY_FOLDER + "/",
                max_results=100,
                direction="desc",
                context=False,
                tags=False
            )
            for r in res.get("resources", []):
                items.append({
                    "url": r.get("secure_url"),
                    "mtime": r.get("created_at")  # ISO string
                })
        except Exception as e:
            print("Cloudinary list error:", e)

    # 2) Local files
    try:
        names = os.listdir(OUTPUT_DIR)
    except Exception as e:
        names = []
        print("GALLERY LIST ERROR:", e)

    local_imgs = [f for f in names if f.lower().endswith((".jpg", ".jpeg", ".png"))]
    for fname in local_imgs:
        path = os.path.join(OUTPUT_DIR, fname)
        try:
            mtime = os.path.getmtime(path)
        except:
            mtime = 0
        items.append({
            "url": f"/static/outputs/{fname}",
            "mtime": mtime
        })

    def to_ts(m):
        if isinstance(m, (int, float)): return float(m)
        try:
            return datetime.fromisoformat(m.replace("Z","+00:00")).timestamp()
        except:
            return 0.0

    items.sort(key=lambda x: to_ts(x["mtime"]), reverse=True)
    files = [it["url"] for it in items]
    return render_template("gallery.html", files=files)

@app.route("/logs")
def logs():
    """Απλά debug logs από data/logs.jsonl (πιο πρόσφατα πρώτα)."""
    if not os.path.exists(LOG_PATH):
        entries = []
    else:
        with open(LOG_PATH, "r", encoding="utf-8") as f:
            lines = f.readlines()
        entries = [json.loads(ln) for ln in lines if ln.strip()]
        entries.reverse()
    return render_template("logs.html", entries=entries)

@app.route("/backup")
def backup():
    """Δημιουργεί ZIP του static/outputs και το κατεβάζει."""
    if not os.path.isdir(OUTPUT_DIR):
        abort(404)
    # temp zip
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    tmp_dir = tempfile.mkdtemp()
    zip_base = os.path.join(tmp_dir, f"outputs_{ts}")
    zip_path = shutil.make_archive(zip_base, "zip", OUTPUT_DIR)
    return send_file(zip_path, as_attachment=True, download_name=f"outputs_{ts}.zip")

@app.route("/health")
def health():
    return "ok", 200

# ==== /captions route (platform/kind/lang/keywords + emojis/hashtags) ====
from flask import request, render_template

@app.route("/captions", methods=["GET","POST"])
def captions():
    error = None
    topic = ""
    tone = "neutral"
    n = 6
    platform = "Instagram"
    kind = "captions"   # captions | hooks | ctas | all
    lang = "el"         # el | en
    keywords = ""
    emojis = False
    hashtags = False

    results = {}

    if request.method == "POST":
        topic = (request.form.get("topic") or "").strip()
        tone = (request.form.get("tone") or "neutral").strip()
        platform = (request.form.get("platform") or "Instagram").strip()
        kind = (request.form.get("kind") or "captions").strip()
        lang = (request.form.get("lang") or "el").strip()
        keywords = (request.form.get("keywords") or "").strip()
        emojis = bool(request.form.get("emojis"))
        hashtags = bool(request.form.get("hashtags"))
        try:
            n = int(request.form.get("n") or 6)
        except:
            n = 6

        try:
            if not topic:
                raise RuntimeError("Γράψε θέμα/προϊόν.")
            results = generate_social_bundle(topic, tone, n, platform, kind, lang, keywords,
                                             use_emojis=emojis, use_hashtags=hashtags)
        except Exception as e:
            error = str(e)

    return render_template("captions.html",
                           error=error,
                           topic=topic, tone=tone, n=n,
                           platform=platform, kind=kind, lang=lang, keywords=keywords,
                           emojis=emojis, hashtags=hashtags,
                           results=results)
# ==== /end captions route ====



if __name__ == "__main__":
    app.run(debug=True)
