# app/routes/admin_routes.py

from flask import Blueprint, current_app, render_template, redirect, url_for, flash, request, session
from .. import db
from ..models import User, FeatureAccess
from ..utils.auth import login_required

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")
ALLOWED_FEATURES = {"financial"}


# ------------------------------------------------
# Super Admin (Platform Owner)
# ------------------------------------------------
def super_admin_required():
    user = session.get("user") or {}
    email = str(user.get("email") or "").strip().lower()
    admin_emails = current_app.config.get("PLATFORM_ADMIN_EMAILS") or set()
    return email in admin_emails


# ------------------------------------------------
# Admin Dashboard (Company Scoped)
# ------------------------------------------------
@admin_bp.route("/")
@login_required
def admin_home():

    if not super_admin_required():
        flash("You are not allowed to access Admin Panel.", "error")
        return redirect(url_for("home"))

    user = session.get("user")
    company_id = user["company_id"]

    users = (
        User.query
        .filter_by(company_id=company_id)
        .order_by(User.created_at.desc())
        .all()
    )

    access = (
        FeatureAccess.query
        .filter_by(company_id=company_id)
        .all()
    )

    return render_template(
        "admin/admin_dashboard.html",
        title="Admin Panel",
        users=users,
        access=access,
    )


# ------------------------------------------------
# Grant Feature Access
# ------------------------------------------------
@admin_bp.route("/grant", methods=["POST"])
@login_required
def grant_access():

    if not super_admin_required():
        flash("Unauthorized.", "error")
        return redirect(url_for("home"))

    user = session.get("user")
    company_id = user["company_id"]

    email = (request.form.get("email") or "").strip().lower()
    feature = (request.form.get("feature") or "").strip().lower()
    if not email or feature not in ALLOWED_FEATURES:
        flash("Invalid access request.", "error")
        return redirect(url_for("admin.admin_home"))

    target_user = User.query.filter_by(company_id=company_id, email=email).first()
    if not target_user:
        flash("User was not found in your company.", "error")
        return redirect(url_for("admin.admin_home"))

    existing = FeatureAccess.query.filter_by(
        company_id=company_id,
        email=email,
        feature=feature
    ).first()

    if existing:
        existing.is_enabled = True
    else:
        fa = FeatureAccess(
            company_id=company_id,
            email=email,
            feature=feature,
            is_enabled=True,
            granted_by=user.get("email")
        )
        db.session.add(fa)

    db.session.commit()
    flash("Access granted.", "success")
    return redirect(url_for("admin.admin_home"))


# ------------------------------------------------
# Revoke Feature Access
# ------------------------------------------------
@admin_bp.route("/revoke", methods=["POST"])
@login_required
def revoke_access():

    if not super_admin_required():
        flash("Unauthorized.", "error")
        return redirect(url_for("home"))

    user = session.get("user")
    company_id = user["company_id"]

    email = (request.form.get("email") or "").strip().lower()
    feature = (request.form.get("feature") or "").strip().lower()
    if not email or feature not in ALLOWED_FEATURES:
        flash("Invalid access request.", "error")
        return redirect(url_for("admin.admin_home"))

    access = FeatureAccess.query.filter_by(
        company_id=company_id,
        email=email,
        feature=feature
    ).first()

    if access:
        access.is_enabled = False
        db.session.commit()
        flash("Access revoked.", "info")

    return redirect(url_for("admin.admin_home"))
