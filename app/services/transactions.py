from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.fraud import engine
from app.fraud.context import TransactionInput, build_user_context
from app.models import RuleHit, Transaction, User
from app.schemas.transaction import TransactionCreate
from app.services.currency import to_ils


def create_and_score(db: Session, user: User, body: TransactionCreate) -> Transaction:
    """Score an incoming transaction against the user's history, then store it with the verdict."""
    txn_in = TransactionInput(
        merchant=body.merchant,
        amount_ils=to_ils(body.amount, body.currency),
        currency=body.currency,
        category=body.category,
        occurred_at=body.occurred_at_or_now(),
    )
    ctx = build_user_context(db, user.id, txn_in)
    decision = engine.evaluate(txn_in, ctx, threshold=get_settings().flag_threshold)

    txn = Transaction(
        user_id=user.id,
        merchant=txn_in.merchant,
        amount=body.amount,
        currency=txn_in.currency,
        amount_ils=txn_in.amount_ils,
        category=txn_in.category,
        occurred_at=txn_in.occurred_at,
        risk_score=decision.risk_score,
        status=decision.status,
        rule_hits=[
            RuleHit(rule_code=h.code, reason=h.reason, score=h.score) for h in decision.hits
        ],
    )
    db.add(txn)
    db.commit()
    db.refresh(txn)
    return txn
