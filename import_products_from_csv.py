import csv
from app import create_app, db
from app.models import Product

CSV_FILE = "products.csv"


def main():
    print("\n📦 Importing products from CSV...\n")

    app = create_app()
    with app.app_context():

        added = 0
        updated = 0

        try:
            with open(CSV_FILE, newline="", encoding="utf-8") as f:
                reader = csv.DictReader(f)

                for row in reader:
                    code = row["sku"]

                    # Check if product exists
                    existing = Product.query.filter_by(code=code).first()

                    if existing:
                        # Update existing record
                        existing.name = row["name"]
                        existing.category = row.get("category")
                        existing.unit = row.get("unit")
                        existing.price = float(row.get("price_ghs") or 0)
                        existing.buying_price = float(row.get("price_ghs") or 0)
                        existing.quantity = int(row.get("stock_qty") or 0)
                        existing.expiry_date = row.get("expiry_date")

                        updated += 1
                        print(f"🔄 Updated: {existing.name}")

                    else:
                        # Create new product
                        product = Product(
                            code=row["sku"],
                            name=row["name"],
                            category=row.get("category"),
                            unit=row.get("unit"),
                            price=float(row.get("price_ghs") or 0),
                            buying_price=float(row.get("price_ghs") or 0),
                            quantity=int(row.get("stock_qty") or 0),
                            expiry_date=row.get("expiry_date")
                        )

                        db.session.add(product)
                        added += 1
                        print(f"➕ Added: {product.name}")

                db.session.commit()

        except FileNotFoundError:
            print(f"❌ ERROR: CSV file '{CSV_FILE}' not found.")
            return

        print("\n✅ DONE!")
        print(f"   ➕ Added: {added}")
        print(f"   🔄 Updated: {updated}\n")


if __name__ == "__main__":
    main()
