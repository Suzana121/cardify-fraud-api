from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Index, Integer, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base

if TYPE_CHECKING:
    from app.models.user import User


class TransactionStatus(StrEnum):
    APPROVED = "APPROVED"
    FLAGGED = "FLAGGED"
    REVIEWED_LEGIT = "REVIEWED_LEGIT"
    REVIEWED_FRAUD = "REVIEWED_FRAUD"


class Transaction(Base):
    __tablename__ = "transactions"
    __table_args__ = (Index("ix_transactions_user_occurred", "user_id", "occurred_at"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    merchant: Mapped[str] = mapped_column(String(255))
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    currency: Mapped[str] = mapped_column(String(3))
    amount_ils: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    category: Mapped[str] = mapped_column(String(50))
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    risk_score: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(20), default=TransactionStatus.APPROVED)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped["User"] = relationship(back_populates="transactions")
    rule_hits: Mapped[list["RuleHit"]] = relationship(
        back_populates="transaction", cascade="all, delete-orphan", lazy="selectin"
    )


class RuleHit(Base):
    """One rule that fired for a transaction — the human-readable 'why it was flagged'."""

    __tablename__ = "rule_hits"

    id: Mapped[int] = mapped_column(primary_key=True)
    transaction_id: Mapped[int] = mapped_column(
        ForeignKey("transactions.id", ondelete="CASCADE"), index=True
    )
    rule_code: Mapped[str] = mapped_column(String(50))
    reason: Mapped[str] = mapped_column(String(255))
    score: Mapped[int] = mapped_column(Integer)

    transaction: Mapped[Transaction] = relationship(back_populates="rule_hits")
