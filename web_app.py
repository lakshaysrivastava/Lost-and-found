# ============================================================
# web_app.py - Lost & Found Management System (Flask web UI)
# Run:  python web_app.py   then open http://127.0.0.1:5000
# ============================================================
import csv
import io
import math
import os
import secrets
import time
import uuid
from datetime import date
from functools import wraps
from pathlib import Path

from flask import (Flask, Response, abort, flash, g, redirect, render_template,
                   request, send_from_directory, session, url_for)
from jinja2 import ChoiceLoader, FileSystemLoader
from werkzeug.utils import secure_filename

import db

BASE_DIR = Path(__file__).parent
UPLOAD_DIR = BASE_DIR / "static" / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
ALLOWED_EXT = {"png", "jpg", "jpeg", "gif", "webp"}
PER_PAGE = 8

# static_folder=None: we serve static files ourselves (see static_files below) so the
# project works both with templates/ + static/ folders AND with all files in one folder.
app = Flask(__name__, static_folder=None)
app.jinja_loader = ChoiceLoader([FileSystemLoader(str(BASE_DIR / "templates")),
                                 FileSystemLoader(str(BASE_DIR))])
app.config["MAX_CONTENT_LENGTH"] = 4 * 1024 * 1024  # 4 MB uploads


@app.route("/static/<path:filename>", endpoint="static")
def static_files(filename):
    """Serve css/uploads. Falls back to style.css in the project root (flat layout).
    Only style.css is ever served from the root, so .py/.db files stay private."""
    if (BASE_DIR / "static" / filename).is_file():
        return send_from_directory(BASE_DIR / "static", filename)
    if filename == "style.css" and (BASE_DIR / "style.css").is_file():
        return send_from_directory(BASE_DIR, "style.css")
    abort(404)


def _load_secret_key():
    """Use env var if set, otherwise generate once and keep it in a local file."""
    if os.environ.get("SECRET_KEY"):
        return os.environ["SECRET_KEY"]
    key_file = BASE_DIR / ".secret_key"
    if not key_file.exists():
        key_file.write_text(secrets.token_hex(32))
    return key_file.read_text().strip()


app.secret_key = _load_secret_key()
db.get_connection().close()  # create / migrate tables on startup


# ---------------------------------------------------------------
# Security helpers: CSRF token, login throttling, role decorators
# ---------------------------------------------------------------
def csrf_token():
    if "_csrf" not in session:
        session["_csrf"] = secrets.token_hex(16)
    return session["_csrf"]


@app.before_request
def check_csrf():
    if request.method == "POST":
        sent = request.form.get("_csrf", "")
        if not sent or not secrets.compare_digest(sent, session.get("_csrf", "")):
            abort(400, "Invalid or missing CSRF token. Go back, refresh the page and retry.")


FAILED = {}  # ip -> (count, first_failure_time)
MAX_TRIES, LOCK_SECONDS = 5, 300


def is_locked(ip):
    count, first = FAILED.get(ip, (0, 0))
    if count >= MAX_TRIES and time.time() - first < LOCK_SECONDS:
        return True
    if time.time() - first >= LOCK_SECONDS:
        FAILED.pop(ip, None)
    return False


def record_failure(ip):
    count, first = FAILED.get(ip, (0, time.time()))
    FAILED[ip] = (count + 1, first)


def login_required(view):
    @wraps(view)
    def wrapped(*a, **kw):
        if not session.get("role"):
            return redirect(url_for("login", next=request.path))
        return view(*a, **kw)
    return wrapped


def admin_required(view):
    @wraps(view)
    def wrapped(*a, **kw):
        if session.get("role") != "admin":
            flash("That page is for administrators only.", "error")
            return redirect(url_for("dashboard") if session.get("role") else url_for("login"))
        return view(*a, **kw)
    return wrapped


def is_admin():
    return session.get("role") == "admin"


def actor():
    return session.get("username", "anonymous")


def notif_id():
    return db.ADMIN_NOTIFY_ID if is_admin() else session.get("user_id")


@app.context_processor
def inject_globals():
    unread = 0
    if session.get("role"):
        try:
            unread = db.unread_count(notif_id())
        except Exception:
            pass
    return dict(csrf_token=csrf_token, is_admin=is_admin(), unread=unread,
                categories=db.CATEGORIES, current_user=session.get("name"))


# ---------------------------------------------------------------
# Small utilities
# ---------------------------------------------------------------
def save_image(file_storage):
    """Validate + store an uploaded image, returns stored filename or None."""
    if not file_storage or not file_storage.filename:
        return None
    ext = file_storage.filename.rsplit(".", 1)[-1].lower()
    if ext not in ALLOWED_EXT:
        raise ValueError("Image must be png, jpg, jpeg, gif or webp.")
    name = f"{uuid.uuid4().hex}_{secure_filename(file_storage.filename)}"
    file_storage.save(UPLOAD_DIR / name)
    return name


def valid_date(text):
    try:
        return date.fromisoformat(text) <= date.today()
    except ValueError:
        return False


def clean_phone(text):
    digits = "".join(c for c in text if c.isdigit())
    return 7 <= len(digits) <= 15


def pagination(total, page):
    return dict(page=page, pages=max(1, math.ceil(total / PER_PAGE)), total=total)


@app.errorhandler(400)
def bad_request(e):
    return render_template("error.html", code=400, message=e.description), 400


@app.errorhandler(404)
def not_found(e):
    return render_template("error.html", code=404, message="Page not found."), 404


@app.errorhandler(413)
def too_large(e):
    return render_template("error.html", code=413, message="Image is too large (max 4 MB)."), 413


# ---------------------------------------------------------------
# Authentication
# ---------------------------------------------------------------
@app.route("/", methods=["GET", "POST"])
@app.route("/login", methods=["GET", "POST"])
def login():
    if session.get("role"):
        return redirect(url_for("dashboard"))
    if request.method == "POST":
        ip = request.remote_addr
        if is_locked(ip):
            flash("Too many failed attempts. Try again in a few minutes.", "error")
            return render_template("login.html"), 429
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        role = request.form.get("role", "student")
        if role == "admin" and db.verify_admin(username, password):
            session.clear()
            session.update(role="admin", username=username, name="Administrator")
            db.log_activity(username, "Login", "Admin signed in")
            return redirect(request.args.get("next") or url_for("dashboard"))
        user = db.verify_user(username, password) if role == "student" else None
        if user:
            session.clear()
            session.update(role="student", username=user["username"],
                           user_id=user["user_id"], name=user["full_name"])
            db.log_activity(username, "Login", "Student signed in")
            return redirect(request.args.get("next") or url_for("dashboard"))
        record_failure(ip)
        flash("Invalid username or password.", "error")
    return render_template("login.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        f = {k: request.form.get(k, "").strip() for k in
             ("username", "full_name", "email", "phone", "password", "confirm")}
        error = None
        if not f["username"] or not f["full_name"] or not f["password"]:
            error = "Username, full name and password are required."
        elif len(f["username"]) < 3 or not f["username"].replace("_", "").isalnum():
            error = "Username must be 3+ letters/numbers/underscores."
        elif len(f["password"]) < 6:
            error = "Password must be at least 6 characters."
        elif f["password"] != f["confirm"]:
            error = "Passwords do not match."
        elif f["email"] and ("@" not in f["email"] or "." not in f["email"]):
            error = "Enter a valid email address."
        elif f["phone"] and not clean_phone(f["phone"]):
            error = "Enter a valid phone number."
        if error:
            flash(error, "error")
        elif db.register_user(f["username"], f["full_name"], f["email"], f["phone"], f["password"]) is None:
            flash("That username is already taken.", "error")
        else:
            db.log_activity(f["username"], "Registered", "New student account")
            flash("Account created. Please sign in.", "success")
            return redirect(url_for("login"))
    return render_template("register.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    if request.method == "POST":
        new = request.form.get("new_password", "")
        if len(new) < 6:
            flash("New password must be at least 6 characters.", "error")
        elif new != request.form.get("confirm", ""):
            flash("New passwords do not match.", "error")
        else:
            ident = session["username"] if is_admin() else session["user_id"]
            if db.change_password(session["role"], ident, request.form.get("old_password", ""), new):
                db.log_activity(actor(), "Password changed")
                flash("Password updated.", "success")
            else:
                flash("Current password is incorrect.", "error")
    user = None if is_admin() else db.get_user(session["user_id"])
    return render_template("profile.html", user=user)


# ---------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------
@app.route("/dashboard")
@login_required
def dashboard():
    uid = None if is_admin() else session["user_id"]
    stats = db.get_analytics()
    mine = None
    if not is_admin():
        mine = dict(lost=db.all_items("lost", user_id=uid), found=db.all_items("found", user_id=uid))
    recent_lost, _ = db.search_items("lost", per_page=5)
    recent_found, _ = db.search_items("found", per_page=5)
    top_matches = db.get_scored_matches()[:3] if is_admin() else []
    max_cat = max([c["lost"] + c["found"] for c in stats["categories"]] or [1])
    max_trend = max([t["lost"] + t["found"] for t in stats["trend"]] or [1])
    return render_template("dashboard.html", stats=stats, lost=recent_lost, found=recent_found,
                           matches=top_matches, mine=mine, max_cat=max_cat, max_trend=max_trend)


# ---------------------------------------------------------------
# Lost / Found items (shared logic via <kind>)
# ---------------------------------------------------------------
def _check_kind(kind):
    if kind not in ("lost", "found"):
        abort(404)


def _can_modify(item):
    return is_admin() or (item["user_id"] and item["user_id"] == session.get("user_id"))


@app.route("/<kind>")
@login_required
def items(kind):
    _check_kind(kind)
    page = request.args.get("page", 1, type=int)
    filters = dict(q=request.args.get("q", "").strip(), category=request.args.get("category", ""),
                   status=request.args.get("status", ""), date_from=request.args.get("date_from", ""),
                   date_to=request.args.get("date_to", ""), sort=request.args.get("sort", "newest"))
    # students see all found items (to claim) but only their own lost reports
    if kind == "lost" and not is_admin():
        filters["user_id"] = session["user_id"]
    elif request.args.get("mine") and not is_admin():
        filters["user_id"] = session["user_id"]
    rows, total = db.search_items(kind, page=page, per_page=PER_PAGE, **filters)
    pg = pagination(total, page)
    args = {k: v for k, v in request.args.items() if k != "page"}
    return render_template("items.html", kind=kind, rows=rows, pg=pg, f=request.args, args=args)


@app.route("/<kind>/new", methods=["GET", "POST"])
@login_required
def new_item(kind):
    _check_kind(kind)
    form = {}
    if request.method == "POST":
        form = {k: request.form.get(k, "").strip() for k in
                ("name", "category", "description", "location", "item_date", "person", "contact")}
        if not is_admin():  # students: person details come from their account
            user = db.get_user(session["user_id"])
            form["person"] = form["person"] or user["full_name"]
            form["contact"] = form["contact"] or user["phone"] or user["email"] or ""
        error = validate_item(form)
        image = None
        if not error:
            try:
                image = save_image(request.files.get("image"))
            except ValueError as exc:
                error = str(exc)
        if error:
            flash(error, "error")
        else:
            uid = None if is_admin() else session["user_id"]
            item_id = db.create_item(kind, form["name"], form["category"], form["description"],
                                     form["location"], form["item_date"], form["person"],
                                     form["contact"], image, uid)
            db.log_activity(actor(), f"{kind.title()} item reported", f"#{item_id} {form['name']}")
            hits = db.notify_on_new_item(kind, item_id)
            flash(f"{kind.title()} item reported successfully."
                  + (f" {hits} possible match(es) found!" if hits and is_admin() else ""), "success")
            return redirect(url_for("item_detail", kind=kind, item_id=item_id))
    return render_template("item_form.html", kind=kind, item=None, form=form, today=str(date.today()))


def validate_item(form):
    if not form["name"]:
        return "Item name is required."
    if len(form["name"]) > 100:
        return "Item name is too long (max 100 characters)."
    if not form["category"]:
        return "Please choose a category."
    if not form["person"] or not form["contact"]:
        return "Name and contact are required."
    if not clean_phone(form["contact"]) and "@" not in form["contact"]:
        return "Contact must be a valid phone number or email."
    if not valid_date(form["item_date"]):
        return "Enter a valid date that is not in the future."
    return None


@app.route("/<kind>/<int:item_id>")
@login_required
def item_detail(kind, item_id):
    _check_kind(kind)
    item = db.get_item(kind, item_id)
    if not item:
        abort(404)
    item["stale"] = db.is_stale(item)
    matches = []
    if item["status"] == "Pending" and (is_admin() or _can_modify(item)):
        matches = db.get_scored_matches(lost_id=item_id if kind == "lost" else None,
                                        found_id=item_id if kind == "found" else None)[:5]
    my_lost, request_sent = [], False
    if kind == "found" and not is_admin():
        my_lost = [l for l in db.all_items("lost", user_id=session["user_id"], status="Pending")]
        request_sent = any(r["found_id"] == item_id and r["status"] == "Pending"
                           for r in db.list_claim_requests(user_id=session["user_id"]))
    show_contact = is_admin() or _can_modify(item)
    return render_template("item_detail.html", kind=kind, item=item, matches=matches,
                           my_lost=my_lost, request_sent=request_sent, show_contact=show_contact,
                           can_edit=_can_modify(item))


@app.route("/<kind>/<int:item_id>/edit", methods=["GET", "POST"])
@login_required
def edit_item(kind, item_id):
    _check_kind(kind)
    item = db.get_item(kind, item_id)
    if not item:
        abort(404)
    if not _can_modify(item):
        abort(404)
    form = {}
    if request.method == "POST":
        form = {k: request.form.get(k, "").strip() for k in
                ("name", "category", "description", "location", "item_date", "person", "contact")}
        error = validate_item(form)
        image = None
        if not error:
            try:
                image = save_image(request.files.get("image"))
            except ValueError as exc:
                error = str(exc)
        if error:
            flash(error, "error")
        else:
            db.update_item(kind, item_id, form["name"], form["category"], form["description"],
                           form["location"], form["item_date"], form["person"], form["contact"], image)
            db.log_activity(actor(), f"{kind.title()} item edited", f"#{item_id} {form['name']}")
            flash("Report updated.", "success")
            return redirect(url_for("item_detail", kind=kind, item_id=item_id))
    return render_template("item_form.html", kind=kind, item=item, form=form, today=str(date.today()))


@app.route("/<kind>/<int:item_id>/delete", methods=["POST"])
@login_required
def delete_item(kind, item_id):
    _check_kind(kind)
    item = db.get_item(kind, item_id)
    if not item or not _can_modify(item):
        abort(404)
    db.delete_item(kind, item_id)
    db.log_activity(actor(), f"{kind.title()} item deleted", f"#{item_id} {item['name']}")
    flash("Report deleted.", "success")
    return redirect(url_for("items", kind=kind))


@app.route("/<kind>/<int:item_id>/status", methods=["POST"])
@admin_required
def change_status(kind, item_id):
    _check_kind(kind)
    status = request.form.get("status")
    if status not in ("Pending", "Claimed"):
        abort(400, "Bad status")
    db.set_item_status(kind, item_id, status)
    db.log_activity(actor(), "Status changed", f"{kind} #{item_id} -> {status}")
    flash(f"Marked as {status}.", "success")
    return redirect(request.referrer or url_for("items", kind=kind))


# ---------------------------------------------------------------
# Matches + claims
# ---------------------------------------------------------------
@app.route("/matches")
@admin_required
def matches():
    threshold = request.args.get("min", db.MATCH_THRESHOLD, type=int)
    return render_template("matches.html", matches=db.get_scored_matches(threshold), threshold=threshold)


@app.route("/claim", methods=["POST"])
@admin_required
def claim():
    lost_id = request.form.get("lost_id", type=int)
    found_id = request.form.get("found_id", type=int)
    remarks = request.form.get("remarks", "").strip()
    lost, found = db.get_item("lost", lost_id or 0), db.get_item("found", found_id or 0)
    if not lost or not found:
        flash("Choose one valid lost report and one valid found report.", "error")
        return redirect(url_for("matches"))
    if lost["status"] == "Claimed" or found["status"] == "Claimed":
        flash("One of those reports is already claimed.", "error")
        return redirect(url_for("matches"))
    cid = db.complete_claim(lost_id, found_id, remarks, actor())
    if lost["user_id"]:
        db.notify(lost["user_id"], f"Good news! Your lost '{lost['name']}' has been recovered. "
                                   "Collect it from the admin office.", f"/receipt/{cid}")
    flash("Item marked as returned. You can print the receipt.", "success")
    return redirect(url_for("receipt", claim_id=cid))


@app.route("/claim-request", methods=["POST"])
@login_required
def claim_request():
    if is_admin():
        abort(404)
    found_id = request.form.get("found_id", type=int)
    lost_id = request.form.get("lost_id", type=int)
    proof = request.form.get("proof", "").strip()
    found = db.get_item("found", found_id or 0)
    if not found or found["status"] != "Pending":
        flash("That item is not available to claim.", "error")
        return redirect(url_for("items", kind="found"))
    if len(proof) < 10:
        flash("Please describe proof of ownership (marks, contents, serial no.) in at least 10 characters.", "error")
        return redirect(url_for("item_detail", kind="found", item_id=found_id))
    if lost_id:
        own = db.get_item("lost", lost_id)
        if not own or own["user_id"] != session["user_id"]:
            lost_id = None
    if db.create_claim_request(found_id, session["user_id"], proof, lost_id) is None:
        flash("You already have a pending claim request for this item.", "error")
    else:
        db.log_activity(actor(), "Claim requested", f"found #{found_id}")
        flash("Claim request sent. The admin will review it.", "success")
    return redirect(url_for("my_claims"))


@app.route("/my-claims")
@login_required
def my_claims():
    if is_admin():
        return redirect(url_for("claims"))
    return render_template("my_claims.html", requests=db.list_claim_requests(user_id=session["user_id"]))


@app.route("/claims")
@admin_required
def claims():
    return render_template("claims.html", pending=db.list_claim_requests(status="Pending"),
                           decided=[r for r in db.list_claim_requests() if r["status"] != "Pending"],
                           history=db.list_claims())


@app.route("/claims/<int:request_id>/decide", methods=["POST"])
@admin_required
def decide_claim(request_id):
    approve = request.form.get("decision") == "approve"
    if db.decide_claim_request(request_id, approve, request.form.get("remarks", "").strip(), actor()):
        flash("Claim approved: item marked returned." if approve else "Claim rejected.", "success")
    else:
        flash("That request was already handled.", "error")
    return redirect(url_for("claims"))


@app.route("/receipt/<int:claim_id>")
@login_required
def receipt(claim_id):
    claim = db.get_claim(claim_id)
    if not claim:
        abort(404)
    return render_template("receipt.html", c=claim)


# ---------------------------------------------------------------
# Notifications, activity log, users, CSV export
# ---------------------------------------------------------------
@app.route("/notifications")
@login_required
def notifications():
    uid = notif_id()
    rows = db.get_notifications(uid)
    db.mark_notifications_read(uid)
    return render_template("notifications.html", rows=rows)


@app.route("/activity")
@admin_required
def activity():
    return render_template("activity.html", logs=db.get_logs())


@app.route("/users")
@admin_required
def users():
    return render_template("users.html", users=db.list_users())


@app.route("/export/<name>.csv")
@admin_required
def export_csv(name):
    if name in ("lost", "found"):
        rows = db.all_items(name)
        cols = ["id", "name", "category", "description", "location", "item_date",
                "person", "contact", "status", "date_reported"]
    elif name == "claims":
        rows = db.list_claims()
        cols = ["claim_id", "claim_date", "lost_name", "reporter_name", "found_name",
                "founder_name", "match_score", "handled_by", "remarks"]
    else:
        abort(404)
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(cols)
    for r in rows:
        writer.writerow([r.get(c, "") for c in cols])
    db.log_activity(actor(), "Export", f"{name}.csv")
    return Response(buf.getvalue(), mimetype="text/csv",
                    headers={"Content-Disposition": f"attachment; filename={name}_{date.today()}.csv"})


if __name__ == "__main__":
    import threading
    import webbrowser
    # open the browser automatically once the server is up
    threading.Timer(1.2, lambda: webbrowser.open("http://127.0.0.1:5000")).start()
    app.run(host="127.0.0.1", port=5000, debug=False)
