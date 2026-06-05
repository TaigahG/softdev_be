# MyJob — Backend

FastAPI backend for the MyJob job portal. Handles candidate and employer profiles, job postings, applications, resume parsing, and Stripe membership subscriptions.

## Tech Stack

- **Framework**: FastAPI, Python 3.11+
- **Database**: PostgreSQL via Supabase (SQLAlchemy + Alembic)
- **Auth**: Supabase JWT verification
- **Storage**: Supabase Storage (resumes, profile images)
- **Payments**: Stripe (membership subscriptions)
- **AI**: Anthropic Claude (resume parsing)

## Prerequisites

- Python 3.11+
- A [Supabase](https://supabase.com) project
- A [Stripe](https://stripe.com) account
- An [Anthropic](https://console.anthropic.com) API key

## Installation

1. **Clone the repository**
   ```bash
   git clone <repo-url>
   cd softdev_be
   ```

2. **Create and activate a virtual environment**
   ```bash
   python -m venv venv

   # Windows
   venv\Scripts\activate

   # macOS / Linux
   source venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**
   ```bash
   cp .env.example .env
   ```
   Fill in all values in `.env` — see `.env.example` for descriptions.

5. **Run database migrations**
   ```bash
   alembic upgrade head
   ```

## Running

**Development**
```bash
uvicorn app.main:app --reload --port 8000
```
API runs at [http://localhost:8000](http://localhost:8000)  
Interactive docs at [http://localhost:8000/docs](http://localhost:8000/docs)

**Production**
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## Seeding

Seed employers, job postings, and candidates into the live database:

```bash
# Seed employers + job postings (150 jobs across 20 companies)
python scripts/seed_prod_employers_jobs.py

# Seed candidates (60 candidates with diverse profiles)
python scripts/seed_candidates.py
```

> Set `SEED_FORCE=1` to re-run seeding even if data already exists.

## Stripe Webhook (local development)

To test membership payments locally, forward Stripe events to your server:

```bash
stripe listen --forward-to localhost:8000/memberships/webhook
```

Copy the printed webhook signing secret into `STRIPE_WEBHOOK_SECRET` in your `.env`.
