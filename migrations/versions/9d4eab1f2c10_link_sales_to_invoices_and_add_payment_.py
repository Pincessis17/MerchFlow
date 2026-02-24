"""Link sales to invoices and add payment method

Revision ID: 9d4eab1f2c10
Revises: 5c4c3b7a9d21
Create Date: 2026-02-24 00:20:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "9d4eab1f2c10"
down_revision = "5c4c3b7a9d21"
branch_labels = None
depends_on = None


def _column_names(inspector, table_name: str):
    return {column["name"] for column in inspector.get_columns(table_name)}


def _index_names(inspector, table_name: str):
    return {index["name"] for index in inspector.get_indexes(table_name)}


def _unique_constraint_names(inspector, table_name: str):
    return {constraint["name"] for constraint in inspector.get_unique_constraints(table_name)}


def _has_sale_fk(inspector, table_name: str):
    for fk in inspector.get_foreign_keys(table_name):
        constrained = fk.get("constrained_columns") or []
        referred = fk.get("referred_table")
        if constrained == ["sale_id"] and referred == "sale":
            return True
    return False


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = _column_names(inspector, "invoice")

    with op.batch_alter_table("invoice", schema=None) as batch_op:
        if "sale_id" not in columns:
            batch_op.add_column(sa.Column("sale_id", sa.Integer(), nullable=True))
        if "payment_method" not in columns:
            batch_op.add_column(
                sa.Column(
                    "payment_method",
                    sa.String(length=40),
                    nullable=False,
                    server_default="pending",
                )
            )

    inspector = sa.inspect(bind)
    indexes = _index_names(inspector, "invoice")
    unique_constraints = _unique_constraint_names(inspector, "invoice")
    has_sale_fk = _has_sale_fk(inspector, "invoice")

    with op.batch_alter_table("invoice", schema=None) as batch_op:
        if "ix_invoice_sale_id" not in indexes:
            batch_op.create_index(batch_op.f("ix_invoice_sale_id"), ["sale_id"], unique=False)
        if "ix_invoice_payment_method" not in indexes:
            batch_op.create_index(batch_op.f("ix_invoice_payment_method"), ["payment_method"], unique=False)
        if "uq_invoice_sale_id" not in unique_constraints:
            batch_op.create_unique_constraint("uq_invoice_sale_id", ["sale_id"])
        if not has_sale_fk:
            batch_op.create_foreign_key(
                "fk_invoice_sale_id_sale",
                "sale",
                ["sale_id"],
                ["id"],
                ondelete="SET NULL",
            )


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = _column_names(inspector, "invoice")
    indexes = _index_names(inspector, "invoice")
    unique_constraints = _unique_constraint_names(inspector, "invoice")
    has_sale_fk = _has_sale_fk(inspector, "invoice")

    with op.batch_alter_table("invoice", schema=None) as batch_op:
        if has_sale_fk:
            batch_op.drop_constraint("fk_invoice_sale_id_sale", type_="foreignkey")
        if "uq_invoice_sale_id" in unique_constraints:
            batch_op.drop_constraint("uq_invoice_sale_id", type_="unique")
        if "ix_invoice_payment_method" in indexes:
            batch_op.drop_index(batch_op.f("ix_invoice_payment_method"))
        if "ix_invoice_sale_id" in indexes:
            batch_op.drop_index(batch_op.f("ix_invoice_sale_id"))
        if "payment_method" in columns:
            batch_op.drop_column("payment_method")
        if "sale_id" in columns:
            batch_op.drop_column("sale_id")
