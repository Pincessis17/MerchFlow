# app/config.py
import os

class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-only-change-me")

    # Postgres in production (DATABASE_URL), SQLite fallback for local
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "postgresql://postgres:MerchFlow2026@db.jltexyjrmbjmyuaumxdo.supabase.co:5432/postgres",
        "sqlite:///pharmacy.db"
    )

    SQLALCHEMY_TRACK_MODIFICATIONS = False

    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_SAMESITE = "LAX"
    