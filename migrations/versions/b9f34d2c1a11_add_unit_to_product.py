"""Add unit column to product

Revision ID: b9f34d2c1a11
Revises: 06d96d440c87
Create Date: 2026-02-22 22:40:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "b9f34d2c1a11"
down_revision = "06d96d440c87"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("product", schema=None) as batch_op:
        batch_op.add_column(sa.Column("unit", sa.String(length=40), nullable=True))


def downgrade():
    with op.batch_alter_table("product", schema=None) as batch_op:
        batch_op.drop_column("unit")
