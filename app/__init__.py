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
    from .routes.reports_routes import reports_bp
    from .routes.financial_routes import financial_bp
    from .routes.admin_routes import admin_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(sales_bp, url_prefix="/sales")
    app.register_blueprint(inventory_bp, url_prefix="/inventory")
    app.register_blueprint(reports_bp, url_prefix="/reports")
    app.register_blueprint(financial_bp, url_prefix="/financial")
    app.register_blueprint(admin_bp, url_prefix="/admin")

    # ==================================================
    # CLI COMMANDS
    # ==================================================
    from .commands import create_user
    app.cli.add_command(create_user)

    # ==================================================
    # JINJA GLOBALS
    # ==================================================
    from .utils.permissions import has_feature_access
    app.jinja_env.globals["has_feature_access"] = has_feature_access
    app.jinja_env.globals["csrf_token"] = generate_csrf_token

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
    from .models import Product, Sale
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

        # ---------------------------
        # Basic Metrics
        # ---------------------------
        total_products = (
            Product.query.filter_by(company_id=company_id).count()
        )

        total_stock = (
            db.session.query(func.coalesce(func.sum(Product.quantity), 0))
            .filter(Product.company_id == company_id)
            .scalar()
        )

        total_sales_value = (
            db.session.query(func.coalesce(func.sum(Sale.line_total), 0.0))
            .filter(Sale.company_id == company_id)
            .scalar()
        )

        # ---------------------------
        # Today's Sales
        # ---------------------------
        today = datetime.utcnow().date()
        day_start = datetime.combine(today, time.min)
        day_end = datetime.combine(today, time.max)

        today_sales_q = Sale.query.filter(
            Sale.company_id == company_id,
            Sale.created_at >= day_start,
            Sale.created_at <= day_end
        )

        today_sales_count = today_sales_q.count()

        today_sales_total = (
            today_sales_q.with_entities(
                func.coalesce(func.sum(Sale.line_total), 0.0)
            ).scalar()
        )

        # ---------------------------
        # Low Stock
        # ---------------------------
        LOW_STOCK_THRESHOLD = 5

        low_stock_products = (
            Product.query.filter(
                Product.company_id == company_id,
                Product.quantity <= LOW_STOCK_THRESHOLD
            )
            .order_by(Product.quantity.asc())
            .all()
        )

        # ---------------------------
        # Top Selling Products
        # ---------------------------
        top_selling_raw = (
            db.session.query(
                Product.name.label("name"),
                func.coalesce(func.sum(Sale.quantity), 0).label("qty"),
                func.coalesce(func.sum(Sale.line_total), 0.0).label("revenue"),
            )
            .join(Sale, Sale.product_id == Product.id)
            .filter(Sale.company_id == company_id)
            .group_by(Product.id)
            .order_by(func.sum(Sale.line_total).desc())
            .limit(5)
            .all()
        )

        top_selling = [
            {
                "name": r.name,
                "qty": int(r.qty or 0),
                "revenue": float(r.revenue or 0),
            }
            for r in top_selling_raw
        ]

        return render_template(
            "dashboard.html",
            total_products=total_products,
            total_stock=total_stock,
            total_sales_value=total_sales_value,
            today_sales_count=today_sales_count,
            today_sales_total=today_sales_total,
            low_stock_products=low_stock_products,
            top_selling=top_selling,
        )

    return app
