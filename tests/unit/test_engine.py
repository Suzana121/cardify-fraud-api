from decimal import Decimal

from app.fraud.engine import MAX_SCORE, evaluate
from app.models import TransactionStatus
from app.services.currency import to_ils
from tests.unit.test_rules import make_ctx, make_txn

THRESHOLD = 50


def test_normal_transaction_is_approved_with_no_hits():
    decision = evaluate(make_txn(), make_ctx(), THRESHOLD)
    assert decision.status == TransactionStatus.APPROVED
    assert decision.risk_score == 0
    assert decision.hits == []


def test_single_weak_signal_is_not_enough():
    decision = evaluate(make_txn(currency="USD"), make_ctx(), THRESHOLD)
    assert decision.status == TransactionStatus.APPROVED
    assert decision.risk_score == 15


def test_combined_signals_flag_and_are_sorted_by_score():
    txn = make_txn(amount_ils=Decimal("900"), currency="EUR")
    decision = evaluate(txn, make_ctx(merchant_seen_before=False), THRESHOLD)
    assert decision.status == TransactionStatus.FLAGGED
    assert [h.code for h in decision.hits] == [
        "HIGH_AMOUNT_VS_MEDIAN",
        "NEW_MERCHANT",
        "FOREIGN_CURRENCY",
    ]
    assert decision.risk_score == 75


def test_large_foreign_payment_is_flagged_even_for_new_user():
    txn = make_txn(amount_ils=to_ils(Decimal("10000"), "USD"), currency="USD")
    ctx = make_ctx(history_count=0, median_amount_ils=None, merchant_seen_before=False)
    decision = evaluate(txn, ctx, THRESHOLD)
    assert decision.status == TransactionStatus.FLAGGED


def test_score_is_capped():
    txn = make_txn(amount_ils=Decimal("50000"), currency="USD", category="Gambling")
    ctx = make_ctx(merchant_seen_before=False, category_count=0, recent_count=10)
    assert evaluate(txn, ctx, THRESHOLD).risk_score == MAX_SCORE


def test_threshold_is_configurable():
    decision = evaluate(make_txn(currency="USD"), make_ctx(), threshold=10)
    assert decision.status == TransactionStatus.FLAGGED


def test_to_ils_rounds_to_agorot():
    assert to_ils(Decimal("10.005"), "USD") == Decimal("37.02")
    assert to_ils(Decimal("100"), "ILS") == Decimal("100.00")
