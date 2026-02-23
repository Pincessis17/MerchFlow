# app/models.py

from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import CheckConstraint, UniqueConstraint
from . import db


# =====================================================
# COMPANY (Root Tenant Model)
# =====================================================
class Company(db.Model):
    __tablename__ = "company"

    id = db.Column(db.Integer, primary_key=True)

    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120))
    phone = db.Column(db.String(60))
    address = db.Column(db.String(200))

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        nullable=False,
        index=True
    )

    # Relationships
    users = db.relationship("User", back_populates="company", cascade="all, delete-orphan")
    products = db.relationship("Product", back_populates="company", cascade="all, delete-orphan")
    sales = db.relationship("Sale", back_populates="company", cascade="all, delete-orphan")
    suppliers = db.relationship("Supplier", back_populates="company", cascade="all, delete-orphan")
    purchases = db.relationship("Purchase", back_populates="company", cascade="all, delete-orphan")
    expenses = db.relationship("Expense", back_populates="company", cascade="all, delete-orphan")
    feature_access = db.relationship("FeatureAccess", back_populates="company", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Company {self.name}>"



# =====================================================
# USER
# =====================================================
class User(db.Model):
    __tablename__ = "user"

    id = db.Column(db.Integer, primary_key=True)

    company_id = db.Column(
        db.Integer,
        db.ForeignKey("company.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    email = db.Column(db.String(120), nullable=False, index=True)
    name = db.Column(db.String(80), nullable=False, default="User")

    password_hash = db.Column(db.String(255), nullable=False)

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        nullable=False,
        index=True
    )

    company = db.relationship("Company", back_populates="users")

    __table_args__ = (
        UniqueConstraint("company_id", "email", name="uq_company_user_email"),
    )

    def set_password(self, raw_password: str):
        self.password_hash = generate_password_hash(raw_password)

    def check_password(self, raw_password: str) -> bool:
        return check_password_hash(self.password_hash, raw_password)

    def __repr__(self):
        return f"<User {self.email}>"



# =====================================================
# FEATURE ACCESS (Per Company)
# =====================================================
class FeatureAccess(db.Model):
    __tablename__ = "feature_access"

    id = db.Column(db.Integer, primary_key=True)

    company_id = db.Column(
        db.Integer,
        db.ForeignKey("company.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    email = db.Column(db.String(120), nullable=False, index=True)
    feature = db.Column(db.String(50), nullable=False, index=True)
    is_enabled = db.Column(db.Boolean, nullable=False, default=True)

    granted_by = db.Column(db.String(120))

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        nullable=False,
        index=True
    )

    company = db.relationship("Company", back_populates="feature_access")

    __table_args__ = (
        UniqueConstraint("company_id", "email", "feature", name="uq_company_email_feature"),
    )

    def __repr__(self):
        return f"<FeatureAccess {self.email} -> {self.feature}>"



# =====================================================
# PRODUCT
# =====================================================
class Product(db.Model):
    __tablename__ = "product"

    id = db.Column(db.Integer, primary_key=True)

    company_id = db.Column(
        db.Integer,
        db.ForeignKey("company.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    code = db.Column(db.String(80), nullable=False)
    name = db.Column(db.String(120), nullable=False)
    unit = db.Column(db.String(40))
    category = db.Column(db.String(80))

    buying_price = db.Column(db.Float, nullable=False, default=0.0)
    price = db.Column(db.Float, nullable=False, default=0.0)
    quantity = db.Column(db.Integer, nullable=False, default=0)

    expiry_date = db.Column(db.String(20))  # optional

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        nullable=False,
        index=True
    )

    company = db.relationship("Company", back_populates="products")
    sales = db.relationship("Sale", back_populates="product", cascade="all, delete-orphan")
    purchases = db.relationship("Purchase", back_populates="product", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("company_id", "code", name="uq_company_product_code"),
        CheckConstraint("buying_price >= 0"),
        CheckConstraint("price >= 0"),
        CheckConstraint("quantity >= 0"),
    )

    def __repr__(self):
        return f"<Product {self.code} {self.name}>"



# =====================================================
# SALE
# =====================================================
class Sale(db.Model):
    __tablename__ = "sale"

    id = db.Column(db.Integer, primary_key=True)

    company_id = db.Column(
        db.Integer,
        db.ForeignKey("company.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    product_id = db.Column(
        db.Integer,
        db.ForeignKey("product.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    quantity = db.Column(db.Integer, nullable=False)
    unit_price = db.Column(db.Float, nullable=False)
    line_total = db.Column(db.Float, nullable=False)

    buying_price = db.Column(db.Float, nullable=False, default=0.0)
    line_profit = db.Column(db.Float, nullable=False, default=0.0)

    payment_status = db.Column(db.String(20), nullable=False, default="unpaid")

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        nullable=False,
        index=True
    )

    company = db.relationship("Company", back_populates="sales")
    product = db.relationship("Product", back_populates="sales")
    payments = db.relationship("Payment", back_populates="sale", cascade="all, delete-orphan")

    __table_args__ = (
        CheckConstraint("quantity > 0"),
        CheckConstraint("unit_price >= 0"),
        CheckConstraint("line_total >= 0"),
    )

    # Payment helpers
    def total_paid(self):
        return sum(float(p.amount or 0) for p in self.payments)

    def balance_due(self):
        return float(self.line_total or 0) - self.total_paid()

    def update_payment_status(self):
        paid = self.total_paid()
        total = float(self.line_total or 0)

        if paid <= 0:
            self.payment_status = "unpaid"
        elif paid < total:
            self.payment_status = "partial"
        else:
            self.payment_status = "paid"

    def __repr__(self):
        return f"<Sale {self.id}>"



# =====================================================
# PAYMENT
# =====================================================
class Payment(db.Model):
    __tablename__ = "payment"

    id = db.Column(db.Integer, primary_key=True)

    company_id = db.Column(
        db.Integer,
        db.ForeignKey("company.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    sale_id = db.Column(
        db.Integer,
        db.ForeignKey("sale.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    amount = db.Column(db.Float, nullable=False)
    method = db.Column(db.String(50), nullable=False)
    reference = db.Column(db.String(120))

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        nullable=False,
        index=True
    )

    sale = db.relationship("Sale", back_populates="payments")

    __table_args__ = (
        CheckConstraint("amount > 0"),
    )

    def __repr__(self):
        return f"<Payment sale={self.sale_id} amount={self.amount}>"



# =====================================================
# SUPPLIER
# =====================================================
class Supplier(db.Model):
    __tablename__ = "supplier"

    id = db.Column(db.Integer, primary_key=True)

    company_id = db.Column(
        db.Integer,
        db.ForeignKey("company.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    name = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(60))
    email = db.Column(db.String(120))

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        nullable=False,
        index=True
    )

    company = db.relationship("Company", back_populates="suppliers")
    purchases = db.relationship("Purchase", back_populates="supplier", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Supplier {self.name}>"



# =====================================================
# PURCHASE
# =====================================================
class Purchase(db.Model):
    __tablename__ = "purchase"

    id = db.Column(db.Integer, primary_key=True)

    company_id = db.Column(
        db.Integer,
        db.ForeignKey("company.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    supplier_id = db.Column(
        db.Integer,
        db.ForeignKey("supplier.id", ondelete="CASCADE"),
        nullable=False
    )

    product_id = db.Column(
        db.Integer,
        db.ForeignKey("product.id", ondelete="CASCADE"),
        nullable=False
    )

    quantity = db.Column(db.Integer, nullable=False)
    unit_cost = db.Column(db.Float, nullable=False)
    line_total = db.Column(db.Float, nullable=False)

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        nullable=False,
        index=True
    )

    company = db.relationship("Company", back_populates="purchases")
    supplier = db.relationship("Supplier", back_populates="purchases")
    product = db.relationship("Product", back_populates="purchases")

    __table_args__ = (
        CheckConstraint("quantity > 0"),
        CheckConstraint("unit_cost >= 0"),
    )

    def __repr__(self):
        return f"<Purchase {self.id}>"



# =====================================================
# EXPENSE
# =====================================================
class Expense(db.Model):
    __tablename__ = "expense"

    id = db.Column(db.Integer, primary_key=True)

    company_id = db.Column(
        db.Integer,
        db.ForeignKey("company.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    category = db.Column(db.String(80), nullable=False)
    description = db.Column(db.String(200))
    amount = db.Column(db.Float, nullable=False)

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        nullable=False,
        index=True
    )

    company = db.relationship("Company", back_populates="expenses")

    __table_args__ = (
        CheckConstraint("amount >= 0"),
    )

    def __repr__(self):
        return f"<Expense {self.id}>"
