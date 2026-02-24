# MerchFlow - Agent Instructions

## Cursor Cloud specific instructions

### Overview
MerchFlow is a multi-tenant SaaS inventory management and POS web application built with Flask + SQLAlchemy + SQLite (local dev). It serves pharmacy/retail businesses with features for inventory, sales, reports, and financials.

### Running the dev server
```
python3 run.py
```
The Flask dev server starts on `http://127.0.0.1:5000` with debug/hot-reload enabled. To bind to all interfaces (needed for browser testing in cloud VMs):
```python
from app import create_app
app = create_app()
app.run(debug=True, host='0.0.0.0', port=5000)
```

### Key caveats
- **Incomplete `requirements.txt`**: The file only lists `flask`, `python-dotenv`, and `supabase`. The app also requires `flask-sqlalchemy`, `flask-migrate`, `flask-wtf`, `flask-limiter`, `reportlab`, and `werkzeug`. The update script installs all of them.
- **SESSION_COOKIE_SECURE**: Defaults to `False` via env var for local HTTP dev. Set `SESSION_COOKIE_SECURE=true` in production.
- **SQLite for local dev**: The `config.py` has a bug where `os.environ.get()` uses the Postgres connection string as the key (first arg) instead of `"DATABASE_URL"`. In practice this falls through to the SQLite default for local dev, which is fine.
- **No automated tests exist** in this codebase.
- **No linter configuration** exists in this codebase.

### Test credentials
To create a test user for login:
```python
from app import create_app, db
from app.models import User, Company
app = create_app()
with app.app_context():
    company = Company.query.first()
    user = User(email='test@merchflow.dev', name='Test User', company_id=company.id)
    user.set_password('testpass123')
    db.session.add(user)
    db.session.commit()
```

### Database
SQLite database lives at `instance/pharmacy.db`. Migrations are managed by Flask-Migrate (Alembic) in `migrations/`.
