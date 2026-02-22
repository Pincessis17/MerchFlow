from collections import defaultdict, deque
from time import time

from flask import Blueprint, current_app, render_template, request, redirect, url_for, flash, session
from ..models import User
from ..utils.auth import login_required

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")

FAILED_LOGIN_WINDOW_SECONDS = 300
FAILED_LOGIN_MAX_ATTEMPTS = 5
FAILED_LOGIN_ATTEMPTS = defaultdict(deque)


def _is_platform_admin_email(email: str) -> bool:
    configured = current_app.config.get("PLATFORM_ADMIN_EMAILS") or set()
    return str(email or "").strip().lower() in configured


def _client_ip() -> str:
    # If app is behind a trusted reverse proxy, the first value is the caller IP.
    forwarded = (request.headers.get("X-Forwarded-For") or "").strip()
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.remote_addr or "unknown"


def _prune_attempts(ip_address: str, now: float):
    attempts = FAILED_LOGIN_ATTEMPTS[ip_address]
    while attempts and (now - attempts[0]) > FAILED_LOGIN_WINDOW_SECONDS:
        attempts.popleft()
    return attempts


# ======================================================
# LOGIN
# ======================================================
@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    user_session = session.get("user")

    # Only redirect if session is COMPLETE and valid
    if user_session and user_session.get("company_id"):
        return redirect(url_for("home"))

    if request.method == "POST":
        now = time()
        ip_address = _client_ip()
        attempts = _prune_attempts(ip_address, now)

        if len(attempts) >= FAILED_LOGIN_MAX_ATTEMPTS:
            flash("Too many failed login attempts. Please try again in a few minutes.", "error")
            return render_template("login.html")

        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        if not email or not password:
            flash("Email and password are required.", "error")
            return render_template("login.html", email=email)

        user = User.query.filter_by(email=email).first()

        if not user or not user.check_password(password):
            FAILED_LOGIN_ATTEMPTS[ip_address].append(now)
            flash("Invalid email or password.", "error")
            return render_template("login.html", email=email)

        # Clear old session
        session.clear()
        FAILED_LOGIN_ATTEMPTS.pop(ip_address, None)

        # Store complete session context
        session["user"] = {
            "id": user.id,
            "company_id": user.company_id,
            "company_name": user.company.name if user.company else "",
            "email": user.email,
            "name": user.name,
            "is_platform_admin": _is_platform_admin_email(user.email),
        }

        flash(f"Welcome back, {user.name}!", "success")
        return redirect(url_for("home"))

    return render_template("login.html")


# ======================================================
# LOGOUT
# ======================================================
@auth_bp.route("/logout", methods=["POST"])
@login_required
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("auth.login"))
