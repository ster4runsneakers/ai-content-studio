import os, io, json, zipfile, re
from datetime import datetime
from pathlib import Path
from flask import Flask, render_template, request, redirect, url_for, send_file
from dotenv import load_dotenv, find_dotenv

# ---------- .env + cleanup ----------
_ZERO_WIDTH = "".join(map(chr, [0x200B,0x200C,0x200D,0x200E,0x200F,0x202A,0x202B,0x202C,0x202D,0x202E]))
def _mask(s: str): return (s[:8]+"…"+s[-6:]) if s and len(s)>16 else ("EMPTY" if not s else "SHORT")
def _clean_val(v: str) -> str:
    if v is None: return ""
    v = v.strip().strip('"').strip("'")
    v = v.replace("—","-").replace("–","-").replace("…","")
    v = "".join(ch for ch in v if ch not in _ZERO_WIDTH)
    return v.strip()
def _force_env_from_file(path: str):
    if not path or not os.path.exists(path): return
    with open(path, "r", encoding="utf-8-sig") as f:
        for raw in f:
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line: continue
            k, v = line.split("=", 1)
            k = "".join(ch for ch in k.strip() if (ch == "_" or (ch.isascii() and ch.isalnum()))).upper()
            v = _clean_val(v)
            if not k: continue
            if k=="OPENAI_API_KEY" and os.environ.get("OPENAI_API_KEY","").startswith("sk-"): continue
            os.environ[k] = v

dotenv_main = find_dotenv(usecwd=True)
load_dotenv(dotenv_path=dotenv_main, override=False)
_force_env_from_file(dotenv_main)
dotenv_override = os.path.join(os.getcwd(), ".env.override")
if os.path.exists(dotenv_override):
    load_dotenv(dotenv_path=dotenv_override, override=True)
    _force_env_from_file(dotenv_override)
print("DOTENV used from:", dotenv_main or "NOT FOUND")

# ---------- Flask ----------
app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY") or "dev-secret"

# ---------- OpenAI ----------
from openai import OpenAI
_raw_key = os.getenv("OPENAI_API_KEY")
OPENAI_KEY = _clean_val(_raw_key)
_bad = [(i, hex(ord(c))) for i,c in enumerate(OPENAI_KEY) if (ord(c)>127 or c.isspace())]
print(f"OPENAI DEBUG len={len(OPENAI_KEY)} last6={OPENAI_KEY[-6:] if OPENAI_KEY else 'EMPTY'} bad={_bad if _bad else 'OK'}")
client = OpenAI(api_key=OPENAI_KEY) if OPENAI_KEY else None

# ---------- Cloudinary ----------
import cloudinary, cloudinary.uploader
CLOUDINARY_URL = os.getenv("CLOUDINARY_URL") or ""
CLOUDINARY_FOLDER = (os.getenv("CLOUDINARY_FOLDER") or "ai-content-studio").strip("/")
if CLOUDINARY_URL:
    cloudinary.config(cloudinary_url=CLOUDINARY_URL)
print(f"Cloudinary: {'ON' if CLOUDINARY_URL else 'OFF'} → folder: {CLOUDINARY_FOLDER or '(default)'}")

# ---------- Google CSE ----------
app.config["GOOGLE_CSE_KEY"] = _clean_val(os.getenv("GOOGLE_CSE_KEY") or "")
app.config["GOOGLE_CSE_ID"]  = _clean_val(os.getenv("GOOGLE_CSE_ID")  or "")
print("CSE DEBUG key=", _mask(app.config["GOOGLE_CSE_KEY"]), "cx=", app.config["GOOGLE_CSE_ID"] or "EMPTY")

# ---------- Paths / constants ----------
BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
OUTPUT_DIR = STATIC_DIR / "outputs"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
LOG_PATH = BASE_DIR / "logs.json"

ASPECT_SIZES = {
    "1:1": (1024,1024), "9:16": (1024,1820), "4:5": (1024,1280), "16:9": (1280,720),
    "Facebook": (1200,628), "Pinterest": (1000,1500)
}
ASPECT_PRESETS = [
    {"value":"1:1","w":1024,"h":1024,"label":"Square — Instagram Grid, Facebook, Ads"},
    {"value":"9:16","w":1024,"h":1820,"label":"Vertical 9:16 — TikTok, Reels, Shorts"},
    {"value":"4:5","w":1024,"h":1280,"label":"Portrait 4:5 — Instagram Feed"},
    {"value":"16:9","w":1280,"h":720,"label":"Wide 16:9 — YouTube, Website Banners"},
    {"value":"Facebook","w":1200,"h":628,"label":"Facebook Link/Feed Ads"},
    {"value":"Pinterest","w":1000,"h":1500,"label":"Pinterest Pins"},
]

def append_log(entry: dict):
    try:
        data = []
        if LOG_PATH.exists():
            data = json.loads(LOG_PATH.read_text(encoding="utf-8"))
        data.append(entry)
        LOG_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception as e:
        print("append_log error:", e)

# ---------- Navbar ----------
NAV_CATALOG = [
    {"label":"Home","candidates":["index"],"pinned":True},
    {"label":"Captions","candidates":["captions"],"pinned":True},
    {"label":"Upload","candidates":["media.upload","upload"],"pinned":False},
    {"label":"CSE","candidates":["media.cse","cse"],"pinned":False},
    {"label":"Gallery","candidates":["gallery"],"pinned":False},
    {"label":"My Snippets","candidates":["snip.index","snippets"],"pinned":False},
    {"label":"Logs","candidates":["logs"],"pinned":False},
    {"label":"Backup (ZIP)","candidates":["backup"],"pinned":False},
]
@app.context_processor
def inject_nav():
    existing = set(app.view_functions.keys())
    def first_existing(cands):
        for ep in cands:
            if ep in existing: return ep
        return None
    pinned, more = [], []
    for item in NAV_CATALOG:
        ep = first_existing(item.get("candidates", []))
        if not ep: continue
        entry = {"label": item["label"], "endpoint": ep}
        (pinned if item.get("pinned") else more).append(entry)
    return {"nav_pinned": pinned, "nav_more": more}

# ---------- Captions (JSON mode) ----------
def _json_safety(txt: str):
    if txt.strip().startswith("```"):
        txt = re.sub(r"^```(?:json)?\s*|\s*```$", "", txt.strip(), flags=re.MULTILINE)
    return txt.strip()

def generate_captions(topic, n=6, platform="Instagram", kind="all", lang="el",
                      tone="energetic", keywords="", want_emojis=True, want_hashtags=True,
                      model="gpt-4o-mini"):
    if not client:
        raise RuntimeError("OPENAI_API_KEY is missing")

    n_hooks = max(2, min(6, (n+1)//2))
    n_ctas  = max(2, min(6, (n+1)//2))
    n_caps  = n

    language = "Greek" if lang=="el" else "English"
    include_emojis   = "yes" if want_emojis else "no"
    include_hashtags = "yes" if want_hashtags else "no"

    sys = ("You are a concise social media copywriter. "
           "Always answer with STRICT JSON only, no explanations, no markdown fences.")
    user = f"""
Generate social content for {platform}.
Language: {language}. Tone: {tone}. Topic: {topic}.
Keywords to weave naturally: {keywords or "none"}.
Include emojis in lines: {include_emojis}. Include hashtags in lines: {"yes" if want_hashtags else "no"}.

Return a single JSON object with EXACTLY these keys:
- "hooks": array of {n_hooks} short hook lines.
- "captions": array of {n_caps} post lines (no numbering, 1 line each).
- "ctas": array of {n_ctas} call-to-action lines.
- "hashtags": array of 8-15 relevant hashtags WITHOUT the # sign (just words), in {language.lower()} context.

Constraints:
- Do not include section headers in the lines.
- Keep each line short and punchy.
- If Include emojis=no, do not put emojis in lines.
- Hashtags must be ONLY the words (no #, no punctuation).
"""
    resp = client.chat.completions.create(
        model=model, temperature=0.7, response_format={"type":"json_object"},
        messages=[{"role":"system","content":sys},{"role":"user","content":user}],
    )
    raw = _json_safety(resp.choices[0].message.content or "")
    data = {"hooks":[], "captions":[], "ctas":[], "hashtags":[]}
    try:
        j = json.loads(raw)
        data["hooks"]    = [s.strip() for s in j.get("hooks",[]) if isinstance(s,str) and s.strip()]
        data["captions"] = [s.strip() for s in j.get("captions",[]) if isinstance(s,str) and s.strip()]
        data["ctas"]     = [s.strip() for s in j.get("ctas",[]) if isinstance(s,str) and s.strip()]
        tags = [s.strip().lstrip("#").replace(" ","") for s in j.get("hashtags",[]) if isinstance(s,str)]
        tags = [re.sub(r"[^A-Za-z0-9_άέήίόύώΆΈΉΊΌΎΏα-ωΑ-Ω]", "", t) for t in tags]
        tags = [t for t in tags if t]
        data["hashtags"] = tags[:15]
    except Exception:
        # Fallback (σπάνιο)
        lines = [ln.strip().lstrip("•-").lstrip("0123456789. ").strip() for ln in raw.splitlines() if ln.strip()]
        hooks, caps, ctas = [], [], []
        for ln in lines:
            low = ln.lower()
            if any(k in low for k in ("buy now","shop now","κάνε τώρα","πάτα το link","order","αγόρασε","παράγγειλε")):
                ctas.append(ln)
            elif any(k in low for k in ("limited","now","σήμερα","τελευταία","offer","προσφορά","μόνο σήμερα")):
                hooks.append(ln)
            else:
                caps.append(ln)
        data["hooks"], data["captions"], data["ctas"], data["hashtags"] = hooks, caps, ctas, []

    # trim
    data["hooks"]    = data["hooks"][:n_hooks]
    data["captions"] = data["captions"][:n_caps]
    data["ctas"]     = data["ctas"][:n_ctas]
    data["hashtags"] = data["hashtags"][:15]
    return data

def _filter_by_kind(data: dict, kind: str) -> dict:
    k = (kind or "all").lower()
    if k == "all":
        return data
    keep = {"hooks","captions","ctas","hashtags"}
    if k in keep:
        return {key:(data.get(key,[]) if key==k else []) for key in ["hooks","captions","ctas","hashtags"]}
    return data

# ---------- Routes ----------
@app.route("/")
def index():
    return render_template("index.html", aspects=list(ASPECT_SIZES.keys()), presets=ASPECT_PRESETS)

@app.route("/captions", methods=["GET","POST"])
def captions():
    error=None
    topic    = request.form.get("topic","")
    tone     = request.form.get("tone","energetic")
    platform = request.form.get("platform","Instagram")
    kind     = request.form.get("kind","all")
    lang     = request.form.get("lang","el")
    n        = int(request.form.get("n","6") or 6)
    keywords = request.form.get("keywords","")
    emojis   = bool(request.form.get("emojis"))
    hashtags = bool(request.form.get("hashtags"))

    print("KIND DEBUG →", kind)

    results = {"hooks":[], "captions":[], "ctas":[], "hashtags":[]}
    hashtags_line = ""
    if request.method == "POST":
        if not topic.strip():
            error = "Γράψε θέμα/προϊόν."
        else:
            try:
                data = generate_captions(
                    topic=topic, n=n, platform=platform, kind=kind, lang=lang,
                    tone=tone, keywords=keywords, want_emojis=emojis, want_hashtags=hashtags
                )
                results = _filter_by_kind(data, kind)
                hashtags_line = " ".join("#"+(t or "").strip().lower().replace(" ","")
                                         for t in results.get("hashtags", []))
            except Exception as e:
                error = f"{e}"

    return render_template("captions.html",
                           error=error, topic=topic, tone=tone, platform=platform, kind=kind,
                           lang=lang, n=n, keywords=keywords, emojis=emojis, hashtags=hashtags,
                           results=results, hashtags_line=hashtags_line)
      

@app.route("/gallery")
def gallery():
    images = []
    for p in sorted(OUTPUT_DIR.glob("*.jpg")):
        images.append({"name":p.name, "path":f"/static/outputs/{p.name}",
                       "mtime": datetime.fromtimestamp(p.stat().st_mtime).strftime("%Y-%m-%d %H:%M")})
    return render_template("gallery.html", images=images)

@app.route("/logs")
def logs():
    data=[]
    if LOG_PATH.exists():
        try: data = json.loads(LOG_PATH.read_text(encoding="utf-8"))
        except: data = []
    return render_template("logs.html", logs=data)

@app.route("/backup")
def backup():
    with_env = request.args.get("with_env","0") == "1"
    project_root = BASE_DIR
    memory_file = io.BytesIO()
    exclude_dirs = {".git",".venv","__pycache__","_backups"}
    exclude_ext  = {".pyc",".pyo",".zip"}
    with zipfile.ZipFile(memory_file,"w",zipfile.ZIP_DEFLATED) as zf:
        for path in project_root.rglob("*"):
            rel = path.relative_to(project_root)
            if any(part in exclude_dirs for part in rel.parts): continue
            if path.is_file():
                if path.suffix.lower() in exclude_ext: continue
                if (not with_env) and path.name == ".env": continue
                zf.write(path, arcname=str(rel))
    memory_file.seek(0)
    name = f"ai-content-studio_{datetime.now().strftime('%Y%m%d-%H%M%S')}.zip"
    return send_file(memory_file, as_attachment=True, download_name=name, mimetype="application/zip")

@app.route("/__endpoints")
def __endpoints():
    return "<pre>" + "\n".join(sorted(app.view_functions.keys())) + "</pre>"

# ---------- Blueprints ----------
try:
    from routes_media import media_bp
    app.register_blueprint(media_bp); print("Blueprint: media ✅")
except Exception as e:
    print("Blueprint: media ❌", e)
try:
    from routes_snippets import snip_bp
    app.register_blueprint(snip_bp); print("Blueprint: snippets ✅")
except Exception as e:
    print("Blueprint: snippets ❌", e)
try:
    from routes_ab import ab_bp
    app.register_blueprint(ab_bp); print("Blueprint: ab ✅")
except Exception as e:
    print("Blueprint: ab ❌", e)

if __name__ == "__main__":
    app.run(debug=True)
