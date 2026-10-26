from datetime import UTC, datetime
from decimal import Decimal

import pytest

from app.fraud.context import TransactionInput, UserContext
from app.fraud.rules import (
    MIN_HISTORY,
    ForeignCurrencyRule,
    HighAmountVsMedianRule,
    LargeAbsoluteAmountRule,
    NewMerchantRule,
    RareCategoryRule,
    VelocityRule,
)


def make_txn(**overrides) -> TransactionInput:
    values = {
        "merchant": "Shufersal",
        "amount_ils": Decimal("120.00"),
        "currency": "ILS",
        "category": "Food",
        "occurred_at": datetime(2026, 10, 1, 12, 0, tzinfo=UTC),
    }
    return TransactionInput(**(values | overrides))


def make_ctx(**overrides) -> UserContext:
    values = {
        "history_count": 50,
        "median_amount_ils": Decimal("100.00"),
        "merchant_seen_before": True,
        "category_count": 20,
        "recent_count": 0,
    }
    return UserContext(**(values | overrides))


class TestHighAmountVsMedian:
    rule = HighAmountVsMedianRule()

    def test_fires_above_five_times_median(self):
        hit = self.rule.evaluate(make_txn(amount_ils=Decimal("750")), make_ctx())
        assert hit is not None
        assert hit.code == "HIGH_AMOUNT_VS_MEDIAN"
        assert "7.5x" in hit.reason

    def test_silent_at_exactly_five_times(self):
        assert self.rule.evaluate(make_txn(amount_ils=Decimal("500")), make_ctx()) is None

    def test_silent_without_enough_history(self):
        ctx = make_ctx(history_count=MIN_HISTORY - 1)
        assert self.rule.evaluate(make_txn(amount_ils=Decimal("9999")), ctx) is None

    def test_silent_when_no_median(self):
        ctx = make_ctx(median_amount_ils=None)
        assert self.rule.evaluate(make_txn(amount_ils=Decimal("9999")), ctx) is None


class TestLargeAbsoluteAmount:
    rule = LargeAbsoluteAmountRule()

    def test_fires_above_limit_even_for_new_user(self):
        ctx = make_ctx(history_count=0, median_amount_ils=None)
        assert self.rule.evaluate(make_txn(amount_ils=Decimal("10000.01")), ctx) is not None

    def test_silent_at_limit(self):
        assert self.rule.evaluate(make_txn(amount_ils=Decimal("10000")), make_ctx()) is None


class TestNewMerchant:
    rule = NewMerchantRule()

    def test_fires_for_unknown_merchant(self):
        assert self.rule.evaluate(make_txn(), make_ctx(merchant_seen_before=False)) is not None

    def test_silent_for_known_merchant(self):
        assert self.rule.evaluate(make_txn(), make_ctx()) is None

    def test_silent_on_cold_start(self):
        ctx = make_ctx(history_count=0, merchant_seen_before=False)
        assert self.rule.evaluate(make_txn(), ctx) is None


class TestForeignCurrency:
    rule = ForeignCurrencyRule()

    @pytest.mark.parametrize("currency", ["USD", "EUR", "GBP"])
    def test_fires_for_foreign(self, currency):
        hit = self.rule.evaluate(make_txn(currency=currency), make_ctx())
        assert hit is not None
        assert currency in hit.reason

    def test_silent_for_ils(self):
        assert self.rule.evaluate(make_txn(), make_ctx()) is None


class TestRareCategory:
    rule = RareCategoryRule()

    def test_fires_for_never_seen_category(self):
        hit = self.rule.evaluate(make_txn(category="Gambling"), make_ctx(category_count=0))
        assert hit is not None
        assert "Gambling" in hit.reason

    def test_silent_for_common_category(self):
        assert self.rule.evaluate(make_txn(), make_ctx()) is None

    def test_silent_on_cold_start(self):
        ctx = make_ctx(history_count=0, category_count=0)
        assert self.rule.evaluate(make_txn(), ctx) is None


class TestVelocity:
    rule = VelocityRule()

    def test_fires_on_fifth_transaction_in_window(self):
        hit = self.rule.evaluate(make_txn(), make_ctx(recent_count=4))
        assert hit is not None
        assert hit.reason.startswith("5 transactions")

    def test_silent_on_fourth(self):
        assert self.rule.evaluate(make_txn(), make_ctx(recent_count=3)) is None
