# MerchFlow

Environment-variable based setup for local and production.

## 1) Local setup (development)

1. Create and activate a virtual environment.
2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Copy example env file:

```bash
cp .env.example .env
```

4. Edit `.env` and keep:
   - `APP_ENV=development`
   - `FLASK_DEBUG=1`
   - `DATABASE_URL=sqlite:///pharmacy.db` (or Postgres URL if you want)
   - `SECRET_KEY=<random value>`
   - `PLATFORM_ADMIN_EMAILS=<your email>`
   - `SESSION_COOKIE_SECURE=0` (local HTTP)

5. Run database migrations:

```bash
flask db upgrade
```

6. Start app:

```bash
python run.py
```

## 2) Production setup (later)

Set these environment variables in your deployment platform (not in git):

- `APP_ENV=production`
- `FLASK_DEBUG=0`
- `DATABASE_URL=postgresql+psycopg://...`
- `SECRET_KEY=<strong random secret>`
- `PLATFORM_ADMIN_EMAILS=<comma-separated admin emails>`
- `SESSION_COOKIE_SECURE=1`

The app will fail to start in production if `SECRET_KEY` or `DATABASE_URL` is missing.

## 3) Security rules for secrets

- Never commit `.env` (already gitignored).
- Rotate secrets if they were ever exposed.
- Prefer HTTPS in production.
- Keep database credentials only in environment variables (or a secrets manager later).