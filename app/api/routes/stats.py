from fastapi import APIRouter
from sqlalchemy import func, select

from app.api.deps import CurrentUser, DbSession
from app.models import RuleHit, Transaction, TransactionStatus
from app.schemas.transaction import RuleCount, StatsSummary

router = APIRouter(prefix="/stats", tags=["stats"])

# Everything the engine raised an alarm on, whatever the user later decided.
ALERTED = (TransactionStatus.FLAGGED, TransactionStatus.REVIEWED_FRAUD)


@router.get("/summary", response_model=StatsSummary)
def summary(db: DbSession, user: CurrentUser) -> StatsSummary:
    rows = db.execute(
        select(Transaction.status, func.count())
        .where(Transaction.user_id == user.id)
        .group_by(Transaction.status)
    ).all()
    by_status = {s: 0 for s in TransactionStatus} | {TransactionStatus(s): n for s, n in rows}
    total = sum(by_status.values())
    alerted = sum(by_status[s] for s in ALERTED)

    top_rules = db.execute(
        select(RuleHit.rule_code, func.count().label("n"))
        .join(Transaction)
        .where(Transaction.user_id == user.id)
        .group_by(RuleHit.rule_code)
        .order_by(func.count().desc(), RuleHit.rule_code)
        .limit(5)
    ).all()

    return StatsSummary(
        total_transactions=total,
        by_status=by_status,
        flagged_rate=round(alerted / total, 4) if total else 0.0,
        top_rules=[RuleCount(rule_code=code, count=n) for code, n in top_rules],
    )
