from collections import defaultdict, deque
from time import time

from flask import Blueprint, current_app, render_template, request, redirect, url_for, flash, session
from .. import db
from ..models import Company, LoginAttempt, User
from ..utils.auth import login_required
from ..utils.notifications import create_platform_notification

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


def _record_login_attempt(*, email: str, ip_address: str, is_success: bool, company_id=None, abuse_score: int = 0):
    attempt = LoginAttempt(
        company_id=company_id,
        email=email,
        ip_address=ip_address,
        user_agent=(request.headers.get("User-Agent") or "")[:400],
        is_success=is_success,
        abuse_score=max(int(abuse_score or 0), 0),
    )
    db.session.add(attempt)


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
            _record_login_attempt(
                email=(request.form.get("email") or "").strip().lower(),
                ip_address=ip_address,
                is_success=False,
                abuse_score=len(attempts),
            )
            create_platform_notification(
                event_type="security.abuse_signal",
                title="Potential abuse signal detected",
                message=f"Too many failed login attempts from IP {ip_address}.",
                category="warning",
                payload={"ip_address": ip_address, "attempts": len(attempts)},
            )
            db.session.commit()
            flash("Too many failed login attempts. Please try again in a few minutes.", "error")
            return render_template("login.html")

        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        if not email or not password:
            flash("Email and password are required.", "error")
            return render_template("login.html", email=email)

        matching_users = User.query.filter_by(email=email).all()
        if len(matching_users) > 1:
            _record_login_attempt(
                email=email,
                ip_address=ip_address,
                is_success=False,
                abuse_score=len(FAILED_LOGIN_ATTEMPTS[ip_address]),
            )
            db.session.commit()
            flash("Multiple accounts are linked to this email. Please contact support.", "error")
            return render_template("login.html", email=email)

        user = matching_users[0] if matching_users else None

        if not user or not user.check_password(password):
            FAILED_LOGIN_ATTEMPTS[ip_address].append(now)
            _record_login_attempt(
                email=email,
                ip_address=ip_address,
                is_success=False,
                abuse_score=len(FAILED_LOGIN_ATTEMPTS[ip_address]),
            )
            db.session.commit()
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
            "role": user.role,
            "is_platform_admin": _is_platform_admin_email(user.email),
        }
        _record_login_attempt(
            email=email,
            ip_address=ip_address,
            is_success=True,
            company_id=user.company_id,
        )
        db.session.commit()

        flash(f"Welcome back, {user.name}!", "success")
        return redirect(url_for("home"))

    prefilled_email = (request.args.get("email") or "").strip().lower()
    return render_template("login.html", email=prefilled_email)


# ======================================================
# REGISTER (Tenant Self-Signup)
# ======================================================
@auth_bp.route("/register", methods=["GET", "POST"])
@auth_bp.route("/signup", methods=["GET", "POST"])
def register():
    user_session = session.get("user")
    if user_session and user_session.get("company_id"):
        return redirect(url_for("home"))

    if request.method == "POST":
        company_name = (request.form.get("company_name") or "").strip()
        name = (request.form.get("name") or "").strip()
        email = (request.form.get("email") or "").strip().lower()
        password = request.form.get("password") or ""
        confirm_password = request.form.get("confirm_password") or ""

        if not company_name or not name or not email or not password:
            flash("Company name, full name, email, and password are required.", "error")
            return render_template(
                "register.html",
                company_name=company_name,
                name=name,
                email=email,
            )

        if "@" not in email or "." not in email:
            flash("Please enter a valid email address.", "error")
            return render_template(
                "register.html",
                company_name=company_name,
                name=name,
                email=email,
            )

        if len(password) < 8:
            flash("Password must be at least 8 characters long.", "error")
            return render_template(
                "register.html",
                company_name=company_name,
                name=name,
                email=email,
            )

        if password != confirm_password:
            flash("Password confirmation does not match.", "error")
            return render_template(
                "register.html",
                company_name=company_name,
                name=name,
                email=email,
            )

        if User.query.filter_by(email=email).first():
            flash("An account with this email already exists. Please sign in.", "error")
            return redirect(url_for("auth.login", email=email))

        try:
            company = Company(name=company_name)
            db.session.add(company)
            db.session.flush()

            user = User(
                company_id=company.id,
                email=email,
                name=name,
                role="admin",
            )
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
        except Exception:
            db.session.rollback()
            flash("Could not create your account right now. Please try again.", "error")
            return render_template(
                "register.html",
                company_name=company_name,
                name=name,
                email=email,
            )

        flash("Account created successfully. Please sign in.", "success")
        return redirect(url_for("auth.login", email=email))

    return render_template("register.html")


# ======================================================
# LOGOUT
# ======================================================
@auth_bp.route("/logout", methods=["POST"])
@login_required
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("auth.login"))
