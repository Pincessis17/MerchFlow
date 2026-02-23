# app/routes/admin_routes.py

from flask import Blueprint, current_app, render_template, redirect, url_for, flash, request, session
from .. import db
from ..models import User, FeatureAccess
from ..utils.auth import login_required

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")
ALLOWED_FEATURES = {"financial"}
TENANT_TEAM_ROLES = {"admin", "manager", "staff", "accountant"}


# ------------------------------------------------
# Super Admin (Platform Owner)
# ------------------------------------------------
def super_admin_required():
    user = session.get("user") or {}
    email = str(user.get("email") or "").strip().lower()
    admin_emails = current_app.config.get("PLATFORM_ADMIN_EMAILS") or set()
    return email in admin_emails


def can_manage_team():
    user = session.get("user") or {}
    role = str(user.get("role") or "").strip().lower()
    return bool(user) and (role == "admin" or bool(user.get("is_platform_admin")))


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


# ------------------------------------------------
# Team Management (Tenant Admin)
# ------------------------------------------------
@admin_bp.route("/team", methods=["GET"])
@login_required
def team_management():
    if not can_manage_team():
        flash("Only company admins can manage staff accounts.", "error")
        return redirect(url_for("home"))

    user = session.get("user") or {}
    company_id = user.get("company_id")
    if not company_id:
        flash("Session expired. Please log in again.", "error")
        return redirect(url_for("auth.login"))

    users = (
        User.query
        .filter_by(company_id=company_id)
        .order_by(User.created_at.desc())
        .all()
    )
    return render_template("admin/team_management.html", users=users, tenant_roles=sorted(TENANT_TEAM_ROLES))


@admin_bp.route("/team/create", methods=["POST"])
@login_required
def create_team_user():
    if not can_manage_team():
        flash("Only company admins can manage staff accounts.", "error")
        return redirect(url_for("home"))

    actor = session.get("user") or {}
    company_id = actor.get("company_id")
    if not company_id:
        flash("Session expired. Please log in again.", "error")
        return redirect(url_for("auth.login"))

    email = (request.form.get("email") or "").strip().lower()
    name = (request.form.get("name") or "").strip()
    role = (request.form.get("role") or "staff").strip().lower()
    password = request.form.get("password") or ""
    confirm_password = request.form.get("confirm_password") or ""

    if not email or not name:
        flash("Name and email are required.", "error")
        return redirect(url_for("admin.team_management"))
    if "@" not in email or "." not in email:
        flash("Please provide a valid email address.", "error")
        return redirect(url_for("admin.team_management"))
    if role not in TENANT_TEAM_ROLES:
        flash("Invalid role selected.", "error")
        return redirect(url_for("admin.team_management"))
    if len(password) < 8:
        flash("Password must be at least 8 characters.", "error")
        return redirect(url_for("admin.team_management"))
    if password != confirm_password:
        flash("Password confirmation does not match.", "error")
        return redirect(url_for("admin.team_management"))

    existing = User.query.filter_by(company_id=company_id, email=email).first()
    if existing:
        flash("A user with this email already exists in your company.", "error")
        return redirect(url_for("admin.team_management"))

    user = User(
        company_id=company_id,
        email=email,
        name=name,
        role=role,
    )
    user.set_password(password)

    db.session.add(user)
    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        flash("Could not create this user. The email may already exist.", "error")
        return redirect(url_for("admin.team_management"))

    flash(f"User account created for {email}.", "success")
    return redirect(url_for("admin.team_management"))
