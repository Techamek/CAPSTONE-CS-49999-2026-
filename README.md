# Event Calendar (Flask + MySQL)

A small app with two sides:

- **Public page (`/`)** — anyone can submit an event (title, date/time, location, description, their name/email). Submissions start as **pending**.
- **Admin area (`/admin/...`)** — requires login. Admins review pending submissions and approve or reject them. Only **approved** events show up on the calendar. Multiple admin accounts are supported, and logged-in admins can create more from the "Manage Admins" page.

## 1. Requirements

- Python 3.10+
- A running MySQL server (local or hosted)

## 2. Setup

```bash
cd calendar_app
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

Create your MySQL database (skip if you'll let the app create tables for you):

```sql
CREATE DATABASE calendar_app CHARACTER SET utf8mb4;
```

Copy the env template and fill in your real values:

```bash
cp .env.example .env
```

Edit `.env`:
```
SECRET_KEY=<generate one, e.g. python -c "import secrets; print(secrets.token_hex(32))">
DB_USER=root
DB_PASSWORD=your-mysql-password
DB_HOST=localhost
DB_NAME=calendar_app
```

## 3. Create the tables and your first admin

```bash
flask init-db
flask create-admin
```

`create-admin` will prompt you for a username, email, and password interactively — nothing is passed on the command line or stored in shell history.

## 4. Run it

```bash
flask run
```

- Public submission form: http://127.0.0.1:5000/
- Admin login: http://127.0.0.1:5000/admin/login
- Admin calendar: http://127.0.0.1:5000/admin/dashboard (after login)
- Pending approvals: http://127.0.0.1:5000/admin/pending
- Manage admins: http://127.0.0.1:5000/admin/manage

## How access control works

- All `/admin/*` routes are protected with Flask-Login's `@login_required`. Unauthenticated visitors are redirected to the login page.
- The calendar's data feed (`/admin/api/events`) is also behind `@login_required` and only ever returns events with `status='approved'` — so pending/rejected submissions are never exposed, even via direct API access.
- Passwords are hashed with Werkzeug's `generate_password_hash` (PBKDF2) — plaintext passwords are never stored.
- Forms use CSRF protection (Flask-WTF).

## Notes / things to harden before deploying publicly

- Set `SECRET_KEY` to a long random value in production (never the placeholder).
- Run behind HTTPS, and set `SESSION_COOKIE_SECURE = True` in `app.config` once you're on HTTPS.
- Consider rate-limiting the public submission form to prevent spam (e.g. Flask-Limiter) and/or adding a CAPTCHA.
- Consider email/username verification before allowing new admin accounts to be created, since anyone with an existing admin login can currently create more.
- Back up your MySQL database regularly.

## Project structure

```
calendar_app/
├── app.py                  # Routes, models, forms
├── requirements.txt
├── schema.sql               # Reference SQL (optional — flask init-db does this for you)
├── .env.example
├── templates/
│   ├── base.html
│   ├── submit.html          # Public submission form
│   ├── login.html
│   ├── dashboard.html       # Admin calendar (FullCalendar.js)
│   ├── pending.html         # Approve/reject queue
│   └── manage_admins.html
└── static/
    └── css/style.css
```
