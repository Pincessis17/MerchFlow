from flask import Blueprint, render_template, request, redirect, url_for, flash, g
from .. import db
from ..models import Invoice
from ..utils.auth import login_required

invoices_bp = Blueprint("invoices", __name__)

@invoices_bp.route("/", methods=["GET"])
@login_required
def index():
    invoices = Invoice.query.filter_by(company_id=g.company.id).order_by(Invoice.created_at.desc()).all()
    return render_template("invoices/index.html", invoices=invoices, title="Invoices")

@invoices_bp.route("/<int:invoice_id>", methods=["GET"])
@login_required
def detail(invoice_id):
    invoice = Invoice.query.filter_by(id=invoice_id, company_id=g.company.id).first_or_404()
    return render_template("sales/invoice_detail.html", invoice=invoice, title=f"Invoice {invoice.invoice_number}")
