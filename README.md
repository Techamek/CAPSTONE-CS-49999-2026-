# Event Calendar (Flask + MySQL)

- **Public page (`/`)** — anyone can request an event: title, type, guest count, duration, an *available* date and start time, a table layout picked from images, and contact info. There is no pricing anywhere on the public side. The menu is a link to a menu image (`static/img/menu.png`, cropped to food/beverage options only). Submissions start as **pending**.
- **Admin area (`/admin/...`)** — requires login. Approve/reject pending requests, view the approved calendar, manage admins, and control **Availability**.

## Availability (admin → Availability)

- **Weekly hours**: per weekday, open/closed and from/until. Guests can start on any 30-minute mark, provided the whole event ends by closing time.
- **Specific dates**: close a single day or give it custom hours. Overrides beat weekly hours (so you can also open a normally-closed day).
- **Approved events block their time slot automatically**, and an admin can't approve a request that overlaps an already-approved event.
- The public form only offers dates/times that are open for the chosen duration; the server re-checks on submit.
- `flask init-db` seeds Mon–Fri 9:00–5:00 (Sat/Sun closed). Change it on the Availability page.

## Table layouts

Guests up to 35 choose from layouts A–D (`static/img/layout35-*.png`); 36–50 guests choose from A–B (`layout50-*.png`). Edit `LAYOUTS` at the top of `app.py` to change seat counts or swap images.

## Pricing (admin only)

Admins still see a base-package estimate (space rental + per-person menu + tax + 20% gratuity, plus deposit) on Pending Approvals and the calendar popup. Constants are in `app.py`. Add-ons (crepe/espresso/décor etc.) are not included since guests no longer select them.

## Setup

```bash
python -m venv venv && source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env    # SECRET_KEY, DB_USER, DB_PASSWORD, DB_HOST, DB_NAME
flask init-db
flask create-admin
flask run
```

Upgrading an existing database: see the note at the bottom of `schema.sql`.

## Notes before deploying

- Set a real `SECRET_KEY`; run behind HTTPS and set `SESSION_COOKIE_SECURE = True`.
- Consider rate-limiting/CAPTCHA on the public form.
- `/api/availability/*` is public and read-only; it exposes only which dates/times are open, not event details.
