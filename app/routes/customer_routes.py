from flask import Blueprint, render_template, request, redirect, url_for, flash, g
from .. import db
from ..models import Customer
from ..utils.auth import login_required

customers_bp = Blueprint("customers", __name__)

@customers_bp.route("/", methods=["GET"])
@login_required
def index():
    customers = Customer.query.filter_by(company_id=g.company.id).order_by(Customer.created_at.desc()).all()
    return render_template("customers/index.html", customers=customers, title="Customers")

@customers_bp.route("/create", methods=["POST"])
@login_required
def create():
    name = (request.form.get("name") or "").strip()
    email = (request.form.get("email") or "").strip()
    phone = (request.form.get("phone") or "").strip()
    address = (request.form.get("address") or "").strip()

    if not name:
        flash("Customer name is required.", "error")
        return redirect(url_for("customers.index"))

    customer = Customer(
        company_id=g.company.id,
        name=name,
        email=email,
        phone=phone,
        address=address
    )
    db.session.add(customer)
    db.session.commit()
    flash("Customer created successfully.", "success")
    return redirect(url_for("customers.index"))
