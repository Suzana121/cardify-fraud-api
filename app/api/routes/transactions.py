from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import func, select

from app.api.deps import CurrentUser, DbSession
from app.models import Transaction, TransactionStatus
from app.schemas.transaction import ReviewIn, TransactionCreate, TransactionOut, TransactionPage
from app.services.transactions import create_and_score

router = APIRouter(prefix="/transactions", tags=["transactions"])


def get_owned_transaction(db: DbSession, user: CurrentUser, transaction_id: int) -> Transaction:
    txn = db.get(Transaction, transaction_id)
    # Same 404 for "doesn't exist" and "not yours" so ids can't be probed.
    if txn is None or txn.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Transaction not found")
    return txn


@router.post("", response_model=TransactionOut, status_code=status.HTTP_201_CREATED)
def create_transaction(body: TransactionCreate, db: DbSession, user: CurrentUser) -> Transaction:
    return create_and_score(db, user, body)


@router.get("", response_model=TransactionPage)
def list_transactions(
    db: DbSession,
    user: CurrentUser,
    status_filter: TransactionStatus | None = Query(default=None, alias="status"),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> TransactionPage:
    query = select(Transaction).where(Transaction.user_id == user.id)
    if status_filter is not None:
        query = query.where(Transaction.status == status_filter)

    total = db.scalar(select(func.count()).select_from(query.subquery()))
    items = db.scalars(
        query.order_by(Transaction.occurred_at.desc(), Transaction.id.desc())
        .limit(limit)
        .offset(offset)
    ).all()
    return TransactionPage(
        items=[TransactionOut.model_validate(t) for t in items],
        total=total or 0,
        limit=limit,
        offset=offset,
    )


@router.get("/{transaction_id}", response_model=TransactionOut)
def get_transaction(transaction_id: int, db: DbSession, user: CurrentUser) -> Transaction:
    return get_owned_transaction(db, user, transaction_id)


@router.patch("/{transaction_id}/review", response_model=TransactionOut)
def review_transaction(
    transaction_id: int, body: ReviewIn, db: DbSession, user: CurrentUser
) -> Transaction:
    """The card holder confirms whether a transaction was really theirs."""
    txn = get_owned_transaction(db, user, transaction_id)
    txn.status = (
        TransactionStatus.REVIEWED_LEGIT
        if body.verdict == "legit"
        else TransactionStatus.REVIEWED_FRAUD
    )
    db.commit()
    db.refresh(txn)
    return txn
