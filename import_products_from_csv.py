import argparse
import csv

from app import create_app, db
from app.models import Product


def _value(row: dict, *keys: str) -> str:
    for key in keys:
        value = row.get(key)
        if value is not None and str(value).strip():
            return str(value).strip()
    return ""


def _to_float(value, default: float = 0.0) -> float:
    try:
        parsed = float(value if value is not None else default)
    except (TypeError, ValueError):
        return default
    return max(parsed, 0.0)


def _to_int(value, default: int = 0) -> int:
    try:
        parsed = int(float(value if value is not None else default))
    except (TypeError, ValueError):
        return default
    return max(parsed, 0)


def main():
    parser = argparse.ArgumentParser(description="Import products into a tenant/company from CSV.")
    parser.add_argument("--company-id", type=int, required=True, help="Target tenant company ID.")
    parser.add_argument("--csv", default="products.csv", help="CSV file path (default: products.csv).")
    args = parser.parse_args()

    print("\n📦 Importing products from CSV...\n")
    print(f"Target company_id: {args.company_id}")
    print(f"CSV file: {args.csv}\n")

    app = create_app()
    with app.app_context():
        added = 0
        updated = 0
        skipped = 0

        try:
            with open(args.csv, newline="", encoding="utf-8") as csv_file:
                reader = csv.DictReader(csv_file)

                for row_number, row in enumerate(reader, start=2):
                    code = _value(row, "sku", "code", "product_code", "item_code").upper()
                    name = _value(row, "name", "product_name", "item_name")

                    if not code or not name:
                        skipped += 1
                        print(f"⚠️  Skipped row {row_number}: missing sku/code or name.")
                        continue

                    existing = Product.query.filter_by(company_id=args.company_id, code=code).first()

                    quantity = _to_int(_value(row, "stock_qty", "quantity", "qty", "stock"))
                    buying_price = _to_float(
                        _value(row, "cost_price", "buying_price", "purchase_price", "unit_cost", "cost")
                    )
                    price = _to_float(_value(row, "selling_price", "price", "unit_price", "price_ghs"))

                    if existing:
                        existing.name = name
                        existing.category = _value(row, "category") or None
                        existing.unit = _value(row, "unit") or None
                        existing.price = price
                        existing.buying_price = buying_price
                        existing.quantity = quantity
                        existing.expiry_date = _value(row, "expiry_date") or None
                        updated += 1
                        print(f"🔄 Updated: {existing.code} - {existing.name}")
                    else:
                        product = Product(
                            company_id=args.company_id,
                            code=code,
                            name=name,
                            category=_value(row, "category") or None,
                            unit=_value(row, "unit") or None,
                            price=price,
                            buying_price=buying_price,
                            quantity=quantity,
                            expiry_date=_value(row, "expiry_date") or None,
                        )
                        db.session.add(product)
                        added += 1
                        print(f"➕ Added: {product.code} - {product.name}")

                db.session.commit()

        except FileNotFoundError:
            print(f"❌ ERROR: CSV file '{args.csv}' not found.")
            return

        print("\n✅ DONE!")
        print(f"   ➕ Added: {added}")
        print(f"   🔄 Updated: {updated}")
        print(f"   ⚠️  Skipped: {skipped}\n")


if __name__ == "__main__":
    main()
