# app/routes/financial_routes.py

from datetime import datetime, date, time
import io

from flask import (
    Blueprint,
    current_app,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    send_file,
    session,
)

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

from .. import db
from ..models import (
    Sale,
    Product,
    Supplier,
    Purchase,
    FeatureAccess,
)
from ..utils.auth import login_required


financial_bp = Blueprint("financial", __name__, url_prefix="/financial")


# =====================================================
# Permission Helper (Company Scoped)
# =====================================================
def _is_platform_admin(email: str) -> bool:
    configured = current_app.config.get("PLATFORM_ADMIN_EMAILS") or set()
    return str(email or "").strip().lower() in configured


def _safe_parse_date(raw_value: str, fallback: date) -> date:
    try:
        return datetime.strptime((raw_value or "").strip(), "%Y-%m-%d").date()
    except ValueError:
        return fallback


def has_financial_access():
    user = session.get("user")
    if not user:
        return False

    # Platform owner bypass
    if _is_platform_admin(user.get("email")):
        return True

    access = FeatureAccess.query.filter_by(
        company_id=user.get("company_id"),
        email=user.get("email"),
        feature="financial",
        is_enabled=True,
    ).first()

    return access is not None

def deny_access():
    flash("You do not have access to this feature.", "error")
    return redirect(url_for("home"))


# =====================================================
# Financial Dashboard (Company Scoped)
# =====================================================
@financial_bp.route("/", methods=["GET"])
@login_required
def financial_home():

    if not has_financial_access():
        return deny_access()

    user = session.get("user")
    company_id = user["company_id"]

    start_date_str = request.args.get("start_date") or date.today().strftime("%Y-%m-%d")
    end_date_str = request.args.get("end_date") or date.today().strftime("%Y-%m-%d")

    start_date = _safe_parse_date(start_date_str, date.today())
    end_date = _safe_parse_date(end_date_str, date.today())
    if end_date < start_date:
        end_date = start_date

    start_dt = datetime.combine(start_date, time.min)
    end_dt = datetime.combine(end_date, time.max)

    # ---- Sales (Company Scoped) ----
    sales = (
        Sale.query.filter(
            Sale.company_id == company_id,
            Sale.created_at >= start_dt,
            Sale.created_at <= end_dt,
        )
        .order_by(Sale.created_at.desc())
        .all()
    )

    total_revenue = sum(float(s.line_total or 0) for s in sales)
    total_profit = sum(float(s.line_profit or 0) for s in sales)
    total_cogs = sum(float(s.buying_price or 0) * int(s.quantity or 0) for s in sales)

    # ---- Purchases (Company Scoped) ----
    purchases = (
        Purchase.query.filter(
            Purchase.company_id == company_id,
            Purchase.created_at >= start_dt,
            Purchase.created_at <= end_dt,
        )
        .order_by(Purchase.id.desc())
        .all()
    )

    total_purchases = sum(float(p.line_total or 0) for p in purchases)

    return render_template(
        "financial.html",
        title="Financial",
        start_date=start_date,
        end_date=end_date,
        total_revenue=total_revenue,
        total_cogs=total_cogs,
        total_profit=total_profit,
        total_purchases=total_purchases,
        sales=sales[:20],
        purchases=purchases[:20],
    )

# =====================================================
# Financial Statement PDF (Company Scoped)
# =====================================================
@financial_bp.route("/statement.pdf", methods=["GET"])
@login_required
def financial_statement_pdf():

    if not has_financial_access():
        return deny_access()

    user = session.get("user")
    company_id = user["company_id"]

    start_date_str = request.args.get("start_date") or date.today().strftime("%Y-%m-%d")
    end_date_str = request.args.get("end_date") or date.today().strftime("%Y-%m-%d")

    start_date = _safe_parse_date(start_date_str, date.today())
    end_date = _safe_parse_date(end_date_str, date.today())
    if end_date < start_date:
        end_date = start_date

    start_dt = datetime.combine(start_date, time.min)
    end_dt = datetime.combine(end_date, time.max)

    sales = (
        Sale.query.filter(
            Sale.company_id == company_id,
            Sale.created_at >= start_dt,
            Sale.created_at <= end_dt,
        )
        .order_by(Sale.created_at.asc())
        .all()
    )

    total_revenue = sum(float(s.line_total or 0) for s in sales)
    total_profit = sum(float(s.line_profit or 0) for s in sales)
    total_cogs = sum(float(s.buying_price or 0) * int(s.quantity or 0) for s in sales)

    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    y = height - 50

    c.setFont("Helvetica-Bold", 14)
    c.drawString(50, y, "MerchFlow Financial Statement")
    y -= 20

    c.setFont("Helvetica", 11)
    c.drawString(50, y, f"Period: {start_date_str} to {end_date_str}")
    y -= 25

    c.setFont("Helvetica-Bold", 11)
    c.drawString(50, y, f"Total Revenue: {total_revenue:.2f}")
    y -= 16
    c.drawString(50, y, f"Total COGS:    {total_cogs:.2f}")
    y -= 16
    c.drawString(50, y, f"Total Profit:  {total_profit:.2f}")
    y -= 25

    c.setFont("Helvetica-Bold", 11)
    c.drawString(50, y, "Sales Lines (first 30):")
    y -= 16

    c.setFont("Helvetica", 9)

    for s in sales[:30]:
        product_name = s.product.name if s.product else "Unknown"

        line = (
            f"{s.created_at.strftime('%Y-%m-%d %H:%M')} | "
            f"{product_name} | "
            f"Qty {s.quantity} | "
            f"Total {float(s.line_total or 0):.2f} | "
            f"Profit {float(s.line_profit or 0):.2f}"
        )

        c.drawString(50, y, line[:110])
        y -= 12

        if y < 80:
            c.showPage()
            y = height - 50
            c.setFont("Helvetica", 9)

    c.showPage()
    c.save()

    buffer.seek(0)

    filename = f"financial_statement_{start_date_str}_to_{end_date_str}.pdf"

    return send_file(
        buffer,
        mimetype="application/pdf",
        as_attachment=True,
        download_name=filename,
    )


# =====================================================
# Suppliers (Company Scoped)
# =====================================================
@financial_bp.route("/suppliers", methods=["GET", "POST"])
@login_required
def suppliers():

    if not has_financial_access():
        return deny_access()

    user = session.get("user")
    company_id = user["company_id"]

    if request.method == "POST":
        name = (request.form.get("name") or "").strip()
        phone = (request.form.get("phone") or "").strip() or None
        email = (request.form.get("email") or "").strip() or None

        if not name:
            flash("Supplier name is required.", "error")
            return redirect(url_for("financial.suppliers"))

        supplier = Supplier(
            company_id=company_id,
            name=name,
            phone=phone,
            email=email,
        )

        db.session.add(supplier)
        db.session.commit()

        flash("Supplier added successfully.", "success")
        return redirect(url_for("financial.suppliers"))

    suppliers = (
        Supplier.query
        .filter_by(company_id=company_id)
        .order_by(Supplier.name.asc())
        .all()
    )

    return render_template(
        "suppliers.html",
        title="Suppliers",
        suppliers=suppliers,
    )


# =====================================================
# Purchases (Company Scoped)
# =====================================================
@financial_bp.route("/purchases", methods=["GET", "POST"])
@login_required
def purchases():

    if not has_financial_access():
        return deny_access()

    user = session.get("user")
    company_id = user["company_id"]

    suppliers = (
        Supplier.query
        .filter_by(company_id=company_id)
        .order_by(Supplier.name.asc())
        .all()
    )

    products = (
        Product.query
        .filter_by(company_id=company_id)
        .order_by(Product.name.asc())
        .all()
    )

    if request.method == "POST":
        try:
            supplier_id = int(request.form.get("supplier_id") or 0)
            product_id = int(request.form.get("product_id") or 0)
            quantity = int(request.form.get("quantity") or 0)
            unit_cost = float(
                request.form.get("unit_cost")
                or request.form.get("buying_price")
                or 0.0
            )
        except ValueError:
            flash("Please provide valid numeric values for quantity and unit cost.", "error")
            return redirect(url_for("financial.purchases"))

        if not supplier_id or not product_id or quantity <= 0 or unit_cost < 0:
            flash("Please select supplier, product and enter valid quantity.", "error")
            return redirect(url_for("financial.purchases"))

        supplier = Supplier.query.filter_by(
            id=supplier_id,
            company_id=company_id
        ).first_or_404()

        product = Product.query.filter_by(
            id=product_id,
            company_id=company_id
        ).first_or_404()

        line_total = round(unit_cost * quantity, 2)

        purchase = Purchase(
            company_id=company_id,
            supplier=supplier,
            product=product,
            quantity=quantity,
            unit_cost=unit_cost,
            line_total=line_total,
        )

        previous_stock = int(product.quantity or 0)
        previous_cost = float(product.buying_price or 0.0)
        updated_stock = previous_stock + quantity

        # Keep a moving average cost so new sales use a realistic COGS basis.
        if updated_stock > 0:
            weighted_cost = (
                (previous_stock * previous_cost) + (quantity * unit_cost)
            ) / updated_stock
            product.buying_price = round(weighted_cost, 4)

        product.quantity = updated_stock

        db.session.add(purchase)
        db.session.commit()

        flash("Purchase recorded and stock updated.", "success")
        return redirect(url_for("financial.purchases"))

    recent_purchases = (
        Purchase.query
        .filter_by(company_id=company_id)
        .order_by(Purchase.id.desc())
        .limit(30)
        .all()
    )

    return render_template(
        "purchases.html",
        title="Purchases",
        suppliers=suppliers,
        products=products,
        recent_purchases=recent_purchases,
    )
