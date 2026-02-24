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
- `PLATFORM_ELEVATED_AUTH_WINDOW_SECONDS=900`
- `GA4_MEASUREMENT_ID` and `GA4_API_SECRET` (optional)
- SMTP vars (`SMTP_HOST`, `SMTP_USERNAME`, etc.) for email alerts (optional)

The app will fail to start in production if `SECRET_KEY` or `DATABASE_URL` is missing.

## 3) Security rules for secrets

- Never commit `.env` (already gitignored).
- Rotate secrets if they were ever exposed.
- Prefer HTTPS in production.
- Keep database credentials only in environment variables (or a secrets manager later).

## 4) SaaS architecture modules

- **Platform owner console**: `/platform`
  - Elevated authentication required (`/platform/elevate`)
  - Tenant subscription analytics (MRR, churn, conversion)
  - Plan management
  - Tenant suspend/activate/cancel controls
  - Real-time platform notifications
  - Platform audit logs and CSV exports

- **Tenant invoice module**: `/invoices`
  - Create invoice with line items
  - Tax + discount calculation
  - Draft / paid status
  - PDF export and print-friendly view
  - Invoice branding settings (logo, color, footer, numbering)

## 5) Self-service tenant data onboarding (CSV import)

Tenant admins/managers can import inventory without platform-owner intervention:

- Go to **Inventory** and use **Bulk Import (CSV)**.
- Upload a CSV with at least:
  - `sku` (or `code`)
  - `name`
- Optional columns:
  - `stock_qty`, `unit`, `category`, `expiry_date`, `cost_price`, `selling_price`
- Behavior:
  - If SKU/code exists in the same company, it is **updated**
  - If SKU/code is new, it is **created**
  - Invalid rows are skipped with summary feedback
- Import is tenant-scoped (`company_id`) and processed in batches for large files.

You can tune limits with:

- `INVENTORY_IMPORT_MAX_FILE_MB`
- `INVENTORY_IMPORT_MAX_ROWS`
- `INVENTORY_IMPORT_CHUNK_SIZE`

## 6) Self-service signup and login

- New subscriber companies can create their own tenant account at:
  - `/auth/register` (also available at `/auth/signup`)
- Signup creates:
  - a new `Company` (tenant)
  - the first `User` in that company with role `admin`
- Returning users simply log in via `/auth/login`.
- Company admins can add more staff accounts from:
  - `/admin/team`
  - Each staff member gets their own login and role.

## 7) Finance permissions, account management, and invoice/sales linkage

- **Finance access policy**
  - Company `admin` always has finance access.
  - Other users require explicit finance grant by company admin.
  - Finance grants are managed from `/admin/team`.

- **Team management**
  - Company admins can:
    - create staff accounts
    - grant/revoke finance access
    - delete user accounts (with safeguards)

- **Invoice improvements**
  - Invoices can be searched by:
    - customer/invoice text (`name`, `email`, `invoice number`)
    - `issue_date`
  - Payment method is captured on invoices.
  - Line items support dynamic add/remove in create form.
  - Sales can be linked to invoices via "Create Invoice" from the sales table.

- **Product search**
  - Sales and Inventory pages support product search by name/code/category.