from functools import wraps
from flask import session, redirect, url_for, flash

def roles_required(*allowed_roles):
    def decorator(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            user = session.get("user")
            role = (user or {}).get("role")
            if not user:
                flash("Please log in.", "error")
                return redirect(url_for("auth.login"))
            if role not in allowed_roles:
                flash("You are not authorized to access that page.", "error")
                return redirect(url_for("home"))
            return view(*args, **kwargs)
        return wrapped
    return decorator
