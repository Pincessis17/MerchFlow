# app/routes/auth_routes.py

from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from .. import db
from ..models import User
from flask_limiter import Limiter
from flask import current_app
auth_bp = Blueprint("auth", __name__, url_prefix="/auth")


# ======================================================
# LOGIN
# ======================================================
@limiter.limit("5 per minute")

@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    user_session = session.get("user")

    # Only redirect if session is COMPLETE and valid
    if user_session and user_session.get("company_id"):
        return redirect(url_for("home"))

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        if not email or not password:
            flash("Email and password are required.", "error")
            return render_template("login.html", email=email)

        user = User.query.filter_by(email=email).first()

        if not user or not user.check_password(password):
            flash("Invalid email or password.", "error")
            return render_template("login.html", email=email)

        # Clear old session
        session.clear()

        PLATFORM_ADMIN_EMAIL = "addaiprincessnhyira@gmail.com"

        # Store complete SaaS-safe session
        session["user"] = {
            "id": user.id,
            "company_id": user.company_id,
            "company_name": user.company.name if user.company else "",
            "email": user.email,
            "name": user.name,
            "is_platform_admin": user.email == PLATFORM_ADMIN_EMAIL,
        }

        flash(f"Welcome back, {user.name}!", "success")
        return redirect(url_for("home"))

        return render_template("login.html")


        # 🔥 PLATFORM OWNER EMAIL
        PLATFORM_ADMIN_EMAIL = "addaiprincessnhyira@gmail.com"

        # ✅ Store complete SaaS-safe session context
        session["user"] = {
            "id": user.id,
            "company_id": user.company_id,
            "company_name": user.company.name if user.company else "",
            "email": user.email,
            "name": user.name,
            "is_platform_admin": user.email == PLATFORM_ADMIN_EMAIL
        }

        flash(f"Welcome back, {user.name}!", "success")
        return redirect(url_for("home"))

    return render_template("login.html")


# ======================================================
# LOGOUT
# ======================================================
@auth_bp.route("/logout")
def logout():
    session.clear()  # safer than pop
    flash("You have been logged out.", "info")
    return redirect(url_for("auth.login"))
