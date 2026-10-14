# Deploying to Railway (app + MySQL)

Railway's menus and variable names change from time to time. If a step doesn't match what you
see, check https://docs.railway.com.

## 1. Put the project on GitHub
The repo root must contain `app.py`, `requirements.txt`, `Procfile`, `templates/` and `static/`
(including `static/img/` with the layout, menu and brand images). `.env` is excluded by
`.gitignore`, so your local passwords are not uploaded.

## 2. Create the Railway project
1. New Project -> Deploy from GitHub repo -> pick this repo.
2. In the same project: New -> Database -> Add MySQL.

## 3. Set variables on the app service (not the MySQL service)
| Variable | Value |
|---|---|
| `SECRET_KEY` | a long random string (e.g. run `python -c "import secrets; print(secrets.token_hex(32))"`) |
| `DATABASE_URL` | `${{MySQL.MYSQL_URL}}` (reference variable; replace `MySQL` with your database service's name) |
| `TZ` | `America/New_York` (otherwise the server uses UTC and "today" and past time slots are wrong) |
| `ADMIN_USERNAME`, `ADMIN_EMAIL`, `ADMIN_PASSWORD` | your first admin login |

The app converts `mysql://` to `mysql+pymysql://` automatically.
The app refuses to start on Railway if `SECRET_KEY` is missing.

## 4. Deploy
On each deploy the start command (`Procfile`) runs `flask --app app init-db`, which creates the
tables if they don't exist, seeds the default weekly hours, and creates your first admin from the
`ADMIN_*` variables while no admin exists. Then it starts the site with gunicorn.

If Railway does not pick up the `Procfile`, set the start command in Settings -> Deploy to:

    flask --app app init-db && gunicorn app:app --bind 0.0.0.0:$PORT --workers 2

## 5. Get a public address
Settings -> Networking -> Generate Domain. Share that https address. Admin login is at `/admin/login`.

## 6. After the first login
- Delete the `ADMIN_PASSWORD` variable (the account is already created).
- Add more admins from the Manage Admins page.
:)
- Turn on database backups for the MySQL service.

## Changing the database later
`init-db` only creates missing tables; it does not alter existing ones. When you add a column to a
model, run the matching `ALTER TABLE` on the Railway database (for example from MySQL Workbench using
the database's public connection details).
