import io
import os
from datetime import datetime

from flask import (
    Blueprint,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    send_file,
    session,
    url_for,
)
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from sqlalchemy import or_
from werkzeug.utils import secure_filename

from .. import db
from ..models import Company, Invoice, InvoiceLineItem, InvoiceSetting, Sale, TenantNotification, User
from ..utils.analytics import send_ga4_event
from ..utils.auth import login_required, tenant_role_required
from ..utils.notifications import create_tenant_notification, send_email_notification

invoices_bp = Blueprint("invoices", __name__, url_prefix="/invoices")
ALLOWED_LOGO_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}
PAYMENT_METHOD_CHOICES = [
    ("pending", "Pending / Not selected"),
    ("cash", "Cash"),
    ("bank_transfer", "Bank Transfer"),
    ("card", "Card"),
    ("mobile_money", "Mobile Money"),
    ("cheque", "Cheque"),
    ("other", "Other"),
]
ALLOWED_PAYMENT_METHODS = {choice[0] for choice in PAYMENT_METHOD_CHOICES}


def _current_company_id():
    user = session.get("user") or {}
    return user.get("company_id")


def _parse_float(raw_value, default: float = 0.0) -> float:
    try:
        return float(raw_value)
    except (TypeError, ValueError):
        return default


def _parse_date(raw_value: str | None):
    if not raw_value:
        return None
    try:
        return datetime.strptime(raw_value, "%Y-%m-%d")
    except ValueError:
        return None


def _normalize_payment_method(raw_value: str | None, default: str = "pending") -> str:
    value = str(raw_value or "").strip().lower().replace(" ", "_")
    if value in ALLOWED_PAYMENT_METHODS:
        return value
    return default


def _calculate_totals(line_items: list[dict], tax_rate: float, discount_type: str, discount_value: float):
    subtotal = round(sum(float(row["line_total"]) for row in line_items), 2)
    tax_rate = max(float(tax_rate or 0.0), 0.0)
    tax_amount = round(subtotal * (tax_rate / 100.0), 2)

    discount_value = max(float(discount_value or 0.0), 0.0)
    discount_amount = 0.0
    if discount_type == "percent":
        discount_amount = round((subtotal + tax_amount) * (discount_value / 100.0), 2)
    elif discount_type == "fixed":
        discount_amount = min(round(discount_value, 2), subtotal + tax_amount)

    total_amount = round(max((subtotal + tax_amount) - discount_amount, 0.0), 2)
    return subtotal, tax_amount, discount_amount, total_amount


def _ensure_invoice_settings(company: Company):
    setting = InvoiceSetting.query.filter_by(company_id=company.id).first()
    if setting:
        return setting

    setting = InvoiceSetting(
        company_id=company.id,
        logo_path=company.logo_path,
        brand_color=company.brand_color or "#5b8cff",
        footer_text=company.invoice_footer,
        payment_instructions=company.payment_instructions,
        prefix=company.invoice_number_prefix or "INV",
        next_number=max(int(company.invoice_next_number or 1), 1),
    )
    db.session.add(setting)
    db.session.flush()
    return setting


def _generate_invoice_number(setting: InvoiceSetting, issue_date: datetime):
    seq = int(setting.next_number or 1)
    template = setting.numbering_format or "{prefix}-{yyyy}-{seq:05d}"
    mapping = {
        "prefix": setting.prefix or "INV",
        "yyyy": issue_date.strftime("%Y"),
        "yy": issue_date.strftime("%y"),
        "seq": seq,
    }
    try:
        invoice_number = template.format(**mapping)
    except Exception:
        invoice_number = f"{mapping['prefix']}-{mapping['yyyy']}-{seq:05d}"

    setting.next_number = seq + 1
    return invoice_number


def _parse_line_items():
    descriptions = request.form.getlist("item_description")
    qty_values = request.form.getlist("item_quantity")
    unit_price_values = request.form.getlist("item_unit_price")

    line_items = []
    for idx, description in enumerate(descriptions):
        desc = (description or "").strip()
        qty = _parse_float(qty_values[idx] if idx < len(qty_values) else 0, 0.0)
        unit_price = _parse_float(unit_price_values[idx] if idx < len(unit_price_values) else 0, 0.0)

        if not desc:
            continue
        if qty <= 0:
            continue
        if unit_price < 0:
            continue

        line_total = round(qty * unit_price, 2)
        line_items.append(
            {
                "description": desc[:300],
                "quantity": qty,
                "unit_price": round(unit_price, 2),
                "line_total": line_total,
                "sort_order": len(line_items) + 1,
            }
        )

    return line_items


def _company_admin_email(company_id: int):
    admin_user = (
        User.query.filter_by(company_id=company_id, role="admin")
        .order_by(User.id.asc())
        .first()
    )
    return admin_user.email if admin_user else None


@invoices_bp.route("/", methods=["GET"])
@login_required
def list_invoices():
    company_id = _current_company_id()
    if not company_id:
        flash("Session expired. Please log in again.", "error")
        return redirect(url_for("auth.login"))

    search_query = (request.args.get("q") or "").strip()
    issue_date_raw = (request.args.get("issue_date") or "").strip()

    invoices_query = Invoice.query.filter_by(company_id=company_id)
    if search_query:
        like_value = f"%{search_query}%"
        invoices_query = invoices_query.filter(
            or_(
                Invoice.invoice_number.ilike(like_value),
                Invoice.customer_name.ilike(like_value),
                Invoice.customer_email.ilike(like_value),
            )
        )

    if issue_date_raw:
        issue_date = _parse_date(issue_date_raw)
        if issue_date:
            invoices_query = invoices_query.filter(
                db.func.date(Invoice.issue_date) == issue_date.strftime("%Y-%m-%d")
            )
        else:
            flash("Invoice date filter is invalid. Use YYYY-MM-DD.", "error")

    invoices = invoices_query.order_by(Invoice.created_at.desc()).all()
    notifications = (
        TenantNotification.query.filter_by(company_id=company_id, is_read=False)
        .order_by(TenantNotification.created_at.desc())
        .limit(20)
        .all()
    )
    return render_template(
        "invoices/list.html",
        title="Invoices",
        invoices=invoices,
        tenant_notifications=notifications,
        search_query=search_query,
        issue_date_filter=issue_date_raw,
        payment_method_choices=PAYMENT_METHOD_CHOICES,
    )


@invoices_bp.route("/notifications/mark-read", methods=["POST"])
@login_required
def mark_tenant_notifications_read():
    company_id = _current_company_id()
    ids = request.form.getlist("notification_ids")
    if company_id and ids:
        TenantNotification.query.filter(
            TenantNotification.company_id == company_id,
            TenantNotification.id.in_(ids),
        ).update({"is_read": True}, synchronize_session=False)
        db.session.commit()
    return redirect(url_for("invoices.list_invoices"))


@invoices_bp.route("/from-sale/<int:sale_id>", methods=["POST"])
@login_required
@tenant_role_required("admin", "manager", "staff")
def create_invoice_from_sale(sale_id):
    company_id = _current_company_id()
    if not company_id:
        flash("Session expired. Please log in again.", "error")
        return redirect(url_for("auth.login"))

    sale = Sale.query.filter_by(id=sale_id, company_id=company_id).first_or_404()
    existing_invoice = Invoice.query.filter_by(company_id=company_id, sale_id=sale.id).first()
    if existing_invoice:
        flash("An invoice already exists for this sale.", "info")
        return redirect(url_for("invoices.view_invoice", invoice_id=existing_invoice.id))

    company = Company.query.get_or_404(company_id)
    setting = _ensure_invoice_settings(company)
    issue_date = datetime.utcnow()
    invoice_number = _generate_invoice_number(setting, issue_date)

    payment_method = _normalize_payment_method(request.form.get("payment_method"), default="pending")

    product_name = sale.product.name if sale.product else f"Sale #{sale.id}"
    invoice = Invoice(
        company_id=company_id,
        created_by_user_id=(session.get("user") or {}).get("id"),
        sale_id=sale.id,
        invoice_number=invoice_number,
        customer_name=(request.form.get("customer_name") or "").strip() or "Walk-in Customer",
        status="draft",
        payment_method=payment_method,
        currency="GHS",
        subtotal=round(float(sale.line_total or 0.0), 2),
        tax_rate=0.0,
        tax_amount=0.0,
        discount_type="none",
        discount_value=0.0,
        discount_amount=0.0,
        total_amount=round(float(sale.line_total or 0.0), 2),
        issue_date=issue_date,
        due_date=None,
        notes=f"Auto-generated from sale #{sale.id}",
    )
    db.session.add(invoice)
    db.session.flush()

    db.session.add(
        InvoiceLineItem(
            invoice_id=invoice.id,
            description=product_name[:300],
            quantity=float(sale.quantity or 0),
            unit_price=round(float(sale.unit_price or 0.0), 2),
            line_total=round(float(sale.line_total or 0.0), 2),
            sort_order=1,
        )
    )

    create_tenant_notification(
        company_id=company_id,
        event_type="invoice.created_from_sale",
        title="Invoice created from sale",
        message=f"Invoice {invoice.invoice_number} was generated from sale #{sale.id}.",
        category="success",
        payload={"invoice_id": invoice.id, "sale_id": sale.id},
    )
    db.session.commit()
    flash("Invoice generated from sale.", "success")
    return redirect(url_for("invoices.view_invoice", invoice_id=invoice.id))


@invoices_bp.route("/new", methods=["GET", "POST"])
@login_required
@tenant_role_required("admin", "manager", "staff")
def create_invoice():
    company_id = _current_company_id()
    if not company_id:
        flash("Session expired. Please log in again.", "error")
        return redirect(url_for("auth.login"))

    company = Company.query.get_or_404(company_id)
    setting = _ensure_invoice_settings(company)

    if request.method == "POST":
        customer_name = (request.form.get("customer_name") or "").strip()
        customer_email = (request.form.get("customer_email") or "").strip()
        billing_address = (request.form.get("billing_address") or "").strip()
        notes = (request.form.get("notes") or "").strip()
        issue_date = _parse_date(request.form.get("issue_date")) or datetime.utcnow()
        due_date = _parse_date(request.form.get("due_date"))
        payment_method = _normalize_payment_method(request.form.get("payment_method"), default="pending")

        tax_rate = max(_parse_float(request.form.get("tax_rate"), 0.0), 0.0)
        discount_type = (request.form.get("discount_type") or "none").strip().lower()
        discount_value = max(_parse_float(request.form.get("discount_value"), 0.0), 0.0)
        action = (request.form.get("action") or "save_draft").strip().lower()
        sale_id_raw = (request.form.get("sale_id") or "").strip()
        sale_id = int(sale_id_raw) if sale_id_raw.isdigit() else None
        linked_sale = None
        if sale_id:
            linked_sale = Sale.query.filter_by(id=sale_id, company_id=company_id).first()
            if not linked_sale:
                flash("Linked sale was not found.", "error")
                return redirect(url_for("invoices.create_invoice"))
            existing_link = Invoice.query.filter_by(company_id=company_id, sale_id=sale_id).first()
            if existing_link:
                flash("An invoice already exists for this sale.", "info")
                return redirect(url_for("invoices.view_invoice", invoice_id=existing_link.id))

        if linked_sale and not customer_name:
            customer_name = "Walk-in Customer"
        if not customer_name:
            flash("Customer name is required.", "error")
            return redirect(url_for("invoices.create_invoice"))

        line_items_payload = _parse_line_items()
        if not line_items_payload:
            flash("Please add at least one valid line item.", "error")
            return redirect(url_for("invoices.create_invoice"))

        subtotal, tax_amount, discount_amount, total_amount = _calculate_totals(
            line_items_payload,
            tax_rate,
            discount_type,
            discount_value,
        )
        status = "paid" if action == "mark_paid" else "draft"
        if status == "paid" and payment_method == "pending":
            flash("Choose a payment method before marking this invoice as paid.", "error")
            return redirect(url_for("invoices.create_invoice"))
        paid_at = datetime.utcnow() if status == "paid" else None

        invoice = Invoice(
            company_id=company_id,
            created_by_user_id=(session.get("user") or {}).get("id"),
            sale_id=sale_id,
            invoice_number=_generate_invoice_number(setting, issue_date),
            customer_name=customer_name,
            customer_email=customer_email or None,
            billing_address=billing_address or None,
            status=status,
            payment_method=payment_method,
            currency="GHS",
            subtotal=subtotal,
            tax_rate=tax_rate,
            tax_amount=tax_amount,
            discount_type=discount_type if discount_type in {"none", "percent", "fixed"} else "none",
            discount_value=discount_value,
            discount_amount=discount_amount,
            total_amount=total_amount,
            issue_date=issue_date,
            due_date=due_date,
            paid_at=paid_at,
            notes=notes or None,
        )
        db.session.add(invoice)
        db.session.flush()

        for row in line_items_payload:
            db.session.add(
                InvoiceLineItem(
                    invoice_id=invoice.id,
                    description=row["description"],
                    quantity=row["quantity"],
                    unit_price=row["unit_price"],
                    line_total=row["line_total"],
                    sort_order=row["sort_order"],
                )
            )

        create_tenant_notification(
            company_id=company_id,
            event_type="invoice.created",
            title="Invoice created",
            message=f"Invoice {invoice.invoice_number} created for {invoice.customer_name}.",
            category="success",
            payload={"invoice_id": invoice.id, "status": invoice.status},
        )
        send_ga4_event(
            "invoice_created",
            params={
                "company_id": company_id,
                "invoice_id": invoice.id,
                "status": invoice.status,
                "line_items": len(line_items_payload),
                "value": total_amount,
            },
        )

        tenant_admin_email = _company_admin_email(company_id)
        if tenant_admin_email:
            send_email_notification(
                tenant_admin_email,
                "Invoice created",
                (
                    f"Invoice {invoice.invoice_number} has been created.\n"
                    f"Customer: {invoice.customer_name}\n"
                    f"Total: {invoice.total_amount:.2f} {invoice.currency}"
                ),
            )
        if status == "paid" and tenant_admin_email:
            send_email_notification(
                tenant_admin_email,
                "Payment received",
                f"Invoice {invoice.invoice_number} has been marked as paid via {invoice.payment_method}.",
            )
            create_tenant_notification(
                company_id=company_id,
                event_type="invoice.paid",
                title="Payment received",
                message=f"Invoice {invoice.invoice_number} was marked as paid.",
                category="info",
                payload={"invoice_id": invoice.id},
            )

        db.session.commit()
        flash("Invoice saved successfully.", "success")
        return redirect(url_for("invoices.view_invoice", invoice_id=invoice.id))

    return render_template(
        "invoices/create.html",
        title="Create Invoice",
        settings=setting,
        today=datetime.utcnow().strftime("%Y-%m-%d"),
        payment_method_choices=PAYMENT_METHOD_CHOICES,
    )


@invoices_bp.route("/<int:invoice_id>", methods=["GET"])
@login_required
def view_invoice(invoice_id):
    company_id = _current_company_id()
    invoice = Invoice.query.filter_by(id=invoice_id, company_id=company_id).first_or_404()
    settings = InvoiceSetting.query.filter_by(company_id=company_id).first()
    return render_template(
        "invoices/detail.html",
        title=f"Invoice {invoice.invoice_number}",
        invoice=invoice,
        settings=settings,
        payment_method_choices=PAYMENT_METHOD_CHOICES,
    )


@invoices_bp.route("/<int:invoice_id>/mark-paid", methods=["POST"])
@login_required
@tenant_role_required("admin", "manager")
def mark_invoice_paid(invoice_id):
    company_id = _current_company_id()
    invoice = Invoice.query.filter_by(id=invoice_id, company_id=company_id).first_or_404()
    payment_method = _normalize_payment_method(
        request.form.get("payment_method"),
        default=(invoice.payment_method or "pending"),
    )
    if payment_method == "pending":
        flash("Please choose a payment method before marking invoice paid.", "error")
        return redirect(url_for("invoices.view_invoice", invoice_id=invoice.id))

    invoice.status = "paid"
    invoice.payment_method = payment_method
    invoice.paid_at = datetime.utcnow()

    create_tenant_notification(
        company_id=company_id,
        event_type="invoice.paid",
        title="Payment received",
        message=f"Invoice {invoice.invoice_number} was marked as paid.",
        category="success",
        payload={"invoice_id": invoice.id},
    )
    send_ga4_event(
        "invoice_paid",
        params={
            "company_id": company_id,
            "invoice_id": invoice.id,
            "value": float(invoice.total_amount or 0.0),
        },
    )
    tenant_admin_email = _company_admin_email(company_id)
    if tenant_admin_email:
        send_email_notification(
            tenant_admin_email,
            "Payment received",
            f"Invoice {invoice.invoice_number} has been marked as paid via {invoice.payment_method}.",
        )

    db.session.commit()
    flash("Invoice marked as paid.", "success")
    return redirect(url_for("invoices.view_invoice", invoice_id=invoice.id))


@invoices_bp.route("/<int:invoice_id>/pdf", methods=["GET"])
@login_required
def download_invoice_pdf(invoice_id):
    company_id = _current_company_id()
    invoice = Invoice.query.filter_by(id=invoice_id, company_id=company_id).first_or_404()
    company = Company.query.get_or_404(company_id)
    settings = InvoiceSetting.query.filter_by(company_id=company_id).first()

    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    y = height - 40

    c.setFont("Helvetica-Bold", 16)
    c.drawString(40, y, company.name or "Company")
    y -= 20

    c.setFont("Helvetica", 10)
    c.drawString(40, y, f"Invoice: {invoice.invoice_number}")
    y -= 14
    c.drawString(40, y, f"Issue Date: {invoice.issue_date.strftime('%Y-%m-%d')}")
    y -= 14
    if invoice.due_date:
        c.drawString(40, y, f"Due Date: {invoice.due_date.strftime('%Y-%m-%d')}")
        y -= 14
    c.drawString(40, y, f"Payment Method: {(invoice.payment_method or 'pending').replace('_', ' ').title()}")
    y -= 14
    if invoice.sale_id:
        c.drawString(40, y, f"Linked Sale: #{invoice.sale_id}")
        y -= 14
    c.drawString(40, y, f"Customer: {invoice.customer_name}")
    y -= 20

    c.setFont("Helvetica-Bold", 10)
    c.drawString(40, y, "Description")
    c.drawString(300, y, "Qty")
    c.drawString(360, y, "Unit Price")
    c.drawString(470, y, "Line Total")
    y -= 12
    c.line(40, y, 550, y)
    y -= 14

    c.setFont("Helvetica", 9)
    for item in invoice.line_items:
        c.drawString(40, y, (item.description or "")[:45])
        c.drawRightString(340, y, f"{float(item.quantity or 0):.2f}")
        c.drawRightString(450, y, f"{float(item.unit_price or 0):.2f}")
        c.drawRightString(550, y, f"{float(item.line_total or 0):.2f}")
        y -= 12
        if y < 100:
            c.showPage()
            y = height - 40
            c.setFont("Helvetica", 9)

    y -= 10
    c.setFont("Helvetica-Bold", 10)
    c.drawRightString(550, y, f"Subtotal: {invoice.subtotal:.2f} {invoice.currency}")
    y -= 14
    c.drawRightString(550, y, f"Tax: {invoice.tax_amount:.2f}")
    y -= 14
    c.drawRightString(550, y, f"Discount: {invoice.discount_amount:.2f}")
    y -= 14
    c.drawRightString(550, y, f"Total: {invoice.total_amount:.2f} {invoice.currency}")
    y -= 20

    footer = ""
    if settings and settings.footer_text:
        footer = settings.footer_text
    elif company.invoice_footer:
        footer = company.invoice_footer
    if footer:
        c.setFont("Helvetica", 9)
        c.drawString(40, y, footer[:120])
        y -= 12

    if settings and settings.payment_instructions:
        c.drawString(40, y, f"Payment instructions: {settings.payment_instructions[:100]}")

    c.showPage()
    c.save()
    buffer.seek(0)

    return send_file(
        buffer,
        mimetype="application/pdf",
        as_attachment=True,
        download_name=f"{invoice.invoice_number}.pdf",
    )


@invoices_bp.route("/<int:invoice_id>/print", methods=["GET"])
@login_required
def print_invoice(invoice_id):
    company_id = _current_company_id()
    invoice = Invoice.query.filter_by(id=invoice_id, company_id=company_id).first_or_404()
    settings = InvoiceSetting.query.filter_by(company_id=company_id).first()
    company = Company.query.get_or_404(company_id)
    return render_template(
        "invoices/print.html",
        title=f"Print {invoice.invoice_number}",
        invoice=invoice,
        settings=settings,
        company=company,
    )


@invoices_bp.route("/settings", methods=["GET", "POST"])
@login_required
@tenant_role_required("admin", "manager")
def invoice_settings():
    company_id = _current_company_id()
    company = Company.query.get_or_404(company_id)
    settings = _ensure_invoice_settings(company)

    if request.method == "POST":
        settings.brand_color = (request.form.get("brand_color") or settings.brand_color or "#5b8cff").strip()
        settings.footer_text = (request.form.get("footer_text") or "").strip() or None
        settings.payment_instructions = (request.form.get("payment_instructions") or "").strip() or None
        settings.prefix = (request.form.get("prefix") or settings.prefix or "INV").strip()[:20]
        settings.numbering_format = (
            (request.form.get("numbering_format") or settings.numbering_format or "{prefix}-{yyyy}-{seq:05d}")
            .strip()[:30]
        )
        settings.next_number = max(_parse_float(request.form.get("next_number"), settings.next_number), 1)

        logo_file = request.files.get("logo")
        if logo_file and logo_file.filename:
            filename = secure_filename(logo_file.filename)
            extension = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
            if extension not in ALLOWED_LOGO_EXTENSIONS:
                flash("Unsupported logo format. Use png/jpg/jpeg/webp.", "error")
                return redirect(url_for("invoices.invoice_settings"))

            base_dir = current_app.config.get("INVOICE_LOGO_UPLOAD_DIR")
            tenant_dir = os.path.join(base_dir, f"company_{company_id}")
            os.makedirs(tenant_dir, exist_ok=True)

            stamped = f"{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{filename}"
            path = os.path.join(tenant_dir, stamped)
            logo_file.save(path)
            settings.logo_path = path.replace("\\", "/")

        company.logo_path = settings.logo_path
        company.brand_color = settings.brand_color
        company.invoice_footer = settings.footer_text
        company.payment_instructions = settings.payment_instructions
        company.invoice_number_prefix = settings.prefix
        company.invoice_next_number = int(settings.next_number)

        db.session.commit()
        flash("Invoice settings updated.", "success")
        return redirect(url_for("invoices.invoice_settings"))

    return render_template(
        "invoices/settings.html",
        title="Invoice Settings",
        settings=settings,
    )
