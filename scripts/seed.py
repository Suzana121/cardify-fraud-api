"""Create a demo user with ~200 realistic transactions (about 5% anomalies).

Every transaction goes through the real scoring pipeline in chronological order,
so the flags you see in the API are produced by the rule engine, not hard-coded.

    python -m scripts.seed
"""

import os
import random
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from sqlalchemy import select

from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models import User
from app.schemas.transaction import TransactionCreate
from app.services.transactions import create_and_score

DEMO_EMAIL = os.environ.get("DEMO_EMAIL", "demo@cardify.dev")
DEMO_PASSWORD = os.environ.get("DEMO_PASSWORD", "demo-pass-123")
N_TRANSACTIONS = 200
ANOMALY_RATE = 0.05

# Same flavour of merchants as the original Cardify synthetic data.
MERCHANTS = {
    "Food": ["שופרסל", "רמי לוי", "יוחננוף", "ארומה", "קפה גרג", "Wolt"],
    "Transport": ["רכבת ישראל", "אגד", "פז", "דלק", "Gett"],
    "Health": ["סופר-פארם", "מכבי", "כללית"],
    "Shopping": ["ZARA", "H&M", "פוקס", "ACE"],
    "Entertainment": ["סינמה סיטי", "Netflix"],
}
SUSPICIOUS = [
    ("CRYPTO EXCHANGE", "Other", "USD"),
    ("ONLINE CASINO PRO", "Entertainment", "EUR"),
    ("INTL MERCHANT 001", "Shopping", "USD"),
    ("MARRIOTT HOTELS", "Travel", "GBP"),
]


def normal_txn(rng: random.Random, when: datetime) -> TransactionCreate:
    category = rng.choice(list(MERCHANTS))
    amount = Decimal(str(round(rng.lognormvariate(4.6, 0.6), 2)))  # median ≈ 100 ILS
    return TransactionCreate(
        merchant=rng.choice(MERCHANTS[category]),
        amount=max(amount, Decimal("5")),
        currency="ILS",
        category=category,
        occurred_at=when,
    )


def anomalous_txn(rng: random.Random, when: datetime) -> TransactionCreate:
    merchant, category, currency = rng.choice(SUSPICIOUS)
    return TransactionCreate(
        merchant=merchant,
        amount=Decimal(str(round(rng.uniform(800, 4000), 2))),
        currency=currency,
        category=category,
        occurred_at=when,
    )


def main() -> None:
    rng = random.Random(42)
    with SessionLocal() as db:
        if db.scalar(select(User).where(User.email == DEMO_EMAIL)):
            print(f"{DEMO_EMAIL} already exists, nothing to do.")
            return

        user = User(
            email=DEMO_EMAIL, hashed_password=hash_password(DEMO_PASSWORD), full_name="Demo"
        )
        db.add(user)
        db.commit()

        start = datetime.now(UTC) - timedelta(days=60)
        times = sorted(
            start + timedelta(minutes=rng.randint(0, 60 * 24 * 60)) for _ in range(N_TRANSACTIONS)
        )
        flagged = 0
        for i, when in enumerate(times):
            # Keep the first 20 clean so the user has a "normal" profile to compare against.
            is_anomaly = i >= 20 and rng.random() < ANOMALY_RATE
            body = anomalous_txn(rng, when) if is_anomaly else normal_txn(rng, when)
            txn = create_and_score(db, user, body)
            flagged += txn.status == "FLAGGED"

        print(f"Created {DEMO_EMAIL} with {N_TRANSACTIONS} transactions, {flagged} flagged.")


if __name__ == "__main__":
    main()
