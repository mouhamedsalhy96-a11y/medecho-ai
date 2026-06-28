# MedEcho AI

MedEcho AI is an educational healthcare simulation platform for OSCE-style consultation practice. It helps healthcare learners and professionals practise text-based patient conversations, timed voice consultations, investigation requests, structured feedback and revision history in one workspace.

> **Important:** MedEcho AI is for educational simulation only. It is not a medical device and must not be used for diagnosis, treatment decisions, prescribing, triage, emergencies or real patient care.

## Features

- Account registration with email verification
- Password reset and login flow
- Role/profession-based profile setup
- AI-generated fictional clinical cases
- Simulated patient chat for history-taking practice
- Investigation ordering with educational reports
- Timed Live Consultation mode with voice interaction
- Consultation transcript capture
- Structured feedback and scoring
- Unified practice history
- Stripe subscription and credit-based billing
- Admin cost dashboard for usage monitoring
- Privacy, terms, safety and contact pages

## Tech Stack

- **Backend:** Python, Django
- **Frontend:** Django Templates, Tailwind CSS, JavaScript
- **AI:** OpenAI text and realtime voice APIs
- **Payments:** Stripe Checkout, Stripe Billing, Stripe Webhooks
- **Email:** Django email system with SMTP/Resend support
- **Database:** SQLite for local development; PostgreSQL recommended for production
- **Deployment:** Vercel-compatible Django configuration, with external database and environment variables

## Local Development

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Open:

```text
http://127.0.0.1:8000/
```

## Environment Variables

Create a local `.env` file based on `.env.production.example` and fill in your values.

Required production values include:

```text
SECRET_KEY
DEBUG
ALLOWED_HOSTS
CSRF_TRUSTED_ORIGINS
DATABASE_URL
OPENAI_API_KEY
STRIPE_SECRET_KEY
STRIPE_WEBHOOK_SECRET
STRIPE_*_PRICE_ID
RESEND_API_KEY
DEFAULT_FROM_EMAIL
```

## Stripe Webhook

Production webhook endpoint:

```text
https://YOUR_DOMAIN.com/billing/webhook/stripe/
```

Local Stripe CLI forwarding:

```bash
stripe listen --forward-to http://127.0.0.1:8000/billing/webhook/stripe/
```

Copy the `whsec_...` value into:

```text
STRIPE_WEBHOOK_SECRET
```

## Production Notes

- Use PostgreSQL in production.
- Do not use SQLite for production payments or user accounts.
- Set `DEBUG=False`.
- Use HTTPS domain names in `CSRF_TRUSTED_ORIGINS`.
- Store secrets only in the deployment provider’s environment variable manager.
- Do not commit `.env`, database files, uploaded media, Stripe secrets or API keys.
- For Vercel, use an external database and external storage for uploaded/generated media if needed.

## License

Private project 
