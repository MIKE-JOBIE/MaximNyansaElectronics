# Maxim Nyansa Electronics — Final Deployment Checklist

## Required production services
- PostgreSQL (Neon recommended for the current stage)
- Cloudinary (durable media storage)
- Redis/Valkey (shared rate-limit storage)
- HTTPS email API such as Resend
- Render web service
- GitHub Actions scheduler using the included maintenance workflow

## Required secrets/environment variables
- SECRET_KEY: random, at least 32 characters
- DATABASE_URL: PostgreSQL URL
- CLOUDINARY_CLOUD_NAME / CLOUDINARY_API_KEY / CLOUDINARY_API_SECRET
- RATELIMIT_STORAGE_URI: shared Redis/Valkey URL
- RESEND_API_KEY
- MAIL_DEFAULT_SENDER: a sender/domain authorized by the email provider
- MAINTENANCE_SECRET: random, at least 32 characters
- PAYSTACK_SECRET_KEY / PAYSTACK_PUBLIC_KEY when payments are enabled
- PAYSTACK_CURRENCY matching the Paystack account currency
- SITE_URL and ALLOWED_HOSTS matching the deployed hostname
- ADMIN_PASSWORD: strong password used when seeding the admin account

## GitHub Actions secrets
Set:
- `MNE_SITE_URL` = the deployed HTTPS site URL
- `MNE_MAINTENANCE_SECRET` = the same `MAINTENANCE_SECRET` used by the application

The included workflow processes stale order reservations and durable email jobs every 15 minutes.

## Database
Run:
`flask db upgrade`

The latest migrations add:
- payment transaction ledger
- inventory transaction ledger
- durable email queue
- supporting indexes

## Important operational behavior
- Production refuses SQLite.
- Production refuses memory-only rate limiting.
- Production refuses missing Cloudinary credentials.
- Production refuses missing HTTPS email credentials.
- Production refuses a weak maintenance secret.
- Payment callbacks/webhooks lock records and are idempotent by payment reference.
- Inventory reservation and release events are ledgered.
- Abandoned unpaid orders are automatically released through the maintenance workflow.
- Email jobs survive application restarts and retry with backoff.

## Scaling
Start conservatively on a small Render instance. Increase workers/instances only after measuring memory, latency, database connections, and error rate. When running multiple instances, keep Redis/Valkey and PostgreSQL shared and use the same external Cloudinary/email services.

No application can honestly guarantee unlimited traffic or ten years of uninterrupted service. This architecture is designed to scale without replacing the core Flask application as usage grows.
