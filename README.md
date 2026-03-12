# Business Manager (Django + React)

Cleaned stack:
- Backend: Django + DRF (`backend/`)
- Frontend: React + Vite (`frontend/`)
- DB: PostgreSQL (via `DATABASE_URL`)

## Run Backend

```bash
cd backend
..\venv\Scripts\python.exe manage.py migrate
..\venv\Scripts\python.exe manage.py runserver
```

Backend URL: `http://127.0.0.1:8000`

## Run Frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend URL: `http://127.0.0.1:5173`

## API Base

Frontend calls Django APIs through Axios:
- `GET /api/products/`
- `GET /api/customers/`
- `POST /api/sales/`
- `GET /api/invoices/`
- `GET /api/expenses/`
- `GET /api/reports/`

## Cleanup

`cleanup_project.py` removes Flask artifacts:
- `run.py`
- `app/`
- `templates/`
- `flask_migrate/`
- `instance/`
- `migrations/`
