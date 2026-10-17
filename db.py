# ============================================================
# db.py
# All database access functions for the Lost & Found system.
# The app now uses SQLite by default so it can run locally
# without a MySQL server.
# ============================================================

import sqlite3
from datetime import date, datetime
from difflib import SequenceMatcher
from pathlib import Path

from werkzeug.security import check_password_hash, generate_password_hash

from config import DB_CONFIG

DB_PATH = Path(__file__).with_name("lost_found.db")


def _is_sqlite():
    return str(DB_CONFIG.get("type", "sqlite")).lower() == "sqlite"


def _init_sqlite_schema(conn):
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS admin (
            admin_id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS lost_items (
            lost_id INTEGER PRIMARY KEY AUTOINCREMENT,
            item_name TEXT NOT NULL,
            category TEXT,
            description TEXT,
            location_lost TEXT,
            date_lost TEXT,
            reporter_name TEXT NOT NULL,
            reporter_contact TEXT,
            status TEXT DEFAULT 'Pending',
            date_reported TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS found_items (
            found_id INTEGER PRIMARY KEY AUTOINCREMENT,
            item_name TEXT NOT NULL,
            category TEXT,
            description TEXT,
            location_found TEXT,
            date_found TEXT,
            founder_name TEXT NOT NULL,
            founder_contact TEXT,
            status TEXT DEFAULT 'Pending',
            date_reported TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS claims (
            claim_id INTEGER PRIMARY KEY AUTOINCREMENT,
            lost_id INTEGER,
            found_id INTEGER,
            claim_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (lost_id) REFERENCES lost_items(lost_id) ON DELETE CASCADE,
            FOREIGN KEY (found_id) REFERENCES found_items(found_id) ON DELETE CASCADE
        )
        """
    )

    conn.execute(
        """INSERT INTO admin (username, password)
           SELECT ?, ?
           WHERE NOT EXISTS (SELECT 1 FROM admin WHERE username = ?)
        """,
        ("admin", "admin123", "admin"),
    )

    lost_count = conn.execute("SELECT COUNT(*) FROM lost_items").fetchone()[0]
    if lost_count == 0:
        conn.execute(
            """
            INSERT INTO lost_items (
                item_name, category, description, location_lost, date_lost,
                reporter_name, reporter_contact
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "Blue Water Bottle",
                "Accessories",
                "Steel bottle with a college sticker on it",
                "Library",
                "2026-08-08",
                "Rahul Sharma",
                "9876543210",
            ),
        )

    found_count = conn.execute("SELECT COUNT(*) FROM found_items").fetchone()[0]
    if found_count == 0:
        conn.execute(
            """
            INSERT INTO found_items (
                item_name, category, description, location_found, date_found,
                founder_name, founder_contact
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "Water Bottle",
                "Accessories",
                "Blue steel bottle found near reading hall",
                "Library",
                "2026-08-08",
                "Security Desk",
                "9123456780",
            ),
        )

    conn.commit()


def _connect_sqlite():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    _init_sqlite_schema(conn)
    _migrate(conn)
    return conn


def get_connection():
    """Open and return a connection to the configured database."""
    if _is_sqlite():
        return _connect_sqlite()

    try:
        import mysql.connector

        mysql_config = {k: v for k, v in DB_CONFIG.items() if k != "type"}
        return mysql.connector.connect(**mysql_config)
    except Exception:
        return _connect_sqlite()


def _execute(conn, query, params=()):
    if isinstance(conn, sqlite3.Connection):
        query = query.replace("%s", "?")
    cur = conn.cursor()
    cur.execute(query, params)
    return cur


# ---------------------------------------------------------------
# ADMIN LOGIN
# ---------------------------------------------------------------
def verify_admin(username, password):
    """Check admin credentials (passwords are stored hashed)."""
    conn = get_connection()
    cur = _execute(conn, "SELECT password FROM admin WHERE username=?", (username,))
    row = cur.fetchone()
    cur.close()
    conn.close()
    return row is not None and check_password_hash(row[0], password)


# ---------------------------------------------------------------
# LOST ITEMS
# ---------------------------------------------------------------
def add_lost_item(item_name, category, description, location_lost,
                   date_lost, reporter_name, reporter_contact):
    conn = get_connection()
    cur = _execute(
        conn,
        """INSERT INTO lost_items
           (item_name, category, description, location_lost, date_lost,
            reporter_name, reporter_contact)
           VALUES (?,?,?,?,?,?,?)""",
        (item_name, category, description, location_lost,
         date_lost, reporter_name, reporter_contact),
    )
    conn.commit()
    cur.close()
    conn.close()


def get_all_lost_items():
    conn = get_connection()
    cur = _execute(
        conn,
        """SELECT lost_id, item_name, category, location_lost,
                  date_lost, reporter_name, reporter_contact, status
           FROM lost_items ORDER BY lost_id DESC""",
    )
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows


def delete_lost_item(lost_id):
    conn = get_connection()
    cur = _execute(conn, "DELETE FROM lost_items WHERE lost_id=?", (lost_id,))
    conn.commit()
    cur.close()
    conn.close()


def update_lost_status(lost_id, status):
    conn = get_connection()
    cur = _execute(conn, "UPDATE lost_items SET status=? WHERE lost_id=?", (status, lost_id))
    conn.commit()
    cur.close()
    conn.close()


# ---------------------------------------------------------------
# FOUND ITEMS
# ---------------------------------------------------------------
def add_found_item(item_name, category, description, location_found,
                    date_found, founder_name, founder_contact):
    conn = get_connection()
    cur = _execute(
        conn,
        """INSERT INTO found_items
           (item_name, category, description, location_found, date_found,
            founder_name, founder_contact)
           VALUES (?,?,?,?,?,?,?)""",
        (item_name, category, description, location_found,
         date_found, founder_name, founder_contact),
    )
    conn.commit()
    cur.close()
    conn.close()


def get_all_found_items():
    conn = get_connection()
    cur = _execute(
        conn,
        """SELECT found_id, item_name, category, location_found,
                  date_found, founder_name, founder_contact, status
           FROM found_items ORDER BY found_id DESC""",
    )
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows


def delete_found_item(found_id):
    conn = get_connection()
    cur = _execute(conn, "DELETE FROM found_items WHERE found_id=?", (found_id,))
    conn.commit()
    cur.close()
    conn.close()


def update_found_status(found_id, status):
    conn = get_connection()
    cur = _execute(conn, "UPDATE found_items SET status=? WHERE found_id=?", (status, found_id))
    conn.commit()
    cur.close()
    conn.close()


# ---------------------------------------------------------------
# SEARCH (used by the Search tab, searches both tables)
# ---------------------------------------------------------------
def search_lost(keyword):
    conn = get_connection()
    like = f"%{keyword}%"
    cur = _execute(
        conn,
        """SELECT lost_id, item_name, category, location_lost,
                  date_lost, reporter_name, reporter_contact, status
           FROM lost_items
           WHERE item_name LIKE ? OR category LIKE ? OR location_lost LIKE ?
           ORDER BY lost_id DESC""",
        (like, like, like),
    )
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows


def search_found(keyword):
    conn = get_connection()
    like = f"%{keyword}%"
    cur = _execute(
        conn,
        """SELECT found_id, item_name, category, location_found,
                  date_found, founder_name, founder_contact, status
           FROM found_items
           WHERE item_name LIKE ? OR category LIKE ? OR location_found LIKE ?
           ORDER BY found_id DESC""",
        (like, like, like),
    )
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows


# ---------------------------------------------------------------
# AUTO-MATCHING: suggest possible lost/found pairs
# (same item name or same category, both still pending)
# ---------------------------------------------------------------
def find_possible_matches():
    conn = get_connection()
    if isinstance(conn, sqlite3.Connection):
        cur = _execute(
            conn,
            """SELECT l.lost_id, l.item_name, l.category, l.reporter_name,
                      f.found_id, f.item_name, f.category, f.founder_name
               FROM lost_items l
               JOIN found_items f
                 ON (LOWER(l.item_name) LIKE '%' || LOWER(f.item_name) || '%'
                     OR LOWER(f.item_name) LIKE '%' || LOWER(l.item_name) || '%'
                     OR LOWER(l.category) = LOWER(f.category))
               WHERE l.status = 'Pending' AND f.status = 'Pending'""",
        )
    else:
        cur = _execute(
            conn,
            """SELECT l.lost_id, l.item_name, l.category, l.reporter_name,
                      f.found_id, f.item_name, f.category, f.founder_name
               FROM lost_items l
               JOIN found_items f
                 ON (LOWER(l.item_name) LIKE CONCAT('%', LOWER(f.item_name), '%')
                     OR LOWER(f.item_name) LIKE CONCAT('%', LOWER(l.item_name), '%')
                     OR LOWER(l.category) = LOWER(f.category))
               WHERE l.status = 'Pending' AND f.status = 'Pending'""",
        )
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows


def mark_as_claimed(lost_id, found_id):
    """Record a claim and mark both the lost and found item as Claimed."""
    conn = get_connection()
    cur = _execute(conn, "INSERT INTO claims (lost_id, found_id) VALUES (?, ?)", (lost_id, found_id))
    cur.close()
    cur = _execute(conn, "UPDATE lost_items SET status='Claimed' WHERE lost_id=?", (lost_id,))
    cur.close()
    cur = _execute(conn, "UPDATE found_items SET status='Claimed' WHERE found_id=?", (found_id,))
    conn.commit()
    cur.close()
    conn.close()


# ---------------------------------------------------------------
# DASHBOARD STATISTICS
# ---------------------------------------------------------------
def get_stats():
    conn = get_connection()
    cur = _execute(conn, "SELECT COUNT(*) FROM lost_items")
    total_lost = cur.fetchone()[0]

    cur = _execute(conn, "SELECT COUNT(*) FROM found_items")
    total_found = cur.fetchone()[0]

    cur = _execute(conn, "SELECT COUNT(*) FROM lost_items WHERE status='Claimed'")
    lost_claimed = cur.fetchone()[0]

    cur = _execute(conn, "SELECT COUNT(*) FROM found_items WHERE status='Claimed'")
    found_claimed = cur.fetchone()[0]

    cur = _execute(conn, "SELECT COUNT(*) FROM lost_items WHERE status='Pending'")
    lost_pending = cur.fetchone()[0]

    cur = _execute(conn, "SELECT COUNT(*) FROM found_items WHERE status='Pending'")
    found_pending = cur.fetchone()[0]

    cur.close()
    conn.close()
    return {
        "total_lost": total_lost,
        "total_found": total_found,
        "lost_claimed": lost_claimed,
        "found_claimed": found_claimed,
        "lost_pending": lost_pending,
        "found_pending": found_pending,
    }


# ================================================================
# =====================  EXTENDED FEATURES  ======================
# Everything below powers the web version (web_app.py). The
# original functions above keep working for the Tkinter app.
# ================================================================
CATEGORIES = ["Electronics", "Books", "Stationery", "ID Card", "Bag",
              "Accessories", "Clothing", "Other"]
STALE_DAYS = 30            # pending items older than this are flagged
MATCH_THRESHOLD = 40       # minimum score (0-100) to show as a match
ADMIN_NOTIFY_ID = 0        # notifications.user_id used for admin inbox

# Maps a "kind" to its table and normalised column aliases.
_KINDS = {
    "lost": dict(table="lost_items", pk="lost_id", loc="location_lost",
                 date="date_lost", person="reporter_name", contact="reporter_contact"),
    "found": dict(table="found_items", pk="found_id", loc="location_found",
                  date="date_found", person="founder_name", contact="founder_contact"),
}


def _select_cols(kind):
    k = _KINDS[kind]
    return (f"{k['pk']} AS id, item_name AS name, category, description, "
            f"{k['loc']} AS location, {k['date']} AS item_date, "
            f"{k['person']} AS person, {k['contact']} AS contact, "
            f"status, date_reported, image, user_id, '{kind}' AS kind")


def _db():
    """Connection returning dict-like rows (used by the extended features)."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _rows(sql, params=()):
    conn = _db()
    try:
        return [dict(r) for r in conn.execute(sql, params).fetchall()]
    finally:
        conn.close()


def _one(sql, params=()):
    rows = _rows(sql, params)
    return rows[0] if rows else None


def _write(sql, params=()):
    conn = _db()
    try:
        cur = conn.execute(sql, params)
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def _has_column(conn, table, column):
    return any(r[1] == column for r in conn.execute(f"PRAGMA table_info({table})"))


# ---------------------------------------------------------------
# SCHEMA MIGRATION (safe to run on every start, keeps old data)
# ---------------------------------------------------------------
def _migrate(conn):
    conn.execute("""CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        full_name TEXT NOT NULL,
        email TEXT,
        phone TEXT,
        password TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")
    conn.execute("""CREATE TABLE IF NOT EXISTS claim_requests (
        request_id INTEGER PRIMARY KEY AUTOINCREMENT,
        found_id INTEGER NOT NULL,
        lost_id INTEGER,
        user_id INTEGER NOT NULL,
        proof TEXT NOT NULL,
        status TEXT DEFAULT 'Pending',
        admin_remarks TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        decided_at TIMESTAMP,
        FOREIGN KEY (found_id) REFERENCES found_items(found_id) ON DELETE CASCADE,
        FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE)""")
    conn.execute("""CREATE TABLE IF NOT EXISTS activity_log (
        log_id INTEGER PRIMARY KEY AUTOINCREMENT,
        actor TEXT, action TEXT, detail TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")
    conn.execute("""CREATE TABLE IF NOT EXISTS notifications (
        notif_id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        message TEXT NOT NULL,
        link TEXT,
        is_read INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")

    for table in ("lost_items", "found_items"):
        if not _has_column(conn, table, "image"):
            conn.execute(f"ALTER TABLE {table} ADD COLUMN image TEXT")
        if not _has_column(conn, table, "user_id"):
            conn.execute(f"ALTER TABLE {table} ADD COLUMN user_id INTEGER")
    for col in ("remarks", "match_score", "handled_by"):
        if not _has_column(conn, "claims", col):
            conn.execute(f"ALTER TABLE claims ADD COLUMN {col} "
                         f"{'INTEGER' if col == 'match_score' else 'TEXT'}")

    # upgrade any plain-text admin password to a hash
    for admin_id, pw in conn.execute("SELECT admin_id, password FROM admin").fetchall():
        if not str(pw).startswith(("pbkdf2:", "scrypt:")):
            conn.execute("UPDATE admin SET password=? WHERE admin_id=?",
                         (generate_password_hash(pw), admin_id))
    conn.commit()


# ---------------------------------------------------------------
# ACTIVITY LOG + NOTIFICATIONS
# ---------------------------------------------------------------
def log_activity(actor, action, detail=""):
    _write("INSERT INTO activity_log (actor, action, detail) VALUES (?,?,?)",
           (actor, action, detail))


def get_logs(limit=200):
    return _rows("SELECT * FROM activity_log ORDER BY log_id DESC LIMIT ?", (limit,))


def notify(user_id, message, link=None):
    _write("INSERT INTO notifications (user_id, message, link) VALUES (?,?,?)",
           (user_id, message, link))


def get_notifications(user_id, limit=50):
    return _rows("SELECT * FROM notifications WHERE user_id=? ORDER BY notif_id DESC LIMIT ?",
                 (user_id, limit))


def unread_count(user_id):
    return _one("SELECT COUNT(*) AS n FROM notifications WHERE user_id=? AND is_read=0",
                (user_id,))["n"]


def mark_notifications_read(user_id):
    _write("UPDATE notifications SET is_read=1 WHERE user_id=?", (user_id,))


# ---------------------------------------------------------------
# USERS (students / staff) + ADMIN PASSWORD
# ---------------------------------------------------------------
def register_user(username, full_name, email, phone, password):
    """Returns user_id, or None if the username is already taken."""
    try:
        return _write(
            "INSERT INTO users (username, full_name, email, phone, password) VALUES (?,?,?,?,?)",
            (username, full_name, email, phone, generate_password_hash(password)))
    except sqlite3.IntegrityError:
        return None


def verify_user(username, password):
    row = _one("SELECT * FROM users WHERE username=?", (username,))
    if row and check_password_hash(row["password"], password):
        return row
    return None


def get_user(user_id):
    return _one("SELECT user_id, username, full_name, email, phone, created_at "
                "FROM users WHERE user_id=?", (user_id,))


def change_password(role, ident, old_password, new_password):
    """role is 'admin' (ident = username) or 'student' (ident = user_id)."""
    if role == "admin":
        row = _one("SELECT password FROM admin WHERE username=?", (ident,))
        if not row or not check_password_hash(row["password"], old_password):
            return False
        _write("UPDATE admin SET password=? WHERE username=?",
               (generate_password_hash(new_password), ident))
    else:
        row = _one("SELECT password FROM users WHERE user_id=?", (ident,))
        if not row or not check_password_hash(row["password"], old_password):
            return False
        _write("UPDATE users SET password=? WHERE user_id=?",
               (generate_password_hash(new_password), ident))
    return True


def list_users():
    return _rows("""SELECT u.user_id, u.username, u.full_name, u.email, u.phone, u.created_at,
                    (SELECT COUNT(*) FROM lost_items l WHERE l.user_id=u.user_id) AS lost_count,
                    (SELECT COUNT(*) FROM found_items f WHERE f.user_id=u.user_id) AS found_count
                    FROM users u ORDER BY u.user_id DESC""")


# ---------------------------------------------------------------
# ITEMS (normalised access for both lost and found)
# ---------------------------------------------------------------
def create_item(kind, name, category, description, location, item_date,
                person, contact, image=None, user_id=None):
    k = _KINDS[kind]
    return _write(
        f"""INSERT INTO {k['table']}
            (item_name, category, description, {k['loc']}, {k['date']},
             {k['person']}, {k['contact']}, image, user_id)
            VALUES (?,?,?,?,?,?,?,?,?)""",
        (name, category, description, location, item_date, person, contact, image, user_id))


def get_item(kind, item_id):
    k = _KINDS[kind]
    return _one(f"SELECT {_select_cols(kind)} FROM {k['table']} WHERE {k['pk']}=?", (item_id,))


def update_item(kind, item_id, name, category, description, location, item_date,
                person, contact, image=None):
    k = _KINDS[kind]
    sql = (f"UPDATE {k['table']} SET item_name=?, category=?, description=?, {k['loc']}=?, "
           f"{k['date']}=?, {k['person']}=?, {k['contact']}=?")
    params = [name, category, description, location, item_date, person, contact]
    if image:
        sql += ", image=?"
        params.append(image)
    sql += f" WHERE {k['pk']}=?"
    params.append(item_id)
    _write(sql, params)


def delete_item(kind, item_id):
    k = _KINDS[kind]
    _write(f"DELETE FROM {k['table']} WHERE {k['pk']}=?", (item_id,))


def set_item_status(kind, item_id, status):
    k = _KINDS[kind]
    _write(f"UPDATE {k['table']} SET status=? WHERE {k['pk']}=?", (status, item_id))


def search_items(kind, q="", category="", status="", user_id=None,
                 date_from="", date_to="", sort="newest", page=1, per_page=8):
    """Filtered, sorted, paginated listing. Returns (rows, total_count)."""
    k = _KINDS[kind]
    where, params = [], []
    if q:
        like = f"%{q}%"
        where.append(f"(item_name LIKE ? OR description LIKE ? OR category LIKE ? "
                     f"OR {k['loc']} LIKE ?)")
        params += [like] * 4
    if category:
        where.append("category = ?"); params.append(category)
    if status:
        where.append("status = ?"); params.append(status)
    if user_id is not None:
        where.append("user_id = ?"); params.append(user_id)
    if date_from:
        where.append(f"{k['date']} >= ?"); params.append(date_from)
    if date_to:
        where.append(f"{k['date']} <= ?"); params.append(date_to)
    clause = ("WHERE " + " AND ".join(where)) if where else ""
    order = {"newest": f"{k['pk']} DESC", "oldest": f"{k['pk']} ASC",
             "name": "item_name COLLATE NOCASE ASC",
             "date": f"{k['date']} DESC"}.get(sort, f"{k['pk']} DESC")
    total = _one(f"SELECT COUNT(*) AS n FROM {k['table']} {clause}", params)["n"]
    page = max(1, page)
    rows = _rows(f"SELECT {_select_cols(kind)} FROM {k['table']} {clause} "
                 f"ORDER BY {order} LIMIT ? OFFSET ?", params + [per_page, (page - 1) * per_page])
    for r in rows:
        r["stale"] = is_stale(r)
    return rows, total


def all_items(kind, **filters):
    rows, _ = search_items(kind, per_page=100000, **filters)
    return rows


def is_stale(item):
    """Pending for more than STALE_DAYS days."""
    if item.get("status") != "Pending" or not item.get("date_reported"):
        return False
    try:
        reported = datetime.strptime(item["date_reported"][:10], "%Y-%m-%d").date()
    except ValueError:
        return False
    return (date.today() - reported).days > STALE_DAYS


# ---------------------------------------------------------------
# SMART MATCHING (scored 0-100 instead of simple name/category join)
# ---------------------------------------------------------------
def _words(text):
    return {w for w in "".join(c.lower() if c.isalnum() else " " for c in (text or "")).split()
            if len(w) > 2}


def _similar(a, b):
    a, b = (a or "").strip().lower(), (b or "").strip().lower()
    if not a or not b:
        return 0.0
    if a in b or b in a:
        return 1.0
    return SequenceMatcher(None, a, b).ratio()


def score_match(lost, found):
    """Return (score 0-100, list of reasons). Works on normalised item dicts."""
    score, reasons = 0, []

    s = _similar(lost["name"], found["name"])
    if s >= 0.5:
        pts = round(s * 35)
        score += pts; reasons.append(f"Similar name (+{pts})")

    if lost["category"] and lost["category"].lower() == (found["category"] or "").lower():
        score += 20; reasons.append("Same category (+20)")

    ls = _similar(lost["location"], found["location"])
    if ls >= 0.6:
        pts = round(ls * 15)
        score += pts; reasons.append(f"Same place (+{pts})")

    try:
        d1 = datetime.strptime(lost["item_date"][:10], "%Y-%m-%d").date()
        d2 = datetime.strptime(found["item_date"][:10], "%Y-%m-%d").date()
        gap = (d2 - d1).days
        if 0 <= gap <= 14:
            pts = 15 if gap <= 3 else 10 if gap <= 7 else 5
            score += pts; reasons.append(f"Found {gap} day(s) after loss (+{pts})")
    except (TypeError, ValueError):
        pass

    common = _words(lost["description"]) & _words(found["description"])
    if common:
        pts = min(15, len(common) * 5)
        score += pts; reasons.append(f"Shared keywords: {', '.join(sorted(common)[:4])} (+{pts})")

    return min(score, 100), reasons


def get_scored_matches(min_score=MATCH_THRESHOLD, lost_id=None, found_id=None):
    lost = all_items("lost", status="Pending")
    found = all_items("found", status="Pending")
    if lost_id:
        lost = [l for l in lost if l["id"] == lost_id]
    if found_id:
        found = [f for f in found if f["id"] == found_id]
    out = []
    for l in lost:
        for f in found:
            score, reasons = score_match(l, f)
            if score >= min_score:
                out.append(dict(lost=l, found=f, score=score, reasons=reasons))
    out.sort(key=lambda m: m["score"], reverse=True)
    return out


def notify_on_new_item(kind, item_id):
    """After a report is filed: alert admin (and the owner) if a strong match exists."""
    matches = (get_scored_matches(60, lost_id=item_id) if kind == "lost"
               else get_scored_matches(60, found_id=item_id))
    if not matches:
        return 0
    best = matches[0]
    msg = (f"Possible match ({best['score']}%): lost '{best['lost']['name']}' "
           f"and found '{best['found']['name']}'")
    notify(ADMIN_NOTIFY_ID, msg, "/matches")
    for side in ("lost", "found"):
        uid = best[side]["user_id"]
        if uid:
            notify(uid, f"We may have found a match for your report '{best[side]['name']}' "
                        f"({best['score']}% match). The admin will review it.",
                   f"/{side}/{best[side]['id']}")
    return len(matches)


# ---------------------------------------------------------------
# CLAIMS
# ---------------------------------------------------------------
def create_claim_request(found_id, user_id, proof, lost_id=None):
    existing = _one("""SELECT request_id FROM claim_requests
                       WHERE found_id=? AND user_id=? AND status='Pending'""", (found_id, user_id))
    if existing:
        return None
    rid = _write("INSERT INTO claim_requests (found_id, lost_id, user_id, proof) VALUES (?,?,?,?)",
                 (found_id, lost_id, user_id, proof))
    notify(ADMIN_NOTIFY_ID, "New claim request awaiting review", "/claims")
    return rid


def list_claim_requests(status=None, user_id=None):
    where, params = [], []
    if status:
        where.append("c.status=?"); params.append(status)
    if user_id is not None:
        where.append("c.user_id=?"); params.append(user_id)
    clause = ("WHERE " + " AND ".join(where)) if where else ""
    return _rows(f"""SELECT c.*, u.full_name, u.phone, u.email,
                            f.item_name AS found_name, f.location_found, f.image AS found_image,
                            l.item_name AS lost_name
                     FROM claim_requests c
                     JOIN users u ON u.user_id = c.user_id
                     JOIN found_items f ON f.found_id = c.found_id
                     LEFT JOIN lost_items l ON l.lost_id = c.lost_id
                     {clause} ORDER BY c.request_id DESC""", params)


def decide_claim_request(request_id, approve, remarks, admin_name):
    req = _one("SELECT * FROM claim_requests WHERE request_id=?", (request_id,))
    if not req or req["status"] != "Pending":
        return False
    if approve:
        complete_claim(req["lost_id"], req["found_id"], remarks, admin_name)
        # reject other pending requests for the same found item
        for other in _rows("""SELECT request_id, user_id FROM claim_requests
                              WHERE found_id=? AND status='Pending' AND request_id<>?""",
                           (req["found_id"], request_id)):
            _write("""UPDATE claim_requests SET status='Rejected', decided_at=CURRENT_TIMESTAMP,
                      admin_remarks='Item was returned to another claimant' WHERE request_id=?""",
                   (other["request_id"],))
            notify(other["user_id"], "Your claim request was rejected: item returned to another claimant.")
    status = "Approved" if approve else "Rejected"
    _write("""UPDATE claim_requests SET status=?, admin_remarks=?, decided_at=CURRENT_TIMESTAMP
              WHERE request_id=?""", (status, remarks, request_id))
    notify(req["user_id"], f"Your claim request was {status.lower()}."
           + (f" Remarks: {remarks}" if remarks else ""), "/my-claims")
    log_activity(admin_name, f"Claim {status}", f"Request #{request_id}, found item #{req['found_id']}")
    return True


def complete_claim(lost_id, found_id, remarks="", admin_name="admin"):
    """Mark a pair as returned; lost_id may be None (claimant had no lost report)."""
    score = None
    if lost_id:
        l, f = get_item("lost", lost_id), get_item("found", found_id)
        if l and f:
            score = score_match(l, f)[0]
    cid = _write("""INSERT INTO claims (lost_id, found_id, remarks, match_score, handled_by)
                    VALUES (?,?,?,?,?)""", (lost_id, found_id, remarks, score, admin_name))
    if lost_id:
        set_item_status("lost", lost_id, "Claimed")
    set_item_status("found", found_id, "Claimed")
    log_activity(admin_name, "Item returned", f"Lost #{lost_id or '-'} <-> Found #{found_id}")
    return cid


def list_claims():
    return _rows("""SELECT c.claim_id, c.claim_date, c.remarks, c.match_score, c.handled_by,
                           l.item_name AS lost_name, l.reporter_name, l.reporter_contact,
                           f.item_name AS found_name, f.founder_name, f.location_found
                    FROM claims c
                    LEFT JOIN lost_items l ON l.lost_id = c.lost_id
                    LEFT JOIN found_items f ON f.found_id = c.found_id
                    ORDER BY c.claim_id DESC""")


def get_claim(claim_id):
    return _one("""SELECT c.*, l.item_name AS lost_name, l.reporter_name, l.reporter_contact,
                          l.description AS lost_desc,
                          f.item_name AS found_name, f.founder_name, f.location_found,
                          f.date_found, f.description AS found_desc
                   FROM claims c
                   LEFT JOIN lost_items l ON l.lost_id = c.lost_id
                   LEFT JOIN found_items f ON f.found_id = c.found_id
                   WHERE c.claim_id=?""", (claim_id,))


# ---------------------------------------------------------------
# ANALYTICS
# ---------------------------------------------------------------
def get_analytics(user_id=None):
    base = get_stats()
    total = base["total_lost"] + base["total_found"]
    claimed = base["lost_claimed"] + base["found_claimed"]
    cats = _rows("""SELECT category, SUM(l) AS lost, SUM(f) AS found FROM (
                      SELECT COALESCE(NULLIF(category,''),'Other') AS category, 1 AS l, 0 AS f FROM lost_items
                      UNION ALL
                      SELECT COALESCE(NULLIF(category,''),'Other'), 0, 1 FROM found_items)
                    GROUP BY category ORDER BY (lost+found) DESC""")
    hotspots = _rows("""SELECT location, COUNT(*) AS n FROM (
                          SELECT location_lost AS location FROM lost_items
                          UNION ALL SELECT location_found FROM found_items)
                        WHERE location IS NOT NULL AND location<>'' GROUP BY location
                        ORDER BY n DESC LIMIT 5""")
    trend = _rows("""SELECT day, SUM(l) AS lost, SUM(f) AS found FROM (
                       SELECT date(date_reported) AS day, 1 AS l, 0 AS f FROM lost_items
                       UNION ALL SELECT date(date_reported), 0, 1 FROM found_items)
                     WHERE day >= date('now','-13 days') GROUP BY day ORDER BY day""")
    stale = (_one("SELECT COUNT(*) AS n FROM lost_items WHERE status='Pending' "
                  "AND date(date_reported) < date('now', ?)", (f"-{STALE_DAYS} days",))["n"]
             + _one("SELECT COUNT(*) AS n FROM found_items WHERE status='Pending' "
                    "AND date(date_reported) < date('now', ?)", (f"-{STALE_DAYS} days",))["n"])
    base.update(
        recovery_rate=round(100 * (base["lost_claimed"]) / base["total_lost"]) if base["total_lost"] else 0,
        total=total, claimed=claimed, categories=cats, hotspots=hotspots, trend=trend,
        stale=stale, users=_one("SELECT COUNT(*) AS n FROM users")["n"],
        pending_claims=_one("SELECT COUNT(*) AS n FROM claim_requests WHERE status='Pending'")["n"])
    return base
