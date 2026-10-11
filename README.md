# Maxim Nyansa Electronics

Flask application for the Maxim Nyansa Electronics training programme, resource library, donor pages, e-commerce, payments and administration.

## Development workflow

Use **GitHub as the source of truth**, develop locally in VS Code, test against a local database, then push reviewed commits. The live Render service auto-deploys from `main`; this hardening branch is intentionally separate so it does not change production while being tested.

### Requirements
- Python 3.11
- Git
- VS Code (recommended)
- A local SQLite database for development; PostgreSQL/Neon for production

### Windows PowerShell setup

```powershell
git clone https://github.com/MIKE-JOBIE/MaximNyansaElectronics.git
cd MaximNyansaElectronics
git checkout codex/production-hardening
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt -r requirements-dev.txt
Copy-Item .env.example .env
```

Edit `.env` for local development. Do not put production credentials in this file or commit it. The `.env` file and local database files are ignored by Git.

Initialize or update the local database:

```powershell
$env:FLASK_APP = "wsgi:app"
flask db upgrade
flask seed
```

Start the application:

```powershell
python wsgi.py
```

Open http://127.0.0.1:5000. The local database uses SQLite and should contain only development/test data. Do not point local development at the production Neon database.

### Run checks

```powershell
pytest -q
```

A green local test suite is necessary but not sufficient for release. Before merging, run the GitHub Actions tests and perform browser-based smoke tests for registration/login, admin permissions, programme applications, uploads, cart/checkout, payment verification, donations, password reset, and mobile layouts.

## Production configuration

Render uses the `render.yaml` Blueprint. The current live service is `maxim-nyansa-electronics` at https://maxim-nyansa-electronics.onrender.com. Never change or reuse the separate MikeShop service for this app.

Required settings (values are configured in Render's environment UI; never commit secrets):

- `SECRET_KEY`: unique random value of at least 32 characters
- `DATABASE_URL`: Neon/PostgreSQL connection string, using the pooled URL only if it supports the app's connection pattern
- `ADMIN_PASSWORD`: strong initial password; changing this variable does not reset an existing administrator's password
- `CLOUDINARY_CLOUD_NAME`, `CLOUDINARY_API_KEY`, `CLOUDINARY_API_SECRET`: durable media storage. Production uploads now fail closed when Cloudinary is absent instead of writing to Render's ephemeral disk.
- `MAIL_SERVER`, `MAIL_PORT`, `MAIL_USE_SSL`, `MAIL_USE_TLS`, `MAIL_USERNAME`, `MAIL_PASSWORD`, `MAIL_DEFAULT_SENDER`: for port 465, use SSL=true and TLS=false.
- `PAYSTACK_SECRET_KEY`, `PAYSTACK_PUBLIC_KEY`, `PAYSTACK_CURRENCY`: payment settings. Set currency to the actual currency enabled on the Paystack account before accepting live payments. An unset currency causes production payment matching to fail closed.
- `RATELIMIT_STORAGE_URI`: a shared Redis/Valkey URL is recommended for distributed rate limits. Memory storage is per-process and resets on restart.
- `MAINTENANCE_SECRET`: unique random value of at least 32 characters used to authorize scheduled maintenance requests.
- `SITE_URL` and `ALLOWED_HOSTS`: must match the deployed HTTPS hostname.

Keep `PAYSTACK_TEST_MODE=true` until a controlled test transaction is verified. Do not enable live payments until amount, currency, reference, callback, webhook, refund/manual-review procedures, and order inventory behavior have been tested end-to-end.

## Creating a local production database backup

Install PostgreSQL client tools so `pg_dump` and `pg_restore` are available in PowerShell. Set `$env:DATABASE_URL` to the **direct** PostgreSQL/Neon connection URL for the database you intend to back up, then run:

```powershell
$env:DATABASE_URL = Read-Host "Paste the direct PostgreSQL connection URL"
.\scripts\backup-postgres.ps1
Remove-Item Env:DATABASE_URL
```

The script asks for explicit confirmation, stores the dump under the ignored local `backups/` folder, prints a SHA-256 checksum, and checks that the archive can be listed. It never commits or uploads the backup. A readable archive is not proof of recoverability: restore it into a separate test database and verify row counts and application behavior before merging a production schema change.

## Database and deployment safety

- Normal builds run migrations and idempotent seed logic only.
- A content backup is **not** automatically imported during deployment. Do not use `flask backup-import` as a routine deploy step.
- Take a fresh database backup before merging any schema change. Verify restore to a separate test database before calling the backup recoverable.
- Migrations are forward-only in production unless a tested rollback plan explicitly says otherwise. Never drop production tables to fix a migration.
- The `/health` endpoint checks database connectivity and is used for the Render health check.
- Stale unpaid order cleanup and email queue processing are protected by `MAINTENANCE_SECRET`. The GitHub Actions workflow runs every 15 minutes but safely skips maintenance until its secrets are configured. Add repository secrets `MNE_SITE_URL` and `MNE_MAINTENANCE_SECRET`, matching the deployed site URL and Render's maintenance secret. Verify the endpoints manually before relying on automated cleanup.
- The email queue stores reset links and recipient details in the database. Restrict database access and avoid logging email bodies or reset URLs.

## Current hardening behavior

- Order stock reservations and releases are recorded in the inventory ledger.
- Successful Paystack callbacks/webhooks are verified against Paystack's transaction API, checked against amount/reference/currency, and recorded idempotently by provider reference.
- Late successful payments after an order's reservation has expired are marked for manual review rather than silently confirming an order without reserved stock.
- Email jobs are persisted in PostgreSQL and retried with bounded backoff. Delivery is at-least-once, so a rare process crash after SMTP acceptance may cause a duplicate message.
- Local upload fallback remains available in development. Production requires Cloudinary to avoid losing uploads on free-tier restarts.
- The app does not yet implement MFA/TOTP. Use strong unique administrator credentials and restrict admin accounts until MFA is implemented.

## Free-tier expectations

Render Free can sleep, has limited memory/CPU, and uses an ephemeral filesystem. Neon/other service limits, database connection counts, email quotas, and Redis quotas also apply. This setup is not an unlimited-traffic guarantee. Measure latency, error rate, database connections, memory, and queue backlog before increasing traffic or workers.
