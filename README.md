# Lost and Found Management System
**Mini Project — Python (Tkinter) + MySQL**

A desktop application that lets a college manage lost and found item
reports: students report lost items, staff/security report found
items, and the system can search across both and suggest possible
matches.

---

## Features
1. **Admin login** (default: `admin` / `admin123`)
2. **Report Lost Item** — form + live table of all lost item reports
3. **Report Found Item** — form + live table of all found item reports
4. **Search** — search lost/found items by name, category or location
5. **Auto-Match Suggestion** — suggests possible lost↔found pairs based
   on item name/category
6. **Claim/Return workflow** — mark a matched pair as "Claimed", which
   is logged in a `claims` table
7. **Dashboard** — quick counts of total/pending/claimed items
8. Delete / update status for any record

---

## Tech Stack
- **Frontend/GUI:** Python `tkinter` (built into Python, no install needed)
- **Backend/Database:** MySQL
- **Connector:** `mysql-connector-python`

---

## Project Structure
```
lost_found_project/
│── schema.sql        # Run this first to create the database & tables
│── config.py         # MySQL connection settings (edit this!)
│── db.py             # All database queries (add/search/update/delete)
│── app.py            # Tkinter GUI - the file you run
│── requirements.txt  # Python dependency
│── README.md
```

---

## Setup Instructions

### 1. Create the database
Open MySQL Workbench / MySQL command line and run:
```sql
SOURCE schema.sql;
```
(or copy-paste the contents of `schema.sql` into your MySQL client)

This creates the `lost_found_db` database with 4 tables
(`admin`, `lost_items`, `found_items`, `claims`) and inserts:
- a default admin login (`admin` / `admin123`)
- 2 sample records so the app isn't empty on first run

### 2. Install the Python dependency
```bash
pip install mysql-connector-python
```

### 3. Configure your database credentials
Open `config.py` and update the password (and host/user if different):
```python
DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "your_mysql_password",   # <-- change this
    "database": "lost_found_db"
}
```

### 4. Run the application
```bash
python app.py
```
Login with `admin` / `admin123`.

---

## How to Explain This Project (viva points)
- **Architecture:** 3-layer design — `config.py` (settings) →
  `db.py` (data access / SQL) → `app.py` (GUI / presentation).
  Keeping SQL out of the GUI file makes the code easier to read,
  reuse and debug.
- **Database design:** two independent tables (`lost_items`,
  `found_items`) so a report can be filed even before a match
  exists; a `claims` table records the *relationship* once an
  item is matched and returned — this is a simple many-to-many
  style link table.
- **Matching logic:** `find_possible_matches()` in `db.py` runs a
  JOIN between the two tables comparing item name and category so
  staff don't have to manually cross-check every report.
- **CRUD:** the project demonstrates Create (report item), Read
  (tables/search), Update (status → Claimed), Delete (remove record).

---

## Possible Extensions (mention if asked "what would you improve")
- Email/SMS notification when a match is found
- Image upload for items
- Separate student login (not just admin) to report their own items
- Export reports to PDF/Excel
