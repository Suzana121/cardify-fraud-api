from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Transaction, TransactionStatus

VELOCITY_WINDOW = timedelta(minutes=10)


@dataclass(frozen=True)
class TransactionInput:
    """The incoming transaction, already converted to ILS."""

    merchant: str
    amount_ils: Decimal
    currency: str
    category: str
    occurred_at: datetime


@dataclass(frozen=True)
class UserContext:
    """What we know about the user's past behaviour, relative to one incoming transaction."""

    history_count: int
    median_amount_ils: Decimal | None
    merchant_seen_before: bool
    category_count: int
    recent_count: int  # earlier transactions inside the velocity window


def build_user_context(db: Session, user_id: int, txn: TransactionInput) -> UserContext:
    # Transactions the user confirmed as fraud must not shape their "normal" profile.
    profile = (
        select(Transaction)
        .where(
            Transaction.user_id == user_id,
            Transaction.status != TransactionStatus.REVIEWED_FRAUD,
        )
        .subquery()
    )

    count, median = db.execute(
        select(
            func.count(),
            func.percentile_cont(0.5).within_group(profile.c.amount_ils),
        ).select_from(profile)
    ).one()

    merchant_seen = db.scalar(
        select(func.count())
        .select_from(profile)
        .where(func.lower(profile.c.merchant) == txn.merchant.strip().lower())
    )
    category_count = db.scalar(
        select(func.count()).select_from(profile).where(profile.c.category == txn.category)
    )
    recent_count = db.scalar(
        select(func.count())
        .select_from(Transaction)
        .where(
            Transaction.user_id == user_id,
            Transaction.occurred_at > txn.occurred_at - VELOCITY_WINDOW,
            Transaction.occurred_at <= txn.occurred_at,
        )
    )

    return UserContext(
        history_count=count,
        median_amount_ils=Decimal(str(median)) if median is not None else None,
        merchant_seen_before=bool(merchant_seen),
        category_count=category_count or 0,
        recent_count=recent_count or 0,
    )
