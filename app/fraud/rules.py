"""Fraud rules.

Each rule looks at one incoming transaction plus the user's context and either returns a
RuleResult (it fired, with a score and a human-readable reason) or None.
Rules are pure: no database access, so they are trivial to unit-test.
"""

from dataclasses import dataclass
from decimal import Decimal

from app.fraud.context import TransactionInput, UserContext
from app.services.currency import HOME_CURRENCY

# Rules that compare against "normal behaviour" stay silent until we have this much history.
MIN_HISTORY = 5


@dataclass(frozen=True)
class RuleResult:
    code: str
    reason: str
    score: int


class Rule:
    code: str
    score: int

    def evaluate(self, txn: TransactionInput, ctx: UserContext) -> RuleResult | None:
        raise NotImplementedError

    def hit(self, reason: str) -> RuleResult:
        return RuleResult(code=self.code, reason=reason, score=self.score)


class HighAmountVsMedianRule(Rule):
    code = "HIGH_AMOUNT_VS_MEDIAN"
    score = 40

    def __init__(self, multiplier: Decimal = Decimal(5)):
        self.multiplier = multiplier

    def evaluate(self, txn, ctx):
        median = ctx.median_amount_ils
        if ctx.history_count < MIN_HISTORY or not median:
            return None
        if txn.amount_ils > median * self.multiplier:
            ratio = (txn.amount_ils / median).quantize(Decimal("0.1"))
            return self.hit(f"Amount is {ratio}x your typical (median) spend")
        return None


class LargeAbsoluteAmountRule(Rule):
    code = "LARGE_ABSOLUTE_AMOUNT"
    score = 40

    def __init__(self, limit_ils: Decimal = Decimal(10_000)):
        self.limit_ils = limit_ils

    def evaluate(self, txn, ctx):
        if txn.amount_ils > self.limit_ils:
            return self.hit(f"Amount exceeds {self.limit_ils:,} ILS")
        return None


class NewMerchantRule(Rule):
    code = "NEW_MERCHANT"
    score = 20

    def evaluate(self, txn, ctx):
        if ctx.history_count >= MIN_HISTORY and not ctx.merchant_seen_before:
            return self.hit("First transaction at this merchant")
        return None


class ForeignCurrencyRule(Rule):
    code = "FOREIGN_CURRENCY"
    score = 15

    def evaluate(self, txn, ctx):
        if txn.currency != HOME_CURRENCY:
            return self.hit(f"Transaction in foreign currency ({txn.currency})")
        return None


class RareCategoryRule(Rule):
    code = "RARE_CATEGORY"
    score = 10

    def __init__(self, min_frequency: float = 0.01):
        self.min_frequency = min_frequency

    def evaluate(self, txn, ctx):
        if ctx.history_count < MIN_HISTORY:
            return None
        if ctx.category_count / ctx.history_count < self.min_frequency:
            return self.hit(f"Rare spending category for you ({txn.category})")
        return None


class VelocityRule(Rule):
    code = "VELOCITY"
    score = 50

    def __init__(self, max_in_window: int = 5):
        self.max_in_window = max_in_window

    def evaluate(self, txn, ctx):
        total = ctx.recent_count + 1  # include this transaction
        if total >= self.max_in_window:
            return self.hit(f"{total} transactions within 10 minutes")
        return None


DEFAULT_RULES: tuple[Rule, ...] = (
    HighAmountVsMedianRule(),
    LargeAbsoluteAmountRule(),
    NewMerchantRule(),
    ForeignCurrencyRule(),
    RareCategoryRule(),
    VelocityRule(),
)
