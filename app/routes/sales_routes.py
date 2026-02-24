# app/routes/sales_routes.py
from datetime import datetime, date, time

from sqlalchemy import or_
from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    session,
)

from .. import db
from ..models import Invoice, Product, Sale
from ..utils.auth import login_required

sales_bp = Blueprint("sales", __name__, url_prefix="/sales")


@sales_bp.route("/", methods=["GET", "POST"])
@login_required
def sales_home():
    """Record a new sale and show recent sales + today's summary."""

    user = session.get("user") or {}
    company_id = user.get("company_id")
    if not company_id:
        flash("Session expired. Please log in again.", "error")
        return redirect(url_for("auth.login"))

    search_query = (request.args.get("q") or "").strip()
    products_query = Product.query.filter_by(company_id=company_id)
    if search_query:
        like_value = f"%{search_query}%"
        products_query = products_query.filter(
            or_(
                Product.name.ilike(like_value),
                Product.code.ilike(like_value),
                Product.category.ilike(like_value),
            )
        )
    products = products_query.order_by(Product.name.asc()).all()

    # ---------- HANDLE NEW SALE (POST) ----------
    if request.method == "POST":
        product_id_raw = request.form.get("product_id")
        qty_raw = request.form.get("quantity")

        # Basic validation
        try:
            product_id = int(product_id_raw or 0)
            quantity = int(qty_raw or 0)
        except ValueError:
            flash("Quantity must be a number.", "error")
            return redirect(url_for("sales.sales_home"))

        if not product_id or quantity <= 0:
            flash("Please select a product and enter a quantity.", "error")
            return redirect(url_for("sales.sales_home"))

        product = Product.query.filter_by(
            id=product_id,
            company_id=company_id,
        ).first_or_404()

        # Check stock
        current_stock = int(product.quantity or 0)
        if current_stock < quantity:
            flash(
                f"Not enough stock for {product.name}. "
                f"Available: {current_stock}, requested: {quantity}.",
                "error",
            )
            return redirect(url_for("sales.sales_home"))

        # Selling price (from Product)
        unit_price = round(float(product.price or 0.0), 2)

        # Cost price (from Product)
        buying_price = round(float(product.buying_price or 0.0), 2)

        line_total = round(unit_price * quantity, 2)
        line_profit = round((unit_price - buying_price) * quantity, 2)

        # Create Sale
        sale = Sale(
            company_id=company_id,
            product=product,
            quantity=quantity,
            unit_price=unit_price,
            line_total=line_total,
            buying_price=buying_price,
            line_profit=line_profit,
        )

        # Reduce stock
        product.quantity = current_stock - quantity

        db.session.add(sale)
        db.session.commit()

        flash(f"Recorded sale: {product.name} x {quantity}", "success")
        return redirect(url_for("sales.sales_home"))

    # ---------- SHOW PAGE (GET) ----------

    # Recent sales table
    recent_sales_query = Sale.query.filter_by(company_id=company_id)
    if search_query:
        like_value = f"%{search_query}%"
        recent_sales_query = (
            recent_sales_query
            .join(Product, Product.id == Sale.product_id)
            .filter(
                or_(
                    Product.name.ilike(like_value),
                    Product.code.ilike(like_value),
                    Product.category.ilike(like_value),
                )
            )
        )

    recent_sales = (
        recent_sales_query
        .order_by(Sale.created_at.desc())
        .limit(50)
        .all()
    )
    recent_sale_ids = [sale.id for sale in recent_sales]
    linked_invoices = {}
    if recent_sale_ids:
        linked_invoices = {
            inv.sale_id: inv
            for inv in Invoice.query.filter(
                Invoice.company_id == company_id,
                Invoice.sale_id.in_(recent_sale_ids),
            ).all()
            if inv.sale_id is not None
        }

    # Today's summary
    today = date.today()
    start_of_day = datetime.combine(today, time.min)
    end_of_day = datetime.combine(today, time.max)

    totals = (
        db.session.query(
            db.func.count(Sale.id),
            db.func.coalesce(db.func.sum(Sale.quantity), 0),
            db.func.coalesce(db.func.sum(Sale.line_total), 0.0),
            db.func.coalesce(db.func.sum(Sale.line_profit), 0.0),
        )
        .filter(
            Sale.company_id == company_id,
            Sale.created_at >= start_of_day,
            Sale.created_at <= end_of_day,
        )
        .one()
    )

    today_sales_count, today_items_sold, today_total_amount, today_total_profit = totals

    return render_template(
        "sales.html",
        title="Sales",
        products=products,
        recent_sales=recent_sales,
        today_sales_count=today_sales_count,
        today_items_sold=today_items_sold,
        today_total_amount=today_total_amount,
        today_total_profit=today_total_profit,
        search_query=search_query,
        linked_invoices=linked_invoices,

    )


@sales_bp.route("/delete/<int:sale_id>", methods=["POST"])
@login_required
def delete_sale(sale_id):
    user = session.get("user") or {}
    company_id = user.get("company_id")
    if not company_id:
        flash("Session expired. Please log in again.", "error")
        return redirect(url_for("auth.login"))

    sale = Sale.query.filter_by(id=sale_id, company_id=company_id).first_or_404()

    # Return stock
    if sale.product and sale.quantity:
        sale.product.quantity = int(sale.product.quantity or 0) + int(sale.quantity or 0)

    db.session.delete(sale)
    db.session.commit()

    flash("Sale deleted.", "info")
    return redirect(url_for("sales.sales_home"))
