# app/routes/inventory_routes.py
from flask import Blueprint, render_template, request, redirect, url_for, flash, session

from .. import db
from ..models import Product
from ..utils.auth import login_required

inventory_bp = Blueprint("inventory", __name__)


def _generate_code_from_name(name: str) -> str:
    """
    Simple helper to generate a unique code for manually-added products.
    Uses the name and appends -2, -3, ... if needed.
    """
    base = name.strip().upper().replace(" ", "-") or "ITEM"
    code = base
    counter = 1

    while Product.query.filter_by(code=code).first() is not None:
        counter += 1
        code = f"{base}-{counter}"

    return code


@inventory_bp.route("/", methods=["GET", "POST"])
@login_required
def inventory_home():
    # ----- Handle new product form -----
    if request.method == "POST":
        name = request.form.get("name", "").strip()

        # Safer parsing (prevents ValueError if field is empty or invalid)
        try:
            quantity = int(request.form.get("quantity") or 0)
        except ValueError:
            quantity = 0

        unit = (request.form.get("unit") or "").strip() or None
        category = (request.form.get("category") or "").strip() or None
        expiry_raw = (request.form.get("expiry_date") or "").strip()

        try:
            price = float(request.form.get("price") or 0)
        except ValueError:
            price = 0.0

        expiry_date = expiry_raw or None  # stored as plain string in the DB

        if not name:
            flash("Product name is required.", "error")
            return redirect(url_for("inventory.inventory_home"))

        # Auto-generate a code for this product
        code = _generate_code_from_name(name)

        product = Product(
            code=code,
            name=name,
            quantity=quantity,
            category=category,
            expiry_date=expiry_date,
            price=price,
            company_id=session.get("user", {}).get("company_id"),
        )

        db.session.add(product)
        db.session.commit()
        flash(f"Product '{name}' added.", "success")
        return redirect(url_for("inventory.inventory_home"))

    # ----- Show current inventory -----
    products = Product.query.order_by(Product.name).all()

    # ✅ No low stock section here anymore
    return render_template(
        "inventory.html",
        products=products,
    )


@inventory_bp.route("/edit/<int:product_id>/", methods=["GET", "POST"])
@login_required
def edit_product(product_id):
    product = Product.query.get_or_404(product_id)

    if request.method == "POST":
        product.name = request.form.get("name", "").strip() or product.name

        try:
            product.quantity = int(request.form.get("quantity") or 0)
        except ValueError:
            product.quantity = 0

        product.category = (request.form.get("category") or "").strip() or None

        expiry_raw = (request.form.get("expiry_date") or "").strip()
        product.expiry_date = expiry_raw or None

        try:
            product.price = float(request.form.get("price") or 0)
        except ValueError:
            product.price = 0.0

        db.session.commit()
        flash("Product updated.", "success")
        return redirect(url_for("inventory.inventory_home"))

    return render_template("edit_products.html", product=product)


@inventory_bp.route("/delete/<int:product_id>/")
@login_required
def delete_product(product_id):
    product = Product.query.get_or_404(product_id)
    db.session.delete(product)
    db.session.commit()
    flash(f"Deleted {product.name}", "info")
    return redirect(url_for("inventory.inventory_home"))
