# app/routes/inventory_routes.py
import csv
import io

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

from .. import db
from ..models import Product
from ..utils.auth import login_required, tenant_role_required

inventory_bp = Blueprint("inventory", __name__)
CSV_TEMPLATE_HEADERS = [
    "sku",
    "name",
    "stock_qty",
    "unit",
    "category",
    "expiry_date",
    "cost_price",
    "selling_price",
]
MAX_IMPORT_ERROR_PREVIEW = 5


def _current_company_id():
    user = session.get("user") or {}
    return user.get("company_id")


def _generate_code_from_name(name: str, company_id: int) -> str:
    """
    Simple helper to generate a unique code for manually-added products.
    Uses the name and appends -2, -3, ... if needed.
    """
    base = name.strip().upper().replace(" ", "-") or "ITEM"
    code = base
    counter = 1

    while Product.query.filter_by(company_id=company_id, code=code).first() is not None:
        counter += 1
        code = f"{base}-{counter}"

    return code


def _parse_non_negative_float(raw_value, field_label: str) -> float:
    try:
        value = float(raw_value or 0)
    except ValueError as exc:
        raise ValueError(f"{field_label} must be a valid number.") from exc

    if value < 0:
        raise ValueError(f"{field_label} cannot be negative.")

    return value


def _parse_non_negative_int(raw_value, field_label: str) -> int:
    raw = str(raw_value or "").strip()
    if not raw:
        return 0

    try:
        number = float(raw)
    except ValueError as exc:
        raise ValueError(f"{field_label} must be a valid number.") from exc

    if number < 0:
        raise ValueError(f"{field_label} cannot be negative.")
    if not number.is_integer():
        raise ValueError(f"{field_label} must be a whole number.")

    return int(number)


def _normalize_csv_header(raw_value: str) -> str:
    return str(raw_value or "").strip().lower().replace("-", "_").replace(" ", "_")


def _csv_value(row: dict, *keys: str) -> str:
    for key in keys:
        value = row.get(key)
        if value is not None and str(value).strip():
            return str(value).strip()
    return ""


def _upsert_product_batch(company_id: int, rows: list) -> tuple[int, int]:
    if not rows:
        return 0, 0

    codes = [row["code"] for row in rows]
    existing_products = (
        Product.query
        .filter(Product.company_id == company_id, Product.code.in_(codes))
        .all()
    )
    existing_by_code = {product.code: product for product in existing_products}

    created = 0
    updated = 0

    for row in rows:
        existing = existing_by_code.get(row["code"])
        if existing:
            existing.name = row["name"]
            existing.quantity = row["quantity"]
            existing.unit = row["unit"]
            existing.category = row["category"]
            existing.expiry_date = row["expiry_date"]
            existing.buying_price = row["buying_price"]
            existing.price = row["price"]
            updated += 1
            continue

        db.session.add(
            Product(
                company_id=company_id,
                code=row["code"],
                name=row["name"],
                quantity=row["quantity"],
                unit=row["unit"],
                category=row["category"],
                expiry_date=row["expiry_date"],
                buying_price=row["buying_price"],
                price=row["price"],
            )
        )
        created += 1

    return created, updated


@inventory_bp.route("/", methods=["GET", "POST"])
@login_required
def inventory_home():
    company_id = _current_company_id()
    if not company_id:
        flash("Session expired. Please log in again.", "error")
        return redirect(url_for("auth.login"))

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
            price = _parse_non_negative_float(request.form.get("price"), "Selling price")
            buying_price = _parse_non_negative_float(
                request.form.get("buying_price"),
                "Cost price",
            )
        except ValueError:
            flash("Please provide valid non-negative prices.", "error")
            return redirect(url_for("inventory.inventory_home"))

        expiry_date = expiry_raw or None  # stored as plain string in the DB

        if not name:
            flash("Product name is required.", "error")
            return redirect(url_for("inventory.inventory_home"))

        # Auto-generate a code for this product
        code = _generate_code_from_name(name, company_id)

        product = Product(
            company_id=company_id,
            code=code,
            name=name,
            quantity=quantity,
            unit=unit,
            category=category,
            expiry_date=expiry_date,
            buying_price=buying_price,
            price=price,
        )

        db.session.add(product)
        db.session.commit()
        flash(f"Product '{name}' added.", "success")
        return redirect(url_for("inventory.inventory_home"))

    # ----- Show current inventory -----
    products = (
        Product.query
        .filter_by(company_id=company_id)
        .order_by(Product.name)
        .all()
    )

    # ✅ No low stock section here anymore
    return render_template(
        "inventory.html",
        products=products,
    )


@inventory_bp.route("/import-template.csv", methods=["GET"])
@login_required
@tenant_role_required("admin", "manager")
def download_inventory_import_template():
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(CSV_TEMPLATE_HEADERS)
    writer.writerow(["MED-001", "Paracetamol 500mg", "120", "TAB", "Analgesic", "2027-12-31", "3.50", "5.00"])
    writer.writerow(["MED-002", "Amoxicillin 250mg", "80", "CAP", "Antibiotic", "", "6.25", "9.50"])

    payload = io.BytesIO(output.getvalue().encode("utf-8"))
    payload.seek(0)

    return send_file(
        payload,
        mimetype="text/csv",
        as_attachment=True,
        download_name="inventory_import_template.csv",
    )


@inventory_bp.route("/import-products", methods=["POST"])
@login_required
@tenant_role_required("admin", "manager")
def import_products_csv():
    company_id = _current_company_id()
    if not company_id:
        flash("Session expired. Please log in again.", "error")
        return redirect(url_for("auth.login"))

    uploaded = request.files.get("products_csv")
    if not uploaded or not uploaded.filename:
        flash("Please select a CSV file to import.", "error")
        return redirect(url_for("inventory.inventory_home"))

    max_file_mb = max(1, int(current_app.config.get("INVENTORY_IMPORT_MAX_FILE_MB", 20)))
    max_rows = max(100, int(current_app.config.get("INVENTORY_IMPORT_MAX_ROWS", 200000)))
    chunk_size = max(100, int(current_app.config.get("INVENTORY_IMPORT_CHUNK_SIZE", 1000)))
    max_bytes = max_file_mb * 1024 * 1024

    raw_csv = uploaded.read(max_bytes + 1)
    if not raw_csv:
        flash("Uploaded file is empty.", "error")
        return redirect(url_for("inventory.inventory_home"))
    if len(raw_csv) > max_bytes:
        flash(f"File is too large. Max allowed size is {max_file_mb}MB.", "error")
        return redirect(url_for("inventory.inventory_home"))

    try:
        decoded_csv = raw_csv.decode("utf-8-sig")
    except UnicodeDecodeError:
        flash("CSV must be UTF-8 encoded.", "error")
        return redirect(url_for("inventory.inventory_home"))

    estimated_rows = max(decoded_csv.count("\n") - 1, 0)
    if estimated_rows > max_rows:
        flash(
            f"CSV has about {estimated_rows:,} rows, but this plan allows {max_rows:,} rows per upload. "
            "Split the file and upload in parts.",
            "error",
        )
        return redirect(url_for("inventory.inventory_home"))

    reader = csv.DictReader(io.StringIO(decoded_csv))
    if not reader.fieldnames:
        flash("CSV header row is missing.", "error")
        return redirect(url_for("inventory.inventory_home"))

    normalized_headers = {_normalize_csv_header(header) for header in reader.fieldnames if header}
    has_code_column = bool(normalized_headers.intersection({"sku", "code", "product_code", "item_code"}))
    has_name_column = bool(normalized_headers.intersection({"name", "product_name", "item_name"}))

    if not has_code_column:
        flash("CSV must include one code column: sku or code.", "error")
        return redirect(url_for("inventory.inventory_home"))
    if not has_name_column:
        flash("CSV must include a product name column (name).", "error")
        return redirect(url_for("inventory.inventory_home"))

    pending_rows = []
    seen_codes = set()
    created_total = 0
    updated_total = 0
    invalid_total = 0
    processed_total = 0
    error_preview = []

    def mark_invalid(row_number: int, reason: str):
        nonlocal invalid_total
        invalid_total += 1
        if len(error_preview) < MAX_IMPORT_ERROR_PREVIEW:
            error_preview.append(f"Row {row_number}: {reason}")

    try:
        for row_number, raw_row in enumerate(reader, start=2):
            normalized_row = {}
            for key, value in raw_row.items():
                normalized_key = _normalize_csv_header(key)
                if normalized_key:
                    normalized_row[normalized_key] = (value or "").strip()

            code = _csv_value(
                normalized_row,
                "sku",
                "code",
                "product_code",
                "item_code",
            ).upper()
            name = _csv_value(normalized_row, "name", "product_name", "item_name")
            quantity_raw = _csv_value(normalized_row, "stock_qty", "quantity", "qty", "stock")
            unit = _csv_value(normalized_row, "unit") or None
            category = _csv_value(normalized_row, "category") or None
            expiry_date = _csv_value(normalized_row, "expiry_date") or None
            cost_raw = _csv_value(
                normalized_row,
                "cost_price",
                "buying_price",
                "purchase_price",
                "unit_cost",
                "cost",
            )
            selling_raw = _csv_value(
                normalized_row,
                "selling_price",
                "price",
                "unit_price",
                "price_ghs",
            )

            if not code:
                mark_invalid(row_number, "Missing sku/code.")
                continue
            if code in seen_codes:
                mark_invalid(row_number, f"Duplicate code '{code}' in upload file.")
                continue
            if not name:
                mark_invalid(row_number, f"Missing name for code '{code}'.")
                continue

            try:
                quantity = _parse_non_negative_int(quantity_raw, "Quantity")
                buying_price = _parse_non_negative_float(cost_raw, "Cost price")
                price = _parse_non_negative_float(selling_raw, "Selling price")
            except ValueError as exc:
                mark_invalid(row_number, str(exc))
                continue

            pending_rows.append(
                {
                    "code": code,
                    "name": name,
                    "quantity": quantity,
                    "unit": unit,
                    "category": category,
                    "expiry_date": expiry_date,
                    "buying_price": buying_price,
                    "price": price,
                }
            )
            seen_codes.add(code)
            processed_total += 1

            if len(pending_rows) >= chunk_size:
                created, updated = _upsert_product_batch(company_id, pending_rows)
                db.session.commit()
                created_total += created
                updated_total += updated
                pending_rows.clear()

        if pending_rows:
            created, updated = _upsert_product_batch(company_id, pending_rows)
            db.session.commit()
            created_total += created
            updated_total += updated

    except Exception:
        db.session.rollback()
        flash("Import failed due to an unexpected error. Please try again.", "error")
        return redirect(url_for("inventory.inventory_home"))

    flash(
        f"Import complete. Processed {processed_total:,} rows: "
        f"{created_total:,} created, {updated_total:,} updated, {invalid_total:,} skipped.",
        "success",
    )
    if invalid_total:
        flash("Some rows were skipped: " + " | ".join(error_preview), "info")

    return redirect(url_for("inventory.inventory_home"))


@inventory_bp.route("/edit/<int:product_id>/", methods=["GET", "POST"])
@login_required
def edit_product(product_id):
    company_id = _current_company_id()
    if not company_id:
        flash("Session expired. Please log in again.", "error")
        return redirect(url_for("auth.login"))

    product = Product.query.filter_by(id=product_id, company_id=company_id).first_or_404()

    if request.method == "POST":
        product.name = request.form.get("name", "").strip() or product.name

        try:
            product.quantity = int(request.form.get("quantity") or 0)
        except ValueError:
            product.quantity = 0

        product.unit = (request.form.get("unit") or "").strip() or None
        product.category = (request.form.get("category") or "").strip() or None

        expiry_raw = (request.form.get("expiry_date") or "").strip()
        product.expiry_date = expiry_raw or None

        try:
            product.price = _parse_non_negative_float(request.form.get("price"), "Selling price")
            product.buying_price = _parse_non_negative_float(
                request.form.get("buying_price"),
                "Cost price",
            )
        except ValueError:
            flash("Please provide valid non-negative prices.", "error")
            return redirect(url_for("inventory.edit_product", product_id=product.id))

        db.session.commit()
        flash("Product updated.", "success")
        return redirect(url_for("inventory.inventory_home"))

    return render_template("edit_products.html", product=product)


@inventory_bp.route("/delete/<int:product_id>/", methods=["POST"])
@login_required
def delete_product(product_id):
    company_id = _current_company_id()
    if not company_id:
        flash("Session expired. Please log in again.", "error")
        return redirect(url_for("auth.login"))

    product = Product.query.filter_by(id=product_id, company_id=company_id).first_or_404()
    db.session.delete(product)
    db.session.commit()
    flash(f"Deleted {product.name}", "info")
    return redirect(url_for("inventory.inventory_home"))
