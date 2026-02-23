from functools import wraps
from time import time

from flask import current_app, flash, redirect, request, session, url_for

from .. import db
from ..models import PlatformAuditLog


def is_platform_owner(user=None) -> bool:
    payload = user or (session.get("user") or {})
    email = str(payload.get("email") or "").strip().lower()
    owner_emails = current_app.config.get("PLATFORM_ADMIN_EMAILS") or set()
    return email in owner_emails


def platform_owner_required(view_func):
    @wraps(view_func)
    def wrapped(*args, **kwargs):
        if not session.get("user"):
            flash("Please log in to continue.", "error")
            return redirect(url_for("auth.login", next=request.path))

        if not is_platform_owner():
            flash("Platform owner access is required.", "error")
            return redirect(url_for("home"))

        return view_func(*args, **kwargs)

    return wrapped


def platform_owner_elevated_required(view_func):
    @wraps(view_func)
    def wrapped(*args, **kwargs):
        if not session.get("user"):
            flash("Please log in to continue.", "error")
            return redirect(url_for("auth.login", next=request.path))

        if not is_platform_owner():
            flash("Platform owner access is required.", "error")
            return redirect(url_for("home"))

        elevated_until = int(session.get("platform_elevated_until") or 0)
        if elevated_until <= int(time()):
            next_url = request.path
            if request.query_string:
                next_url = f"{request.path}?{request.query_string.decode('utf-8', errors='ignore')}"
            flash("Please re-authenticate for elevated platform access.", "error")
            return redirect(url_for("platform.elevate_access", next=next_url))

        return view_func(*args, **kwargs)

    return wrapped


def set_platform_elevated_session():
    window = int(current_app.config.get("PLATFORM_ELEVATED_AUTH_WINDOW_SECONDS") or 900)
    session["platform_elevated_until"] = int(time()) + max(window, 60)


def clear_platform_elevated_session():
    session.pop("platform_elevated_until", None)


def log_platform_audit(
    action: str,
    target_type: str,
    *,
    target_id: str | None = None,
    company_id: int | None = None,
    details: str | None = None,
):
    user = session.get("user") or {}
    entry = PlatformAuditLog(
        actor_user_id=user.get("id"),
        actor_email=user.get("email"),
        action=action,
        target_type=target_type,
        target_id=target_id,
        company_id=company_id,
        details=details,
        ip_address=request.remote_addr,
        user_agent=(request.headers.get("User-Agent") or "")[:400],
    )
    db.session.add(entry)
