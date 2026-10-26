"""initial schema: users, transactions, rule_hits

Revision ID: 0001
Revises:
Create Date: 2026-10-26
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("full_name", sa.String(255), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.create_table(
        "transactions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("merchant", sa.String(255), nullable=False),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("amount_ils", sa.Numeric(14, 2), nullable=False),
        sa.Column("category", sa.String(50), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("risk_score", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index("ix_transactions_user_occurred", "transactions", ["user_id", "occurred_at"])

    op.create_table(
        "rule_hits",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "transaction_id",
            sa.Integer(),
            sa.ForeignKey("transactions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("rule_code", sa.String(50), nullable=False),
        sa.Column("reason", sa.String(255), nullable=False),
        sa.Column("score", sa.Integer(), nullable=False),
    )
    op.create_index("ix_rule_hits_transaction_id", "rule_hits", ["transaction_id"])


def downgrade() -> None:
    op.drop_table("rule_hits")
    op.drop_table("transactions")
    op.drop_table("users")
