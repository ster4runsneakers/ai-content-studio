# routes_ab.py
import hashlib, random, io, csv
from datetime import datetime, timedelta
from flask import Blueprint, request, render_template, jsonify, redirect, url_for, Response
from werkzeug.exceptions import NotFound, BadRequest
from models import db, ABTest, CaptionVariant, ABEvent

ab_bp = Blueprint("ab", __name__, url_prefix="/ab")

# ------------------------------
# Helpers
# ------------------------------
def _hash_ip(ip: str | None) -> str | None:
    if not ip: return None
    try: return hashlib.sha256(ip.encode("utf-8")).hexdigest()
    except Exception: return None

def _pick_weighted(variants: list[CaptionVariant]) -> CaptionVariant:
    """Ασφαλής επιλογή με βάρη (αγνοεί μη-θετικά, fallback σε ίσα βάρη)."""
    if not variants: raise ValueError("No variants")
    weights = [max(0.0, float(v.weight or 0)) for v in variants]
    total = sum(weights)
    if total <= 0:
        # όλα μη-θετικά → ίσα βάρη
        idx = random.randrange(len(variants))
        return variants[idx]
    r = random.random() * total
    upto = 0.0
    for v, w in zip(variants, weights):
        upto += w
        if upto >= r:
            return v
    return variants[-1]

def _should_count_impression(test_id: str, ip_hash: str | None, window_sec: int = 900) -> bool:
    """Μην μετράς συνεχόμενα impressions από τον ίδιο IP (hash) για μικρό διάστημα."""
    if not ip_hash: 
        return True
    last = (ABEvent.query
            .filter_by(test_id=test_id, event="impression", ip_hash=ip_hash)
            .order_by(ABEvent.created_at.desc())
            .first())
    if last is None: 
        return True
    return (datetime.utcnow() - last.created_at) > timedelta(seconds=window_sec)

def _ctr(clicks: int, impr: int) -> float:
    return (clicks / impr) if impr else 0.0

def _copy_rate(copies: int, impr: int) -> float:
    return (copies / impr) if impr else 0.0

def _z_test_two_props(x1, n1, x2, n2):
    """Διπλό αναλογιών (περίπου), γρήγορο για CTR. Επιστρέφει z, p (διπλής ουράς)."""
    # Προστασίες
    if n1 == 0 or n2 == 0: 
        return 0.0, 1.0
    p1, p2 = x1 / n1, x2 / n2
    p = (x1 + x2) / (n1 + n2)
    import math
    denom = math.sqrt(p * (1 - p) * (1/n1 + 1/n2)) or 1e-9
    z = (p1 - p2) / denom
    # approx p-value (διπλής ουράς)
    # Φ(z) ~ 0.5*(1+erf(z/sqrt(2)))
    pval = 2 * (1 - 0.5 * (1 + math.erf(abs(z) / math.sqrt(2))))
    return z, pval

def _winner_by_ctr(variants, min_impr=50, alpha=0.05):
    """Σύγκρινε το καλύτερο CTR με τον 2ο καλύτερο. Αν είναι σημαντική η διαφορά → winner."""
    if len(variants) < 2: 
        return None
    # Ταξινόμηση κατά CTR
    scored = []
    for v in variants:
        if v.impressions >= min_impr:
            scored.append((v, _ctr(v.clicks, v.impressions)))
    if len(scored) < 2:
        return None
    scored.sort(key=lambda t: t[1], reverse=True)
    best, best_ctr = scored[0]
    second, second_ctr = scored[1]
    # z-test
    _, p = _z_test_two_props(best.clicks, best.impressions, second.clicks, second.impressions)
    if p < alpha:
        return {"variant_id": best.id, "label": best.label, "ctr": best_ctr, "p_value": p}
    return None

# ------------------------------
# Views
# ------------------------------
@ab_bp.route("/")
def index():
    """Λίστα tests με γρήγορη σύνοψη."""
    tests = ABTest.query.order_by(ABTest.created_at.desc()).all()
    summary = []
    for t in tests:
        total_impr = sum(v.impressions for v in t.variants)
        total_clicks = sum(v.clicks for v in t.variants)
        total_copies = sum(v.copies for v in t.variants)
        summary.append({
            "test": t,
            "total_impr": total_impr,
            "total_clicks": total_clicks,
            "total_copies": total_copies,
            "ctr": _ctr(total_clicks, total_impr),
            "copy_rate": _copy_rate(total_copies, total_impr),
        })
    return render_template("ab_index.html", rows=summary)


@ab_bp.route("/new", methods=["GET", "POST"])
def create_test():
    if request.method == "GET":
        return render_template("ab_new.html")

    data = request.form
    name = (data.get("name") or "TikTok Caption Test").strip()
    platform = (data.get("platform") or "tiktok").strip()
    target_url = (data.get("target_url") or "").strip() or None

    labels = ["A","B","C","D"]
    pairs = []
    for lbl in labels:
        txt = (data.get(f"text_{lbl}") or "").strip()
        if txt:
            try:
                w = float(data.get(f"weight_{lbl}", "1") or 1)
            except Exception:
                w = 1.0
            if w < 0: w = 0
            pairs.append((lbl, txt, w))

    if len(pairs) < 2:
        return render_template("ab_new.html", error="Χρειάζονται τουλάχιστον 2 captions.")

    test = ABTest(name=name, platform=platform, target_url=target_url)
    db.session.add(test); db.session.flush()
    for lbl, txt, w in pairs:
        db.session.add(CaptionVariant(test_id=test.id, label=lbl, text=txt, weight=w))
    db.session.commit()
    return redirect(url_for("ab.view_test", test_id=test.id))

@ab_bp.route("/<test_id>")
def view_test(test_id):
    test = ABTest.query.get(test_id)
    if not test: 
        raise NotFound("Test not found")
    winner = _winner_by_ctr(test.variants, min_impr=50, alpha=0.05)
    return render_template("ab_view.html", test=test, winner=winner)

@ab_bp.route("/serve/<test_id>")
def serve_variant(test_id):
    test = ABTest.query.get(test_id)
    if not test: 
        return jsonify({"error":"test_not_found"}), 404
    if not test.variants: 
        return jsonify({"error":"no_variants"}), 404

    try: 
        variant = _pick_weighted(test.variants)
    except Exception: 
        variant = random.choice(test.variants)

    ip_hash = _hash_ip(request.remote_addr)

    # Rate-limit impressions ανά IP
    if _should_count_impression(test.id, ip_hash, window_sec=900):
        variant.impressions += 1
        ev = ABEvent(test_id=test.id, variant_id=variant.id, event="impression",
                     user_agent=request.headers.get("User-Agent"),
                     ip_hash=ip_hash)
        db.session.add(ev)
        db.session.commit()

    return jsonify({
        "test_id": test.id,
        "variant_id": variant.id,
        "label": variant.label,
        "text": variant.text,
        "target_url": test.target_url
    })

@ab_bp.route("/event", methods=["POST"])
def track_event():
    try:
        data = request.get_json(force=True) or {}
    except Exception:
        raise BadRequest("Invalid JSON")

    test_id = (data.get("test_id") or "").strip()
    variant_id = (data.get("variant_id") or "").strip()
    event = (data.get("event") or "").strip().lower()
    if event not in {"copy","click"}:
        raise BadRequest("Invalid event type")

    test = ABTest.query.get(test_id)
    if not test: raise NotFound("Test not found")
    variant = CaptionVariant.query.get(variant_id)
    if not variant or variant.test_id != test.id:
        raise NotFound("Variant not found")

    if event == "copy": variant.copies += 1
    if event == "click": variant.clicks += 1

    ev = ABEvent(test_id=test.id, variant_id=variant.id, event=event,
                 user_agent=request.headers.get("User-Agent"),
                 ip_hash=_hash_ip(request.remote_addr))
    db.session.add(ev); db.session.commit()
    return jsonify({"ok": True})

@ab_bp.route("/<test_id>/export.csv")
def export_csv(test_id):
    test = ABTest.query.get(test_id)
    if not test:
        return jsonify({"error": "test_not_found"}), 404

    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["test_id","test_name","platform","variant","text","weight",
                "impressions","copies","clicks","ctr_clicks_impr","copy_rate"])
    for v in test.variants:
        ctr = _ctr(v.clicks, v.impressions)
        cpr = _copy_rate(v.copies, v.impressions)
        w.writerow([test.id, test.name, test.platform,
                    v.label, v.text.replace("\n"," ").strip(),
                    f"{(v.weight or 0):.2f}",
                    v.impressions, v.copies, v.clicks,
                    f"{ctr:.4f}", f"{cpr:.4f}"])
    return Response(buf.getvalue(),
                    mimetype="text/csv",
                    headers={"Content-Disposition": f'attachment; filename="ab_{test.id}.csv"'})

# --- Admin actions ---
@ab_bp.route("/<test_id>/toggle", methods=["POST"])
def toggle_active(test_id):
    t = ABTest.query.get_or_404(test_id)
    t.is_active = not t.is_active
    db.session.commit()
    return redirect(url_for("ab.view_test", test_id=test_id))

@ab_bp.route("/<test_id>/duplicate", methods=["POST"])
def duplicate_test(test_id):
    t = ABTest.query.get_or_404(test_id)
    t2 = ABTest(name=f"{t.name} (copy)", platform=t.platform, target_url=t.target_url)
    db.session.add(t2); db.session.flush()
    for v in t.variants:
        db.session.add(CaptionVariant(test_id=t2.id, label=v.label, text=v.text, weight=v.weight))
    db.session.commit()
    return redirect(url_for("ab.view_test", test_id=t2.id))

@ab_bp.route("/<test_id>/delete", methods=["POST"])
def delete_test(test_id):
    t = ABTest.query.get_or_404(test_id)
    db.session.delete(t)
    db.session.commit()
    return redirect(url_for("ab.index"))
