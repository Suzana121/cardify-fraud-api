from collections.abc import Sequence
from dataclasses import dataclass

from app.fraud.context import TransactionInput, UserContext
from app.fraud.rules import DEFAULT_RULES, Rule, RuleResult
from app.models import TransactionStatus

MAX_SCORE = 100


@dataclass(frozen=True)
class Decision:
    risk_score: int
    status: TransactionStatus
    hits: list[RuleResult]


def evaluate(
    txn: TransactionInput,
    ctx: UserContext,
    threshold: int,
    rules: Sequence[Rule] = DEFAULT_RULES,
) -> Decision:
    hits = [result for rule in rules if (result := rule.evaluate(txn, ctx)) is not None]
    hits.sort(key=lambda h: h.score, reverse=True)  # most important reason first
    score = min(sum(h.score for h in hits), MAX_SCORE)
    status = TransactionStatus.FLAGGED if score >= threshold else TransactionStatus.APPROVED
    return Decision(risk_score=score, status=status, hits=hits)
