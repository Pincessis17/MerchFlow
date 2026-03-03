"""Add SaaS subscription, invoice, and platform tables

Revision ID: 17f9d7528d8f
Revises: b9f34d2c1a11
Create Date: 2026-02-22 23:20:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "17f9d7528d8f"
down_revision = "b9f34d2c1a11"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("company", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("status", sa.String(length=20), nullable=False, server_default="trial")
        )
        batch_op.add_column(
            sa.Column("is_suspended", sa.Boolean(), nullable=False, server_default=sa.false())
        )
        batch_op.add_column(sa.Column("suspended_at", sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column("trial_ends_at", sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column("logo_path", sa.String(length=255), nullable=True))
        batch_op.add_column(
            sa.Column("brand_color", sa.String(length=20), nullable=True, server_default="#5b8cff")
        )
        batch_op.add_column(sa.Column("invoice_footer", sa.String(length=500), nullable=True))
        batch_op.add_column(sa.Column("payment_instructions", sa.String(length=500), nullable=True))
        batch_op.add_column(
            sa.Column(
                "invoice_number_prefix",
                sa.String(length=20),
                nullable=True,
                server_default="INV",
            )
        )
        batch_op.add_column(
            sa.Column(
                "invoice_next_number",
                sa.Integer(),
                nullable=False,
                server_default="1",
            )
        )
        batch_op.create_index(batch_op.f("ix_company_status"), ["status"], unique=False)
        batch_op.create_index(batch_op.f("ix_company_is_suspended"), ["is_suspended"], unique=False)

    with op.batch_alter_table("user", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("role", sa.String(length=20), nullable=False, server_default="staff")
        )
        batch_op.create_index(batch_op.f("ix_user_role"), ["role"], unique=False)

    op.create_table(
        "subscription_plan",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("code", sa.String(length=40), nullable=False),
        sa.Column("name", sa.String(length=80), nullable=False),
        sa.Column("monthly_price", sa.Float(), nullable=False),
        sa.Column("yearly_price", sa.Float(), nullable=True),
        sa.Column("max_users", sa.Integer(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint("monthly_price >= 0"),
        sa.CheckConstraint("yearly_price IS NULL OR yearly_price >= 0"),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("subscription_plan", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_subscription_plan_code"), ["code"], unique=True)
        batch_op.create_index(batch_op.f("ix_subscription_plan_created_at"), ["created_at"], unique=False)
        batch_op.create_index(batch_op.f("ix_subscription_plan_is_active"), ["is_active"], unique=False)

    op.create_table(
        "tenant_subscription",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("company_id", sa.Integer(), nullable=False),
        sa.Column("plan_id", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("billing_cycle", sa.String(length=20), nullable=False),
        sa.Column("amount", sa.Float(), nullable=False),
        sa.Column("started_at", sa.DateTime(), nullable=False),
        sa.Column("trial_ends_at", sa.DateTime(), nullable=True),
        sa.Column("current_period_end", sa.DateTime(), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint("amount >= 0"),
        sa.ForeignKeyConstraint(["company_id"], ["company.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["plan_id"], ["subscription_plan.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("tenant_subscription", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_tenant_subscription_company_id"), ["company_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_tenant_subscription_plan_id"), ["plan_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_tenant_subscription_status"), ["status"], unique=False)
        batch_op.create_index(batch_op.f("ix_tenant_subscription_started_at"), ["started_at"], unique=False)
        batch_op.create_index(batch_op.f("ix_tenant_subscription_created_at"), ["created_at"], unique=False)
        batch_op.create_index(batch_op.f("ix_tenant_subscription_updated_at"), ["updated_at"], unique=False)

    op.create_table(
        "platform_notification",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("company_id", sa.Integer(), nullable=True),
        sa.Column("category", sa.String(length=40), nullable=False),
        sa.Column("event_type", sa.String(length=80), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("message", sa.String(length=600), nullable=False),
        sa.Column("payload_json", sa.Text(), nullable=True),
        sa.Column("is_read", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["company_id"], ["company.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("platform_notification", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_platform_notification_company_id"), ["company_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_platform_notification_category"), ["category"], unique=False)
        batch_op.create_index(batch_op.f("ix_platform_notification_event_type"), ["event_type"], unique=False)
        batch_op.create_index(batch_op.f("ix_platform_notification_is_read"), ["is_read"], unique=False)
        batch_op.create_index(batch_op.f("ix_platform_notification_created_at"), ["created_at"], unique=False)

    op.create_table(
        "tenant_notification",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("company_id", sa.Integer(), nullable=False),
        sa.Column("category", sa.String(length=40), nullable=False),
        sa.Column("event_type", sa.String(length=80), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("message", sa.String(length=600), nullable=False),
        sa.Column("payload_json", sa.Text(), nullable=True),
        sa.Column("is_read", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["company_id"], ["company.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("tenant_notification", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_tenant_notification_company_id"), ["company_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_tenant_notification_category"), ["category"], unique=False)
        batch_op.create_index(batch_op.f("ix_tenant_notification_event_type"), ["event_type"], unique=False)
        batch_op.create_index(batch_op.f("ix_tenant_notification_is_read"), ["is_read"], unique=False)
        batch_op.create_index(batch_op.f("ix_tenant_notification_created_at"), ["created_at"], unique=False)

    op.create_table(
        "platform_audit_log",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("actor_user_id", sa.Integer(), nullable=True),
        sa.Column("actor_email", sa.String(length=120), nullable=True),
        sa.Column("action", sa.String(length=120), nullable=False),
        sa.Column("target_type", sa.String(length=80), nullable=False),
        sa.Column("target_id", sa.String(length=120), nullable=True),
        sa.Column("company_id", sa.Integer(), nullable=True),
        sa.Column("details", sa.Text(), nullable=True),
        sa.Column("ip_address", sa.String(length=64), nullable=True),
        sa.Column("user_agent", sa.String(length=400), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["actor_user_id"], ["user.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["company_id"], ["company.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("platform_audit_log", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_platform_audit_log_actor_user_id"), ["actor_user_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_platform_audit_log_actor_email"), ["actor_email"], unique=False)
        batch_op.create_index(batch_op.f("ix_platform_audit_log_action"), ["action"], unique=False)
        batch_op.create_index(batch_op.f("ix_platform_audit_log_target_type"), ["target_type"], unique=False)
        batch_op.create_index(batch_op.f("ix_platform_audit_log_company_id"), ["company_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_platform_audit_log_created_at"), ["created_at"], unique=False)

    op.create_table(
        "login_attempt",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("company_id", sa.Integer(), nullable=True),
        sa.Column("email", sa.String(length=120), nullable=True),
        sa.Column("ip_address", sa.String(length=64), nullable=True),
        sa.Column("user_agent", sa.String(length=400), nullable=True),
        sa.Column("is_success", sa.Boolean(), nullable=False),
        sa.Column("abuse_score", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint("abuse_score >= 0"),
        sa.ForeignKeyConstraint(["company_id"], ["company.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("login_attempt", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_login_attempt_company_id"), ["company_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_login_attempt_email"), ["email"], unique=False)
        batch_op.create_index(batch_op.f("ix_login_attempt_ip_address"), ["ip_address"], unique=False)
        batch_op.create_index(batch_op.f("ix_login_attempt_is_success"), ["is_success"], unique=False)
        batch_op.create_index(batch_op.f("ix_login_attempt_created_at"), ["created_at"], unique=False)

    op.create_table(
        "invoice_setting",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("company_id", sa.Integer(), nullable=False),
        sa.Column("logo_path", sa.String(length=255), nullable=True),
        sa.Column("brand_color", sa.String(length=20), nullable=True),
        sa.Column("footer_text", sa.String(length=500), nullable=True),
        sa.Column("payment_instructions", sa.String(length=500), nullable=True),
        sa.Column("numbering_format", sa.String(length=30), nullable=True),
        sa.Column("prefix", sa.String(length=20), nullable=True),
        sa.Column("next_number", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint("next_number >= 1"),
        sa.ForeignKeyConstraint(["company_id"], ["company.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("company_id"),
    )
    with op.batch_alter_table("invoice_setting", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_invoice_setting_company_id"), ["company_id"], unique=True)
        batch_op.create_index(batch_op.f("ix_invoice_setting_created_at"), ["created_at"], unique=False)
        batch_op.create_index(batch_op.f("ix_invoice_setting_updated_at"), ["updated_at"], unique=False)

    op.create_table(
        "invoice",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("company_id", sa.Integer(), nullable=False),
        sa.Column("created_by_user_id", sa.Integer(), nullable=True),
        sa.Column("invoice_number", sa.String(length=60), nullable=False),
        sa.Column("customer_name", sa.String(length=120), nullable=False),
        sa.Column("customer_email", sa.String(length=120), nullable=True),
        sa.Column("billing_address", sa.String(length=300), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("currency", sa.String(length=10), nullable=False),
        sa.Column("subtotal", sa.Float(), nullable=False),
        sa.Column("tax_rate", sa.Float(), nullable=False),
        sa.Column("tax_amount", sa.Float(), nullable=False),
        sa.Column("discount_type", sa.String(length=20), nullable=False),
        sa.Column("discount_value", sa.Float(), nullable=False),
        sa.Column("discount_amount", sa.Float(), nullable=False),
        sa.Column("total_amount", sa.Float(), nullable=False),
        sa.Column("issue_date", sa.DateTime(), nullable=False),
        sa.Column("due_date", sa.DateTime(), nullable=True),
        sa.Column("paid_at", sa.DateTime(), nullable=True),
        sa.Column("notes", sa.String(length=600), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint("discount_amount >= 0"),
        sa.CheckConstraint("discount_value >= 0"),
        sa.CheckConstraint("subtotal >= 0"),
        sa.CheckConstraint("tax_amount >= 0"),
        sa.CheckConstraint("tax_rate >= 0"),
        sa.CheckConstraint("total_amount >= 0"),
        sa.ForeignKeyConstraint(["company_id"], ["company.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["user.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("company_id", "invoice_number", name="uq_company_invoice_number"),
    )
    with op.batch_alter_table("invoice", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_invoice_company_id"), ["company_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_invoice_created_by_user_id"), ["created_by_user_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_invoice_invoice_number"), ["invoice_number"], unique=False)
        batch_op.create_index(batch_op.f("ix_invoice_status"), ["status"], unique=False)
        batch_op.create_index(batch_op.f("ix_invoice_created_at"), ["created_at"], unique=False)
        batch_op.create_index(batch_op.f("ix_invoice_updated_at"), ["updated_at"], unique=False)

    op.create_table(
        "invoice_line_item",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("invoice_id", sa.Integer(), nullable=False),
        sa.Column("description", sa.String(length=300), nullable=False),
        sa.Column("quantity", sa.Float(), nullable=False),
        sa.Column("unit_price", sa.Float(), nullable=False),
        sa.Column("line_total", sa.Float(), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint("line_total >= 0"),
        sa.CheckConstraint("quantity > 0"),
        sa.CheckConstraint("unit_price >= 0"),
        sa.ForeignKeyConstraint(["invoice_id"], ["invoice.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("invoice_line_item", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_invoice_line_item_invoice_id"), ["invoice_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_invoice_line_item_created_at"), ["created_at"], unique=False)


def downgrade():
    with op.batch_alter_table("invoice_line_item", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_invoice_line_item_created_at"))
        batch_op.drop_index(batch_op.f("ix_invoice_line_item_invoice_id"))
    op.drop_table("invoice_line_item")

    with op.batch_alter_table("tenant_notification", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_tenant_notification_created_at"))
        batch_op.drop_index(batch_op.f("ix_tenant_notification_is_read"))
        batch_op.drop_index(batch_op.f("ix_tenant_notification_event_type"))
        batch_op.drop_index(batch_op.f("ix_tenant_notification_category"))
        batch_op.drop_index(batch_op.f("ix_tenant_notification_company_id"))
    op.drop_table("tenant_notification")

    with op.batch_alter_table("invoice", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_invoice_updated_at"))
        batch_op.drop_index(batch_op.f("ix_invoice_created_at"))
        batch_op.drop_index(batch_op.f("ix_invoice_status"))
        batch_op.drop_index(batch_op.f("ix_invoice_invoice_number"))
        batch_op.drop_index(batch_op.f("ix_invoice_created_by_user_id"))
        batch_op.drop_index(batch_op.f("ix_invoice_company_id"))
    op.drop_table("invoice")

    with op.batch_alter_table("invoice_setting", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_invoice_setting_updated_at"))
        batch_op.drop_index(batch_op.f("ix_invoice_setting_created_at"))
        batch_op.drop_index(batch_op.f("ix_invoice_setting_company_id"))
    op.drop_table("invoice_setting")

    with op.batch_alter_table("login_attempt", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_login_attempt_created_at"))
        batch_op.drop_index(batch_op.f("ix_login_attempt_is_success"))
        batch_op.drop_index(batch_op.f("ix_login_attempt_ip_address"))
        batch_op.drop_index(batch_op.f("ix_login_attempt_email"))
        batch_op.drop_index(batch_op.f("ix_login_attempt_company_id"))
    op.drop_table("login_attempt")

    with op.batch_alter_table("platform_audit_log", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_platform_audit_log_created_at"))
        batch_op.drop_index(batch_op.f("ix_platform_audit_log_company_id"))
        batch_op.drop_index(batch_op.f("ix_platform_audit_log_target_type"))
        batch_op.drop_index(batch_op.f("ix_platform_audit_log_action"))
        batch_op.drop_index(batch_op.f("ix_platform_audit_log_actor_email"))
        batch_op.drop_index(batch_op.f("ix_platform_audit_log_actor_user_id"))
    op.drop_table("platform_audit_log")

    with op.batch_alter_table("platform_notification", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_platform_notification_created_at"))
        batch_op.drop_index(batch_op.f("ix_platform_notification_is_read"))
        batch_op.drop_index(batch_op.f("ix_platform_notification_event_type"))
        batch_op.drop_index(batch_op.f("ix_platform_notification_category"))
        batch_op.drop_index(batch_op.f("ix_platform_notification_company_id"))
    op.drop_table("platform_notification")

    with op.batch_alter_table("tenant_subscription", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_tenant_subscription_updated_at"))
        batch_op.drop_index(batch_op.f("ix_tenant_subscription_created_at"))
        batch_op.drop_index(batch_op.f("ix_tenant_subscription_started_at"))
        batch_op.drop_index(batch_op.f("ix_tenant_subscription_status"))
        batch_op.drop_index(batch_op.f("ix_tenant_subscription_plan_id"))
        batch_op.drop_index(batch_op.f("ix_tenant_subscription_company_id"))
    op.drop_table("tenant_subscription")

    with op.batch_alter_table("subscription_plan", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_subscription_plan_is_active"))
        batch_op.drop_index(batch_op.f("ix_subscription_plan_created_at"))
        batch_op.drop_index(batch_op.f("ix_subscription_plan_code"))
    op.drop_table("subscription_plan")

    with op.batch_alter_table("user", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_user_role"))
        batch_op.drop_column("role")

    with op.batch_alter_table("company", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_company_is_suspended"))
        batch_op.drop_index(batch_op.f("ix_company_status"))
        batch_op.drop_column("invoice_next_number")
        batch_op.drop_column("invoice_number_prefix")
        batch_op.drop_column("payment_instructions")
        batch_op.drop_column("invoice_footer")
        batch_op.drop_column("brand_color")
        batch_op.drop_column("logo_path")
        batch_op.drop_column("trial_ends_at")
        batch_op.drop_column("suspended_at")
        batch_op.drop_column("is_suspended")
        batch_op.drop_column("status")
