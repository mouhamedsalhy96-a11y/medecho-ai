# Phase 9D Deployment Safety Checklist

## Clinical simulation safety

- Hidden diagnosis should not be visible to normal users.
- Hidden diagnosis may be visible only to staff users or through Django admin.
- Every case, image, feedback page and PDF should make clear that MedEcho AI is educational simulation only.
- AI-generated investigation images must remain labelled as educational only and not real clinical imaging.

## Django production safety

Before production deployment:

```powershell
python manage.py check --deploy
```

Recommended production checks:

- `DEBUG=False`
- `SECRET_KEY` loaded from environment and not committed
- `ALLOWED_HOSTS` set to real production domains
- `CSRF_TRUSTED_ORIGINS` set for HTTPS production origins if needed
- `SESSION_COOKIE_SECURE=True` when using HTTPS
- `CSRF_COOKIE_SECURE=True` when using HTTPS
- static files collected and served correctly
- media files stored/served safely
- production WSGI/ASGI server instead of `runserver`

## Stripe safety

- Use test keys locally and live keys only in production.
- `STRIPE_WEBHOOK_SECRET` must match the exact webhook endpoint secret.
- Stripe CLI webhook secret and Stripe Dashboard webhook secret are different.
- Webhook endpoint must remain CSRF-exempt but signature-verified.
- Do not grant credits from success page redirects; grant only from verified webhooks.

## API key safety

Keep these only in `.env` / hosting secrets:

- `OPENAI_API_KEY`
- `ELEVENLABS_API_KEY`
- `REPLICATE_API_TOKEN`
- `STRIPE_SECRET_KEY`
- `STRIPE_WEBHOOK_SECRET`

Do not commit `.env` to Git.

## Pre-deploy smoke test

- Register/login works.
- Dashboard loads.
- Normal Practice case generation works.
- Patient chat works.
- Investigations work.
- Feedback page works.
- PDF download works.
- Real Consultation setup/start/transcription loop works.
- Stripe Checkout works.
- Stripe webhook grants subscription/PAYG/Real Consultation credits.
- Custom 404/500/403 templates exist.
