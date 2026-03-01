from flask import Blueprint, render_template, request, redirect, url_for, flash, g
import json
from datetime import datetime
from .. import db
from ..models import Sale, SaleItem, Customer, Invoice
from ..utils.auth import login_required

sales_bp = Blueprint("sales", __name__)

@sales_bp.route("/create", methods=["GET", "POST"])
@login_required
def create():
    if request.method == "POST":
        customer_id = request.form.get("customer_id", type=int)
        if not customer_id:
            flash("Customer is required.", "error")
            return redirect(url_for("sales.create"))
            
        action = request.form.get("action", "draft")
        items_json = request.form.get("items_json")
        try:
            items_data = json.loads(items_json) if items_json else []
        except:
            items_data = []

        if not items_data:
            flash("At least one item is required.", "error")
            return redirect(url_for("sales.create"))

        # Create Sale
        sale = Sale(
            company_id=g.company.id,
            customer_id=customer_id,
            status="draft",
            subtotal=0.0,
            tax=0.0,
            total_amount=0.0
        )
        db.session.add(sale)
        db.session.flush()

        subtotal = 0.0
        for item in items_data:
            qty = int(item.get("quantity", 1))
            price = float(item.get("unit_price", 0.0))
            line_total = qty * price
            subtotal += line_total
            
            s_item = SaleItem(
                sale_id=sale.id,
                product_name=item.get("product_name", "Unknown Item"),
                quantity=qty,
                unit_price=price,
                line_total=line_total
            )
            db.session.add(s_item)

        # Tax is 0 for now or compute based on logic
        sale.subtotal = subtotal
        sale.total_amount = subtotal

        if action == "invoice":
            sale.status = "invoiced"
            # create invoice
            existing_count = Invoice.query.filter_by(company_id=g.company.id).count()
            inv_number = f"INV-{datetime.utcnow().year}-{existing_count + 1:03d}"
            
            invoice = Invoice(
                company_id=g.company.id,
                sale_id=sale.id,
                invoice_number=inv_number,
                total_amount=sale.total_amount,
                amount_paid=0.0,
                status="unpaid"
            )
            db.session.add(invoice)
            db.session.commit()
            flash("Sale created and converted to Invoice.", "success")
            return redirect(url_for("invoices.detail", invoice_id=invoice.id))
        else:
            db.session.commit()
            flash("Sale saved as Draft.", "success")
            return redirect(url_for("sales.create"))

    customers = Customer.query.filter_by(company_id=g.company.id).order_by(Customer.name.asc()).all()
    return render_template("sales/create.html", customers=customers, title="Create Sale")
