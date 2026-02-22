# app/utils/auth.py
from functools import wraps
from flask import session, redirect, url_for, flash, request


def login_required(view_func):
    @wraps(view_func)
    def wrapped(*args, **kwargs):
        if not session.get("user"):
            flash("Please log in to continue.", "error")
            return redirect(url_for("auth.login", next=request.path))
        return view_func(*args, **kwargs)

    return wrapped


def role_required(*allowed_roles):
    """
    Usage:
        @role_required("admin", "accountant")
    Expects session['user'] to contain a 'role' key.
    Example:
        session['user'] = {"id": 1, "name": "...", "email": "...", "role": "admin"}
    """
    allowed = {r.lower() for r in allowed_roles}

    def decorator(view_func):
        @wraps(view_func)
        def wrapped(*args, **kwargs):
            user = session.get("user") or {}
            role = str(user.get("role") or "").lower()

            if role not in allowed:
                flash("You are not authorized to access that page.", "error")
                return redirect(url_for("home"))

            return view_func(*args, **kwargs)

        return wrapped

    return decorator
