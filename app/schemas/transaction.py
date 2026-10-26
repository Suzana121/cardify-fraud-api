from datetime import UTC, datetime
from decimal import Decimal
from typing import Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, field_validator

from app.models import TransactionStatus
from app.services.currency import SUPPORTED_CURRENCIES

Category = Literal[
    "Food", "Shopping", "Transport", "Health", "Education", "Entertainment", "Travel", "Other"
]


class TransactionCreate(BaseModel):
    merchant: str = Field(min_length=2, max_length=255, examples=["Shufersal"])
    amount: Decimal = Field(gt=0, le=1_000_000, max_digits=12, decimal_places=2, examples=[120.5])
    currency: str = Field(default="ILS", examples=["ILS"])
    category: Category = "Other"
    occurred_at: AwareDatetime | None = Field(
        default=None, description="When the payment happened (defaults to now)"
    )

    @field_validator("merchant")
    @classmethod
    def strip_merchant(cls, v: str) -> str:
        return v.strip()

    @field_validator("currency")
    @classmethod
    def check_currency(cls, v: str) -> str:
        v = v.upper()
        if v not in SUPPORTED_CURRENCIES:
            raise ValueError(f"currency must be one of {sorted(SUPPORTED_CURRENCIES)}")
        return v

    def occurred_at_or_now(self) -> datetime:
        return self.occurred_at or datetime.now(UTC)


class RuleHitOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    rule_code: str
    reason: str
    score: int


class TransactionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    merchant: str
    amount: Decimal
    currency: str
    amount_ils: Decimal
    category: str
    occurred_at: datetime
    risk_score: int
    status: TransactionStatus
    rule_hits: list[RuleHitOut]
    created_at: datetime


class TransactionPage(BaseModel):
    items: list[TransactionOut]
    total: int
    limit: int
    offset: int


class ReviewIn(BaseModel):
    verdict: Literal["legit", "fraud"]


class RuleCount(BaseModel):
    rule_code: str
    count: int


class StatsSummary(BaseModel):
    total_transactions: int
    by_status: dict[TransactionStatus, int]
    flagged_rate: float
    top_rules: list[RuleCount]
