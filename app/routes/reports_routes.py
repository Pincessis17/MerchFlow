# app/routes/reports_routes.py
from datetime import datetime, date, time

from flask import Blueprint, flash, render_template, request, send_file, redirect, session, url_for
from sqlalchemy import func
import io

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet

from ..models import Sale, Product
from ..utils.auth import login_required

reports_bp = Blueprint("reports", __name__, url_prefix="/reports")


def _parse_date(date_str: str, fallback: date) -> date:
    """Parse YYYY-MM-DD safely."""
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").date()
    except Exception:
        return fallback


def _build_reports_pdf(
    start_date: date,
    end_date: date,
    total_sales_count: int,
    total_items_sold: int,
    total_amount: float,
    top_products: list,
    sales_by_day: list,
    sales_by_category: list,
) -> bytes:
    """Create a PDF report and return the bytes."""
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=36,
        rightMargin=36,
        topMargin=36,
        bottomMargin=36,
        title="Sales Report",
    )

    styles = getSampleStyleSheet()
    story = []

    # Title
    story.append(Paragraph("Sales Report", styles["Title"]))
    story.append(Paragraph(
        f"Period: {start_date.strftime('%Y-%m-%d')} → {end_date.strftime('%Y-%m-%d')}",
        styles["Normal"]
    ))
    story.append(Spacer(1, 12))

    # Summary
    story.append(Paragraph("Summary", styles["Heading2"]))
    summary_data = [
        ["Total number of sales", str(total_sales_count)],
        ["Total items sold", str(total_items_sold)],
        ["Total amount (GHS)", f"{total_amount:.2f}"],
    ]
    summary_table = Table(summary_data, colWidths=[250, 200])
    summary_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.whitesmoke),
        ("TEXTCOLOR", (0, 0), (-1, -1), colors.black),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ROWBACKGROUNDS", (0, 0), (-1, -1), [colors.white, colors.whitesmoke]),
    ]))
    story.append(summary_table)
    story.append(Spacer(1, 16))

    # Top Products
    story.append(Paragraph("Top Products (by quantity)", styles["Heading2"]))
    if top_products:
        tp_data = [["Product", "Qty Sold"]]
        for name, qty in top_products:
            tp_data.append([str(name), str(qty)])

        tp_table = Table(tp_data, colWidths=[350, 100])
        tp_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
            ("FONTSIZE", (0, 0), (-1, -1), 10),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ]))
        story.append(tp_table)
    else:
        story.append(Paragraph("No sales in this period.", styles["Normal"]))
    story.append(Spacer(1, 16))

    # Sales by Day
    story.append(Paragraph("Sales by Day", styles["Heading2"]))
    if sales_by_day:
        day_data = [["Date", "Total Amount (GHS)", "Items Sold"]]
        for day_obj, stats in sales_by_day:
            day_data.append([
                day_obj.strftime("%Y-%m-%d"),
                f"{float(stats['amount']):.2f}",
                str(int(stats["items"]))
            ])

        day_table = Table(day_data, colWidths=[120, 160, 120])
        day_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
            ("FONTSIZE", (0, 0), (-1, -1), 10),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ]))
        story.append(day_table)
    else:
        story.append(Paragraph("No sales in this period.", styles["Normal"]))
    story.append(Spacer(1, 16))

    # Sales by Category
    story.append(Paragraph("Sales by Category", styles["Heading2"]))
    if sales_by_category:
        cat_data = [["Category", "Total Amount (GHS)", "Items Sold"]]
        for cat, stats in sales_by_category:
            cat_data.append([
                str(cat),
                f"{float(stats['amount']):.2f}",
                str(int(stats["items"]))
            ])

        cat_table = Table(cat_data, colWidths=[200, 160, 120])
        cat_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
            ("FONTSIZE", (0, 0), (-1, -1), 10),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ]))
        story.append(cat_table)
    else:
        story.append(Paragraph("No sales in this period.", styles["Normal"]))

    doc.build(story)
    pdf_bytes = buf.getvalue()
    buf.close()
    return pdf_bytes


@reports_bp.route("/", methods=["GET"])
@login_required
def reports_home():
    user = session.get("user") or {}
    company_id = user.get("company_id")
    if not company_id:
        flash("Session expired. Please log in again.", "error")
        return redirect(url_for("auth.login"))

    # Default: today
    today = date.today()
    start_date_str = (request.args.get("start_date") or today.strftime("%Y-%m-%d")).strip()
    end_date_str = (request.args.get("end_date") or today.strftime("%Y-%m-%d")).strip()

    # Parse dates
    start_date = _parse_date(start_date_str, today)
    end_date = _parse_date(end_date_str, today)

    # Ensure end >= start
    if end_date < start_date:
        end_date = start_date

    start_dt = datetime.combine(start_date, time.min)
    end_dt = datetime.combine(end_date, time.max)

    # Pull sales
    sales = (
        Sale.query.filter(
            Sale.company_id == company_id,
            Sale.created_at >= start_dt,
            Sale.created_at <= end_dt,
        )
        .order_by(Sale.created_at.desc())
        .all()
    )

    total_sales_count = len(sales)
    total_items_sold = sum(int(s.quantity or 0) for s in sales)
    total_amount = sum(float(s.line_total or 0) for s in sales)

    # Top products
    product_qty = {}
    for s in sales:
        name = s.product.name if s.product else "Unknown"
        product_qty[name] = product_qty.get(name, 0) + int(s.quantity or 0)
    top_products = sorted(product_qty.items(), key=lambda x: x[1], reverse=True)[:10]

    # Sales by Day (aggregate)
    day_data = (
        Sale.query.with_entities(
            func.date(Sale.created_at).label("day"),
            func.coalesce(func.sum(Sale.line_total), 0.0).label("amount"),
            func.coalesce(func.sum(Sale.quantity), 0).label("items"),
        )
        .filter(
            Sale.company_id == company_id,
            Sale.created_at >= start_dt,
            Sale.created_at <= end_dt,
        )
        .group_by(func.date(Sale.created_at))
        .order_by(func.date(Sale.created_at).asc())
        .all()
    )

    sales_by_day = []
    for day_str, amount, items in day_data:
        day_obj = _parse_date(str(day_str), today)
        sales_by_day.append((day_obj, {"amount": float(amount), "items": int(items)}))

    # Sales by Category (uses Product.category text)
    cat_data = (
        Sale.query.join(Product, Product.id == Sale.product_id)
        .with_entities(
            func.coalesce(Product.category, "Uncategorized").label("category"),
            func.coalesce(func.sum(Sale.line_total), 0.0).label("amount"),
            func.coalesce(func.sum(Sale.quantity), 0).label("items"),
        )
        .filter(
            Sale.company_id == company_id,
            Sale.created_at >= start_dt,
            Sale.created_at <= end_dt,
        )
        .group_by(func.coalesce(Product.category, "Uncategorized"))
        .order_by(func.sum(Sale.line_total).desc())
        .all()
    )

    sales_by_category = []
    for category, amount, items in cat_data:
        sales_by_category.append((category, {"amount": float(amount), "items": int(items)}))

    return render_template(
        "reports.html",
        title="Reports",
        start_date=start_date,
        end_date=end_date,
        total_sales_count=total_sales_count,
        total_items_sold=total_items_sold,
        total_amount=total_amount,
        top_products=top_products,
        sales_by_day=sales_by_day,
        sales_by_category=sales_by_category,
    )


@reports_bp.route("/download_pdf", methods=["GET"])
@login_required
def download_pdf():
    user = session.get("user") or {}
    company_id = user.get("company_id")
    if not company_id:
        flash("Session expired. Please log in again.", "error")
        return redirect(url_for("auth.login"))

    today = date.today()
    start_date_str = (request.args.get("start_date") or today.strftime("%Y-%m-%d")).strip()
    end_date_str = (request.args.get("end_date") or today.strftime("%Y-%m-%d")).strip()

    start_date = _parse_date(start_date_str, today)
    end_date = _parse_date(end_date_str, today)
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
        .order_by(Sale.created_at.desc())
        .all()
    )

    total_sales_count = len(sales)
    total_items_sold = sum(int(s.quantity or 0) for s in sales)
    total_amount = sum(float(s.line_total or 0) for s in sales)

    product_qty = {}
    for s in sales:
        name = s.product.name if s.product else "Unknown"
        product_qty[name] = product_qty.get(name, 0) + int(s.quantity or 0)
    top_products = sorted(product_qty.items(), key=lambda x: x[1], reverse=True)[:10]

    day_data = (
        Sale.query.with_entities(
            func.date(Sale.created_at).label("day"),
            func.coalesce(func.sum(Sale.line_total), 0.0).label("amount"),
            func.coalesce(func.sum(Sale.quantity), 0).label("items"),
        )
        .filter(
            Sale.company_id == company_id,
            Sale.created_at >= start_dt,
            Sale.created_at <= end_dt,
        )
        .group_by(func.date(Sale.created_at))
        .order_by(func.date(Sale.created_at).asc())
        .all()
    )
    sales_by_day = []
    for day_str, amount, items in day_data:
        day_obj = _parse_date(str(day_str), today)
        sales_by_day.append((day_obj, {"amount": float(amount), "items": int(items)}))

    cat_data = (
        Sale.query.join(Product, Product.id == Sale.product_id)
        .with_entities(
            func.coalesce(Product.category, "Uncategorized").label("category"),
            func.coalesce(func.sum(Sale.line_total), 0.0).label("amount"),
            func.coalesce(func.sum(Sale.quantity), 0).label("items"),
        )
        .filter(
            Sale.company_id == company_id,
            Sale.created_at >= start_dt,
            Sale.created_at <= end_dt,
        )
        .group_by(func.coalesce(Product.category, "Uncategorized"))
        .order_by(func.sum(Sale.line_total).desc())
        .all()
    )
    sales_by_category = []
    for category, amount, items in cat_data:
        sales_by_category.append((category, {"amount": float(amount), "items": int(items)}))

    pdf_bytes = _build_reports_pdf(
        start_date=start_date,
        end_date=end_date,
        total_sales_count=total_sales_count,
        total_items_sold=total_items_sold,
        total_amount=total_amount,
        top_products=top_products,
        sales_by_day=sales_by_day,
        sales_by_category=sales_by_category,
    )

    mem = io.BytesIO(pdf_bytes)
    mem.seek(0)

    filename = f"sales_report_{start_date.strftime('%Y-%m-%d')}_to_{end_date.strftime('%Y-%m-%d')}.pdf"

    return send_file(
        mem,
        mimetype="application/pdf",
        as_attachment=True,
        download_name=filename,
    )
