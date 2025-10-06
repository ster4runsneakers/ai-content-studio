# routes_snippets.py
import os, sqlite3, io, csv
from datetime import datetime
from flask import Blueprint, render_template, request, jsonify, send_file, make_response, current_app

snip_bp = Blueprint("snip", __name__)

# --- DB paths ---
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
INSTANCE_DIR = os.path.join(BASE_DIR, "instance")
os.makedirs(INSTANCE_DIR, exist_ok=True)
DB_PATH = os.path.join(INSTANCE_DIR, "snippets.db")

# --- helpers ---
def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_conn() as con:
        con.execute("""
        CREATE TABLE IF NOT EXISTS snippets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL,
            platform TEXT,
            lang TEXT,
            kind TEXT,            -- caption / hook / cta / mixed
            text TEXT NOT NULL,
            tags TEXT             -- comma separated
        )
        """)
init_db()

def row_to_dict(r):
    return {
        "id": r["id"],
        "created_at": r["created_at"],
        "platform": r["platform"] or "",
        "lang": r["lang"] or "",
        "kind": r["kind"] or "",
        "text": r["text"] or "",
        "tags": r["tags"] or "",
    }

# --- routes ---
@snip_bp.route("/snippets", methods=["GET"])
def index():
    q    = (request.args.get("q") or "").strip()
    tag  = (request.args.get("tag") or "").strip()
    kind = (request.args.get("kind") or "").strip()  # optional filter

    sql  = "SELECT * FROM snippets WHERE 1=1"
    args = []
    if q:
        sql += " AND (text LIKE ? OR tags LIKE ?)"
        args += [f"%{q}%", f"%{q}%"]
    if tag:
        sql += " AND ((',' || ifnull(tags,'') || ',') LIKE ?)"
        args += [f"%,{tag},%"]
    if kind:
        sql += " AND kind = ?"
        args += [kind]

    sql += " ORDER BY id DESC LIMIT 500"
    with get_conn() as con:
        rows = [row_to_dict(r) for r in con.execute(sql, args).fetchall()]

    return render_template("snippets.html", rows=rows, q=q, tag=tag, kind=kind)

@snip_bp.route("/snippets/add", methods=["POST"])
def add_one():
    data = request.form or request.json or {}
    text = (data.get("text") or "").strip()
    if not text:
        return jsonify({"ok": False, "error": "empty text"}), 400
    platform = (data.get("platform") or "").strip()
    lang     = (data.get("lang") or "").strip()
    kind     = (data.get("kind") or "caption").strip()
    tags     = (data.get("tags") or "").strip()
    with get_conn() as con:
        con.execute(
            "INSERT INTO snippets (created_at, platform, lang, kind, text, tags) VALUES (?, ?, ?, ?, ?, ?)",
            (datetime.now().isoformat(timespec="seconds"), platform, lang, kind, text, tags)
        )
    return jsonify({"ok": True})

@snip_bp.route("/snippets/bulk_add", methods=["POST"])
def bulk_add():
    """
    Περιμένει JSON:
    {
      "items":[
        {"text":"...", "platform":"instagram","lang":"el","kind":"caption","tags":"sneakers,summer"},
        ...
      ]
    }
    """
    payload = request.get_json(silent=True) or {}
    items = payload.get("items") or []
    if not items:
        return jsonify({"ok": False, "error": "no items"}), 400
    with get_conn() as con:
        for it in items:
            text = (it.get("text") or "").strip()
            if not text:
                continue
            platform = (it.get("platform") or "").strip()
            lang     = (it.get("lang") or "").strip()
            kind     = (it.get("kind") or "caption").strip()
            tags     = (it.get("tags") or "").strip()
            con.execute(
                "INSERT INTO snippets (created_at, platform, lang, kind, text, tags) VALUES (?, ?, ?, ?, ?, ?)",
                (datetime.now().isoformat(timespec="seconds"), platform, lang, kind, text, tags)
            )
    return jsonify({"ok": True, "count": len(items)})

@snip_bp.route("/snippets/update", methods=["POST"])
def update():
    data = request.form or request.json or {}
    sid  = data.get("id")
    if not sid:
        return jsonify({"ok": False, "error": "missing id"}), 400
    text = (data.get("text") or "").strip()
    tags = (data.get("tags") or "").strip()
    with get_conn() as con:
        con.execute("UPDATE snippets SET text=?, tags=? WHERE id=?", (text, tags, sid))
    return jsonify({"ok": True})

@snip_bp.route("/snippets/delete", methods=["POST"])
def delete():
    data = request.form or request.json or {}
    sid  = data.get("id")
    if not sid:
        return jsonify({"ok": False, "error": "missing id"}), 400
    with get_conn() as con:
        con.execute("DELETE FROM snippets WHERE id=?", (sid,))
    return jsonify({"ok": True})

@snip_bp.route("/snippets/export.csv", methods=["GET"])
def export_csv():
    q    = (request.args.get("q") or "").strip()
    tag  = (request.args.get("tag") or "").strip()
    kind = (request.args.get("kind") or "").strip()
    sql  = "SELECT * FROM snippets WHERE 1=1"
    args = []
    if q:
        sql += " AND (text LIKE ? OR tags LIKE ?)"
        args += [f"%{q}%", f"%{q}%"]
    if tag:
        sql += " AND ((',' || ifnull(tags,'') || ',') LIKE ?)"
        args += [f"%,{tag},%"]
    if kind:
        sql += " AND kind = ?"
        args += [kind]
    sql += " ORDER BY id DESC"
    with get_conn() as con:
        rows = con.execute(sql, args).fetchall()

    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["id","created_at","platform","lang","kind","text","tags"])
    for r in rows:
        w.writerow([r["id"], r["created_at"], r["platform"], r["lang"], r["kind"], r["text"], r["tags"]])
    resp = make_response(buf.getvalue())
    resp.headers["Content-Type"] = "text/csv; charset=utf-8"
    resp.headers["Content-Disposition"] = "attachment; filename=snippets_export.csv"
    return resp

@snip_bp.route("/snippets/export.txt", methods=["GET"])
def export_txt():
    q    = (request.args.get("q") or "").strip()
    tag  = (request.args.get("tag") or "").strip()
    kind = (request.args.get("kind") or "").strip()
    sql  = "SELECT * FROM snippets WHERE 1=1"
    args = []
    if q:
        sql += " AND (text LIKE ? OR tags LIKE ?)"
        args += [f"%{q}%", f"%{q}%"]
    if tag:
        sql += " AND ((',' || ifnull(tags,'') || ',') LIKE ?)"
        args += [f"%,{tag},%"]
    if kind:
        sql += " AND kind = ?"
        args += [kind]
    sql += " ORDER BY id DESC"
    with get_conn() as con:
        rows = con.execute(sql, args).fetchall()

    lines = []
    for r in rows:
        lines.append(r["text"])
    txt = "\n\n".join(lines)
    resp = make_response(txt)
    resp.headers["Content-Type"] = "text/plain; charset=utf-8"
    resp.headers["Content-Disposition"] = "attachment; filename=snippets_export.txt"
    return resp

@snip_bp.route("/snippets/backup", methods=["GET"])
def backup_db():
    # Κατεβάζει ΑΥΤΟ το sqlite db όπως είναι
    return send_file(DB_PATH, as_attachment=True, download_name="snippets.db")
