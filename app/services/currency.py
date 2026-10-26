from decimal import ROUND_HALF_UP, Decimal

# Fixed rates are enough for anomaly scoring (same approach as the original Cardify project).
RATES_TO_ILS: dict[str, Decimal] = {
    "ILS": Decimal("1.0"),
    "USD": Decimal("3.7"),
    "EUR": Decimal("4.0"),
    "GBP": Decimal("4.6"),
}
SUPPORTED_CURRENCIES = frozenset(RATES_TO_ILS)
HOME_CURRENCY = "ILS"


def to_ils(amount: Decimal, currency: str) -> Decimal:
    rate = RATES_TO_ILS[currency]
    return (amount * rate).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
