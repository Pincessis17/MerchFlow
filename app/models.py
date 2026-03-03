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
    status = db.Column(db.String(20), nullable=False, default="trial", index=True)
    is_suspended = db.Column(db.Boolean, nullable=False, default=False, index=True)
    suspended_at = db.Column(db.DateTime)
    trial_ends_at = db.Column(db.DateTime)

    # Tenant branding and invoice preferences
    logo_path = db.Column(db.String(255))
    brand_color = db.Column(db.String(20), default="#5b8cff")
    invoice_footer = db.Column(db.String(500))
    payment_instructions = db.Column(db.String(500))
    invoice_number_prefix = db.Column(db.String(20), default="INV")
    invoice_next_number = db.Column(db.Integer, nullable=False, default=1)

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
    subscriptions = db.relationship(
        "TenantSubscription",
        back_populates="company",
        cascade="all, delete-orphan",
        order_by="TenantSubscription.created_at.desc()",
    )
    invoices = db.relationship("Invoice", back_populates="company", cascade="all, delete-orphan")
    invoice_settings = db.relationship(
        "InvoiceSetting",
        back_populates="company",
        cascade="all, delete-orphan",
        uselist=False,
    )
    tenant_notifications = db.relationship(
        "TenantNotification",
        back_populates="company",
        cascade="all, delete-orphan",
    )

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
    role = db.Column(db.String(20), nullable=False, default="staff", index=True)

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
# CUSTOMER
# =====================================================
class Customer(db.Model):
    __tablename__ = "customer"

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(
        db.Integer,
        db.ForeignKey("company.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
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

    company = db.relationship("Company", backref=db.backref("customers", cascade="all, delete-orphan"))
    sales = db.relationship("Sale", back_populates="customer", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Customer {self.name}>"


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
    customer_id = db.Column(
        db.Integer,
        db.ForeignKey("customer.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    status = db.Column(db.String(20), nullable=False, default="draft")  # draft, invoiced
    subtotal = db.Column(db.Float, nullable=False, default=0.0)
    tax = db.Column(db.Float, nullable=False, default=0.0)
    total_amount = db.Column(db.Float, nullable=False, default=0.0)

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        nullable=False,
        index=True
    )

    company = db.relationship("Company", back_populates="sales")
    customer = db.relationship("Customer", back_populates="sales")
    items = db.relationship("SaleItem", back_populates="sale", cascade="all, delete-orphan")
    invoices = db.relationship("Invoice", back_populates="sale", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Sale {self.id}>"


# =====================================================
# SALE ITEM
# =====================================================
class SaleItem(db.Model):
    __tablename__ = "sale_item"

    id = db.Column(db.Integer, primary_key=True)
    sale_id = db.Column(
        db.Integer,
        db.ForeignKey("sale.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    product_name = db.Column(db.String(120), nullable=False)
    quantity = db.Column(db.Integer, nullable=False, default=1)
    unit_price = db.Column(db.Float, nullable=False, default=0.0)
    line_total = db.Column(db.Float, nullable=False, default=0.0)

    sale = db.relationship("Sale", back_populates="items")

    def __repr__(self):
        return f"<SaleItem {self.product_name}>"



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


# =====================================================
# SUBSCRIPTION PLAN (Platform Level)
# =====================================================
class SubscriptionPlan(db.Model):
    __tablename__ = "subscription_plan"

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(40), nullable=False, unique=True, index=True)
    name = db.Column(db.String(80), nullable=False)
    monthly_price = db.Column(db.Float, nullable=False, default=0.0)
    yearly_price = db.Column(db.Float)
    max_users = db.Column(db.Integer)
    is_active = db.Column(db.Boolean, nullable=False, default=True, index=True)

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        nullable=False,
        index=True,
    )

    subscriptions = db.relationship("TenantSubscription", back_populates="plan")

    __table_args__ = (
        CheckConstraint("monthly_price >= 0"),
        CheckConstraint("yearly_price IS NULL OR yearly_price >= 0"),
    )

    def __repr__(self):
        return f"<SubscriptionPlan {self.code}>"


# =====================================================
# TENANT SUBSCRIPTION
# =====================================================
class TenantSubscription(db.Model):
    __tablename__ = "tenant_subscription"

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(
        db.Integer,
        db.ForeignKey("company.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    plan_id = db.Column(
        db.Integer,
        db.ForeignKey("subscription_plan.id", ondelete="SET NULL"),
        index=True,
    )

    status = db.Column(db.String(20), nullable=False, default="trial", index=True)
    billing_cycle = db.Column(db.String(20), nullable=False, default="monthly")

    amount = db.Column(db.Float, nullable=False, default=0.0)
    started_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    trial_ends_at = db.Column(db.DateTime)
    current_period_end = db.Column(db.DateTime)
    cancelled_at = db.Column(db.DateTime)

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        nullable=False,
        index=True,
    )
    updated_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
        index=True,
    )

    company = db.relationship("Company", back_populates="subscriptions")
    plan = db.relationship("SubscriptionPlan", back_populates="subscriptions")

    __table_args__ = (
        CheckConstraint("amount >= 0"),
    )

    def __repr__(self):
        return f"<TenantSubscription company={self.company_id} status={self.status}>"


# =====================================================
# PLATFORM NOTIFICATION
# =====================================================
class PlatformNotification(db.Model):
    __tablename__ = "platform_notification"

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(
        db.Integer,
        db.ForeignKey("company.id", ondelete="SET NULL"),
        index=True,
    )
    category = db.Column(db.String(40), nullable=False, default="info", index=True)
    event_type = db.Column(db.String(80), nullable=False, index=True)
    title = db.Column(db.String(200), nullable=False)
    message = db.Column(db.String(600), nullable=False)
    payload_json = db.Column(db.Text)
    is_read = db.Column(db.Boolean, nullable=False, default=False, index=True)

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        nullable=False,
        index=True,
    )

    def __repr__(self):
        return f"<PlatformNotification {self.event_type}>"


# =====================================================
# TENANT NOTIFICATION
# =====================================================
class TenantNotification(db.Model):
    __tablename__ = "tenant_notification"

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(
        db.Integer,
        db.ForeignKey("company.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    category = db.Column(db.String(40), nullable=False, default="info", index=True)
    event_type = db.Column(db.String(80), nullable=False, index=True)
    title = db.Column(db.String(200), nullable=False)
    message = db.Column(db.String(600), nullable=False)
    payload_json = db.Column(db.Text)
    is_read = db.Column(db.Boolean, nullable=False, default=False, index=True)

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        nullable=False,
        index=True,
    )

    company = db.relationship("Company", back_populates="tenant_notifications")

    def __repr__(self):
        return f"<TenantNotification {self.event_type}>"


# =====================================================
# PLATFORM AUDIT LOG
# =====================================================
class PlatformAuditLog(db.Model):
    __tablename__ = "platform_audit_log"

    id = db.Column(db.Integer, primary_key=True)
    actor_user_id = db.Column(
        db.Integer,
        db.ForeignKey("user.id", ondelete="SET NULL"),
        index=True,
    )
    actor_email = db.Column(db.String(120), index=True)
    action = db.Column(db.String(120), nullable=False, index=True)
    target_type = db.Column(db.String(80), nullable=False, index=True)
    target_id = db.Column(db.String(120))
    company_id = db.Column(
        db.Integer,
        db.ForeignKey("company.id", ondelete="SET NULL"),
        index=True,
    )
    details = db.Column(db.Text)
    ip_address = db.Column(db.String(64))
    user_agent = db.Column(db.String(400))

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        nullable=False,
        index=True,
    )

    def __repr__(self):
        return f"<PlatformAuditLog {self.action}>"


# =====================================================
# LOGIN ATTEMPT LOG
# =====================================================
class LoginAttempt(db.Model):
    __tablename__ = "login_attempt"

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(
        db.Integer,
        db.ForeignKey("company.id", ondelete="SET NULL"),
        index=True,
    )
    email = db.Column(db.String(120), index=True)
    ip_address = db.Column(db.String(64), index=True)
    user_agent = db.Column(db.String(400))
    is_success = db.Column(db.Boolean, nullable=False, default=False, index=True)
    abuse_score = db.Column(db.Integer, nullable=False, default=0)

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        nullable=False,
        index=True,
    )

    __table_args__ = (
        CheckConstraint("abuse_score >= 0"),
    )

    def __repr__(self):
        return f"<LoginAttempt {self.email} success={self.is_success}>"


# =====================================================
# INVOICE SETTINGS (Tenant Level)
# =====================================================
class InvoiceSetting(db.Model):
    __tablename__ = "invoice_setting"

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(
        db.Integer,
        db.ForeignKey("company.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    logo_path = db.Column(db.String(255))
    brand_color = db.Column(db.String(20), default="#5b8cff")
    footer_text = db.Column(db.String(500))
    payment_instructions = db.Column(db.String(500))
    numbering_format = db.Column(db.String(30), default="{prefix}-{yyyy}-{seq:05d}")
    prefix = db.Column(db.String(20), default="INV")
    next_number = db.Column(db.Integer, nullable=False, default=1)

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        nullable=False,
        index=True,
    )
    updated_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
        index=True,
    )

    company = db.relationship("Company", back_populates="invoice_settings")

    __table_args__ = (
        CheckConstraint("next_number >= 1"),
    )

    def __repr__(self):
        return f"<InvoiceSetting company={self.company_id}>"


# =====================================================
# INVOICE (Tenant Level)
# =====================================================
class Invoice(db.Model):
    __tablename__ = "invoice"

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

    invoice_number = db.Column(db.String(60), nullable=False, index=True)
    total_amount = db.Column(db.Float, nullable=False, default=0.0)
    amount_paid = db.Column(db.Float, nullable=False, default=0.0)
    status = db.Column(db.String(20), nullable=False, default="unpaid")  # unpaid, partial, paid
    due_date = db.Column(db.DateTime)

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        nullable=False,
        index=True
    )

    company = db.relationship("Company", back_populates="invoices")
    sale = db.relationship("Sale", back_populates="invoices")
    payments = db.relationship("Payment", back_populates="invoice", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("company_id", "invoice_number", name="uq_company_invoice_number_new"),
    )

    def __repr__(self):
        return f"<Invoice {self.invoice_number}>"


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
    invoice_id = db.Column(
        db.Integer,
        db.ForeignKey("invoice.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    amount = db.Column(db.Float, nullable=False)
    payment_method = db.Column(db.String(50), nullable=False)  # cash, momo, card, bank

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        nullable=False,
        index=True
    )

    invoice = db.relationship("Invoice", back_populates="payments")

    __table_args__ = (
        CheckConstraint("amount > 0"),
    )

    def __repr__(self):
        return f"<Payment invoice={self.invoice_id} amount={self.amount}>"


# =====================================================
# TENANT (Property Management)
# =====================================================
class Tenant(db.Model):
    __tablename__ = 'tenant'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120))
    phone = db.Column(db.String(60))
    property_address = db.Column(db.String(200))
    lease_status = db.Column(db.String(20), default='active', index=True)
    payment_history = db.Column(db.String(100), default='ok,ok,ok,ok')
    end_date = db.Column(db.DateTime, index=True)
    monthly_rent = db.Column(db.Float, default=0.0)

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)

    def __repr__(self):
        return f'<Tenant {self.name}>'
