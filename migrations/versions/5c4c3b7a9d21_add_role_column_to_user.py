"""Add role column to user table

Revision ID: 5c4c3b7a9d21
Revises: 17f9d7528d8f
Create Date: 2026-02-23 23:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "5c4c3b7a9d21"
down_revision = "17f9d7528d8f"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_columns = {column["name"] for column in inspector.get_columns("user")}
    existing_indexes = {index["name"] for index in inspector.get_indexes("user")}

    with op.batch_alter_table("user", schema=None) as batch_op:
        if "role" not in existing_columns:
            batch_op.add_column(
                sa.Column("role", sa.String(length=20), nullable=False, server_default="staff")
            )
        if "ix_user_role" not in existing_indexes:
            batch_op.create_index(batch_op.f("ix_user_role"), ["role"], unique=False)


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_columns = {column["name"] for column in inspector.get_columns("user")}
    existing_indexes = {index["name"] for index in inspector.get_indexes("user")}

    with op.batch_alter_table("user", schema=None) as batch_op:
        if "ix_user_role" in existing_indexes:
            batch_op.drop_index(batch_op.f("ix_user_role"))
        if "role" in existing_columns:
            batch_op.drop_column("role")
