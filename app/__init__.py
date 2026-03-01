# app/__init__.py

import hmac
import secrets
from datetime import datetime, time
from flask import Flask, abort, render_template, request, session, g, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from sqlalchemy import func

from .config import Config

db = SQLAlchemy()
migrate = Migrate()


def create_app():
    Config.validate()
    app = Flask(__name__)
    app.config.from_object(Config)
    app.config["APP_START_TIME"] = datetime.utcnow()

    db.init_app(app)
    migrate.init_app(app, db)

    def generate_csrf_token():
        token = session.get("_csrf_token")
        if not token:
            token = secrets.token_urlsafe(32)
            session["_csrf_token"] = token
        return token

    @app.before_request
    def csrf_protect():
        if request.method not in {"POST", "PUT", "PATCH", "DELETE"}:
            return

        sent_token = request.form.get("_csrf_token") or request.headers.get("X-CSRF-Token")
        session_token = session.get("_csrf_token")

        if not sent_token or not session_token or not hmac.compare_digest(sent_token, session_token):
            abort(400, description="Invalid CSRF token.")

    @app.after_request
    def set_security_headers(response):
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault(
            "Content-Security-Policy",
            "default-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:;",
        )
        return response

    # ==================================================
    # BLUEPRINTS
    # ==================================================
    from .routes.auth_routes import auth_bp
    from .routes.sales_routes import sales_bp
    from .routes.inventory_routes import inventory_bp
    from .routes.admin_routes import admin_bp
    from .routes.platform_routes import platform_bp
    from .routes.invoice_routes import invoices_bp
    from .routes.customer_routes import customers_bp
    from .routes.payment_routes import payments_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(sales_bp, url_prefix="/sales")
    app.register_blueprint(inventory_bp, url_prefix="/inventory")
    app.register_blueprint(admin_bp, url_prefix="/admin")
    app.register_blueprint(platform_bp, url_prefix="/platform")
    app.register_blueprint(invoices_bp, url_prefix="/invoices")
    app.register_blueprint(customers_bp, url_prefix="/customers")
    app.register_blueprint(payments_bp, url_prefix="/payments")

    # ==================================================
    # CLI COMMANDS
    # ==================================================
    from .commands import create_user
    app.cli.add_command(create_user)

    # ==================================================
    # JINJA GLOBALS
    # ==================================================
    from .utils.permissions import has_feature_access
    from .utils.platform_security import is_platform_owner
    app.jinja_env.globals["has_feature_access"] = has_feature_access
    app.jinja_env.globals["csrf_token"] = generate_csrf_token
    app.jinja_env.globals["is_platform_owner"] = is_platform_owner

    # ==================================================
    # LOAD COMPANY CONTEXT (Multi-Tenant Middleware)
    # ==================================================
    from .models import Company

    @app.before_request
    def load_company():
        """
        Automatically attach current company to Flask global `g`
        for easier access inside routes.
        """
        user = session.get("user")
        if user and user.get("company_id"):
            g.company = Company.query.get(user["company_id"])
        else:
            g.company = None

    # ==================================================
    # HEALTH CHECK
    # ==================================================
    @app.get("/health")
    def health():
        return {"status": "ok"}

    # ==================================================
    # DASHBOARD (Company Scoped)
    # ==================================================
    from .models import Customer, Invoice
    from .utils.auth import login_required

    @app.route("/")
    @login_required
    def home():
        user = session.get("user")

        # Defensive check
        if not user or not user.get("company_id"):
            flash("Session expired. Please login again.", "error")
            return redirect(url_for("auth.login"))

        company_id = user["company_id"]

        total_customers = Customer.query.filter_by(company_id=company_id).count()
        total_invoices = Invoice.query.filter_by(company_id=company_id).count()

        total_revenue = db.session.query(func.coalesce(func.sum(Invoice.total_amount), 0.0)) \
            .filter(Invoice.company_id == company_id, Invoice.status == "paid").scalar()

        outstanding_revenue = db.session.query(func.coalesce(func.sum(Invoice.total_amount - Invoice.amount_paid), 0.0)) \
            .filter(Invoice.company_id == company_id, Invoice.status != "paid").scalar()

        return render_template(
            "dashboard.html",
            total_customers=total_customers,
            total_invoices=total_invoices,
            total_revenue=total_revenue,
            outstanding_revenue=outstanding_revenue
        )

    return app
