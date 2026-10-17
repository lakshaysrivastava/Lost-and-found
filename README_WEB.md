# Lost & Found Management System — Web version (Flask + SQLite)

## Run
```
python -m pip install -r requirements.txt
python web_app.py
```
Open http://127.0.0.1:5000 — admin login: `admin` / `admin123` (choose "Administrator"; change it under *My account*).
Students click **Create a student account** on the login page.
The old Tkinter app (`desktop_app.py`) still works with the same database. Your existing data is kept; new tables/columns are added automatically on first start.

## Features
**Original:** admin login, report lost/found, search, auto-match, claim/return, dashboard, delete/status update.

**New**
1. **Two roles** — Administrator and Student/Staff (self-registration).
2. **Password hashing** (werkzeug) — old plain-text admin password is upgraded automatically.
3. **Security** — CSRF tokens on every form, login lockout after 5 failures (5 min), upload type/size checks, ownership checks (students can only edit/delete their own reports), auto-generated secret key.
4. **Smart match scoring (0–100%)** — name similarity (difflib), category, location, date gap, shared description keywords; each match shows *why* it scored that way.
5. **Claim-request workflow** — student submits proof of ownership → admin approves/rejects with remarks → item returned. Other pending requests for the same item are auto-rejected.
6. **Printable return receipt** for each completed return.
7. **Photo upload** for items.
8. **Edit** any report (admin or owner), full input validation (dates, phone/email, lengths).
9. **Advanced search & filters** — keyword, category, status, date range, sorting, **pagination**.
10. **Dashboard analytics** — recovery rate, reports by category, 14-day trend, hotspot locations, items pending 30+ days (no external chart library needed).
11. **In-app notifications** — alerts on strong matches (≥60%), claim requests, decisions and returns.
12. **Activity / audit log** of logins, reports, edits, deletes, claims, exports.
13. **CSV export** of lost, found and claims.
14. **Privacy** — students cannot see contact details of other people's reports.
15. **User management page** (admin) and **change password**.

## Files
| File | Purpose |
|---|---|
| `db.py` | all SQL / business logic (migrations, scoring, claims, analytics) |
| `web_app.py` | Flask routes, validation, security |
| `templates/`, `static/style.css` | HTML pages and styling |
| `desktop_app.py` | original Tkinter GUI (unchanged) |

## Viva talking points
- **Architecture:** 3 layers — templates (presentation) → `web_app.py` (controller/validation) → `db.py` (data access).
- **Matching algorithm:** weighted scoring — name 35, category 20, place 15, date proximity 15, keywords 15 (capped at 100).
- **Normalisation:** separate lost/found tables, `claims` link table, `claim_requests` for the approval workflow, `users`, `notifications`, `activity_log`.
- **Security:** hashed passwords, CSRF, parameterised SQL (no SQL injection), role checks, upload validation.
- **Future work:** email/SMS alerts, QR-coded item tags, deployment with gunicorn + MySQL.

## Quick start (Windows)
Double-click **start.bat**. It installs Flask if needed, starts the server and opens the website in your browser automatically. Keep the black window open while using the app; close it to stop.

## Deploying on Render
- Build command: `pip install -r requirements.txt`
- Start command: `gunicorn web_app:app`
- Environment variable: `SECRET_KEY` = any long random string
- Note: on Render's free plan the disk is temporary, so `lost_found.db` and uploaded photos reset on every redeploy/restart.
