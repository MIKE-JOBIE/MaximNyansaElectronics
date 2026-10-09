# Maxim Nyansa Electronics — Production Readiness

## What this release hardens
- Transactional training-capacity locking and a database-enforced active-application uniqueness rule.
- Transactional order cancellation with row locks before stock restoration.
- Payment callbacks/webhooks cannot resurrect cancelled orders.
- AuditLog database trail for important administrative changes.
- Cloudinary failure is fail-closed when configured; the app no longer silently falls back to ephemeral Render storage.
- Admin list pagination (25 records/page) and trainee application pagination.
- Logout changed to POST + CSRF.
- Accessibility labels improved where form fields are rendered directly.
- Removed stray payment fields from VideoTestimonial and added a corrective migration.
- Added `flask --app wsgi release-stale-orders --minutes 60` for abandoned unpaid order reservations.

## Deployment requirements
1. Use PostgreSQL (Neon is suitable).
2. Set a random `SECRET_KEY` of at least 32 characters.
3. Set `FLASK_ENV=production`, `SITE_URL`, and `ALLOWED_HOSTS`.
4. Configure Cloudinary (or another persistent object-storage integration) for production uploads. If Cloudinary is configured and unavailable, uploads fail safely instead of being saved to Render's ephemeral disk.
5. Configure Paystack currency and keys only if online payments are enabled.
6. Run `flask db upgrade` before starting the web service.
7. For Render Free, keep the initial Gunicorn footprint conservative and monitor memory/latency.
8. When running more than one app instance, move Flask-Limiter from `memory://` to shared Redis/Valkey.
9. Schedule `release-stale-orders` when shop volume makes abandoned payment reservations material.

## Verification
The packaged project includes the complete source, migrations, tests, deployment configuration, examples, and documentation. The audit environment cannot execute the bundled Windows virtual environment on Linux, so dependency-backed pytest execution must be performed after installing `requirements.txt` in the deployment/staging environment.

## Still deliberately infrastructure-dependent
The application code is now prepared for the next scaling stage, but no free-tier web host can guarantee indefinite heavy traffic. At higher traffic, use persistent object storage/CDN, shared Redis/Valkey for rate limiting, a background worker for large email batches, centralized logs/monitoring, and a larger PostgreSQL plan.
