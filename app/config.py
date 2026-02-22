# app/config.py
import os
import secrets


def _env_flag(name: str, default: bool = False) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _admin_email_set() -> set[str]:
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
    SECRET_KEY = os.environ.get("SECRET_KEY") or secrets.token_hex(32)

    # Production DB URL via environment. SQLite remains the local fallback.
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL", "sqlite:///pharmacy.db")

    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = _env_flag(
        "SESSION_COOKIE_SECURE",
        default=not _env_flag("FLASK_DEBUG", default=False),
    )

    PLATFORM_ADMIN_EMAILS = _admin_email_set()
