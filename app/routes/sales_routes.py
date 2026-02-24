# app/routes/sales_routes.py
from datetime import datetime, date, time

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
from ..models import Product, Sale
from ..utils.auth import login_required

sales_bp = Blueprint("sales", __name__, url_prefix="/sales")


@sales_bp.route("/", methods=["GET", "POST"])
@login_required
def sales_home():
    """Record a new sale and show recent sales + today's summary."""

    products = Product.query.order_by(Product.name).all()

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

        product = Product.query.get_or_404(product_id)

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
        unit_price = float(product.price or 0.0)

        # Cost price (from Product)
        buying_price = float(product.buying_price or 0.0)

        line_total = unit_price * quantity
        line_profit = (unit_price - buying_price) * quantity

        # Create Sale
        sale = Sale(
            company_id=session.get("user", {}).get("company_id"),
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
    recent_sales = Sale.query.order_by(Sale.created_at.desc()).limit(20).all()

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
    .filter(Sale.created_at >= start_of_day, Sale.created_at <= end_of_day)
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

    )


@sales_bp.route("/delete/<int:sale_id>", methods=["POST"])
@login_required
def delete_sale(sale_id):
    sale = Sale.query.get_or_404(sale_id)

    # Return stock
    if sale.product and sale.quantity:
        sale.product.quantity = int(sale.product.quantity or 0) + int(sale.quantity or 0)

    db.session.delete(sale)
    db.session.commit()

    flash("Sale deleted.", "info")
    return redirect(url_for("sales.sales_home"))
