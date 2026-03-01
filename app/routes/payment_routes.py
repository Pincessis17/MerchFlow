from flask import Blueprint, request, redirect, url_for, flash, g
from .. import db
from ..models import Invoice, Payment
from ..utils.auth import login_required

payments_bp = Blueprint("payments", __name__)

@payments_bp.route("/record/<int:invoice_id>", methods=["POST"])
@login_required
def record(invoice_id):
    invoice = Invoice.query.filter_by(id=invoice_id, company_id=g.company.id).first_or_404()
    
    amount = request.form.get("amount", type=float)
    method = request.form.get("payment_method", "cash")
    
    if not amount or amount <= 0:
        flash("Invalid payment amount.", "error")
        return redirect(url_for("invoices.detail", invoice_id=invoice.id))

    payment = Payment(
        company_id=g.company.id,
        invoice_id=invoice.id,
        amount=amount,
        payment_method=method
    )
    db.session.add(payment)
    
    # Auto logic
    invoice.amount_paid += amount
    if invoice.amount_paid >= invoice.total_amount:
        invoice.status = "paid"
        invoice.amount_paid = invoice.total_amount # cap it
    elif invoice.amount_paid > 0:
        invoice.status = "partial"
    else:
        invoice.status = "unpaid"

    db.session.commit()
    flash("Payment recorded successfully.", "success")
    return redirect(url_for("invoices.detail", invoice_id=invoice.id))
