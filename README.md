# Event Calendar (Flask + MySQL)

A small app with two sides:

- **Public page (`/`)** — anyone can submit an event: title, type of event, guest count, date/start time/duration, location, a full menu selection, table arrangement, and their contact info. A live price estimate is shown as the form is filled out. Submissions start as **pending**.
- **Admin area (`/admin/...`)** — requires login. Admins review pending submissions (seeing the full menu, guest count, table layout, and price/deposit) and approve or reject them. Only **approved** events show up on the calendar. Multiple admin accounts are supported, and logged-in admins can create more from the "Manage Admins" page.

## What's new in this version

- **Event details prompt**: type of event, number of guests (capped at the venue's 50-guest capacity), date, start time, and duration.
- **Menu selection**: choose 2 savory and 2 sweet items (from Coco Café's current menu), plus optional a la carte enhancements (crepe/espresso stations, décor, fruit tray, salad, vegan/GF).
- **Table arrangement designer**: a drag-and-drop floor plan on the submission form. Add round, rectangular, or high-top tables from a palette and drag them into position; a running seat count compares against the guest count. The layout is saved as JSON and shown (read-only) to admins in Pending Approvals and on the calendar's event detail popup.
- **Live price tracking**: pricing follows Coco Café's Special Events rate sheet (`$175/hr` space rental, `+$50/hr` once guest count exceeds 35, `$17.50/person` menu, a la carte enhancement pricing), with Medina County, OH sales tax (6.75%) and a 20% gratuity added, and a deposit equal to the space rental fee. The estimate updates live on the form (via `/api/price-estimate`) and the final numbers are stored with the event for admins to see.

> Pricing constants live at the top of `app.py` (`SPACE_RENTAL_PER_HOUR`, `MENU_PRICE_PER_PERSON`, `ENHANCEMENTS`, `SALES_TAX_RATE`, etc.) — update them there if the venue's rate sheet changes. These are estimates only; the venue confirms the final invoice.

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

If you're upgrading an existing database rather than starting fresh, `flask init-db` only creates tables that don't already exist — you'll need to add the new `events` columns yourself (see `schema.sql` for the full column list) or drop and recreate the `events` table.

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
- The `/api/price-estimate` endpoint is public (it powers the live estimate on the public submission form) and only echoes back a computed price for the numbers it's given — it doesn't read or write any event data.
- Passwords are hashed with Werkzeug's `generate_password_hash` (PBKDF2) — plaintext passwords are never stored.
- Forms use CSRF protection (Flask-WTF).

## Notes / things to harden before deploying publicly

- Set `SECRET_KEY` to a long random value in production (never the placeholder).
- Run behind HTTPS, and set `SESSION_COOKIE_SECURE = True` in `app.config` once you're on HTTPS.
- Consider rate-limiting the public submission form to prevent spam (e.g. Flask-Limiter) and/or adding a CAPTCHA.
- Consider email/username verification before allowing new admin accounts to be created, since anyone with an existing admin login can currently create more.
- Back up your MySQL database regularly.
- Double-check the pricing constants in `app.py` against the venue's current rate sheet before relying on the estimate for real bookings.

## Project structure

```
calendar_app/
├── app.py                       # Routes, models, forms, pricing engine
├── requirements.txt
├── schema.sql                   # Reference SQL (optional — flask init-db does this for you)
├── .env.example
├── templates/
│   ├── base.html
│   ├── submit.html              # Public submission form (event details, menu, table designer, price)
│   ├── login.html
│   ├── dashboard.html           # Admin calendar (FullCalendar.js) with full event-detail modal
│   ├── pending.html             # Approve/reject queue with menu, table layout, price
│   └── manage_admins.html
└── static/
    ├── css/style.css
    └── js/submit.js             # Table layout designer + live price estimator
```
