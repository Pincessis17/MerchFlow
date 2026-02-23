# app/config.py
import os
import secrets
from typing import Set
from dotenv import load_dotenv

load_dotenv()

def _env_flag(name: str, default: bool = False) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _app_env() -> str:
    return (os.environ.get("APP_ENV") or os.environ.get("FLASK_ENV") or "development").strip().lower()


def _admin_email_set() -> Set[str]:
    emails = set()

    primary = (os.environ.get("PLATFORM_ADMIN_EMAIL") or "").strip().lower()
    if primary:
        emails.add(primary)

    csv_value = os.environ.get("PLATFORM_ADMIN_EMAILS", "")
    for item in csv_value.split(","):
        email = item.strip().lower()
        if email:
            emails.add(email)

    return emails

class Config:
    APP_ENV = _app_env()
    IS_PRODUCTION = APP_ENV in {"production", "prod"}

    # Local developer convenience fallback (production must set SECRET_KEY).
    SECRET_KEY = os.environ.get("SECRET_KEY") or (
        secrets.token_hex(32) if not IS_PRODUCTION else None
    )

    # Always read DB from environment when present.
    # SQLite fallback is for local development only.
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL", "sqlite:///pharmacy.db")

    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = _env_flag(
        "SESSION_COOKIE_SECURE",
        default=IS_PRODUCTION,
    )

    PLATFORM_ADMIN_EMAILS = _admin_email_set()
    PLATFORM_ELEVATED_AUTH_WINDOW_SECONDS = int(
        os.environ.get("PLATFORM_ELEVATED_AUTH_WINDOW_SECONDS", "900")
    )

    # Analytics (GA4 Measurement Protocol)
    GA4_MEASUREMENT_ID = os.environ.get("GA4_MEASUREMENT_ID")
    GA4_API_SECRET = os.environ.get("GA4_API_SECRET")
    GA4_ENVIRONMENT = os.environ.get("GA4_ENVIRONMENT") or APP_ENV

    # Optional SMTP configuration for notification emails
    SMTP_HOST = os.environ.get("SMTP_HOST")
    SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
    SMTP_USERNAME = os.environ.get("SMTP_USERNAME")
    SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD")
    SMTP_FROM_EMAIL = os.environ.get("SMTP_FROM_EMAIL")
    SMTP_USE_TLS = _env_flag("SMTP_USE_TLS", default=True)

    INVOICE_LOGO_UPLOAD_DIR = os.environ.get(
        "INVOICE_LOGO_UPLOAD_DIR",
        "app/static/uploads/invoice_logos",
    )
    INVENTORY_IMPORT_MAX_FILE_MB = int(os.environ.get("INVENTORY_IMPORT_MAX_FILE_MB", "20"))
    INVENTORY_IMPORT_MAX_ROWS = int(os.environ.get("INVENTORY_IMPORT_MAX_ROWS", "200000"))
    INVENTORY_IMPORT_CHUNK_SIZE = int(os.environ.get("INVENTORY_IMPORT_CHUNK_SIZE", "1000"))

    @classmethod
    def validate(cls):
        missing = []
        if cls.IS_PRODUCTION:
            if not os.environ.get("SECRET_KEY"):
                missing.append("SECRET_KEY")
            if not os.environ.get("DATABASE_URL"):
                missing.append("DATABASE_URL")
        if missing:
            missing_csv = ", ".join(missing)
            raise RuntimeError(
                f"Missing required environment variables for production: {missing_csv}"
            )
