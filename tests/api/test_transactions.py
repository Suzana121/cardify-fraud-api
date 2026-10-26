from datetime import UTC, datetime, timedelta

from tests.api.conftest import register_and_login

BASE_TIME = datetime(2026, 10, 1, 9, 0, tzinfo=UTC)


def post_txn(client, headers, **overrides):
    body = {"merchant": "Shufersal", "amount": "120.00", "currency": "ILS", "category": "Food"}
    body |= overrides
    r = client.post("/transactions", json=body, headers=headers)
    assert r.status_code == 201, r.text
    return r.json()


def build_history(client, headers, n=10):
    """n ordinary grocery payments, one every day."""
    for i in range(n):
        post_txn(client, headers, occurred_at=(BASE_TIME + timedelta(days=i)).isoformat())


def test_normal_transaction_is_approved(client, auth_headers):
    txn = post_txn(client, auth_headers)
    assert txn["status"] == "APPROVED"
    assert txn["risk_score"] == 0
    assert txn["rule_hits"] == []
    assert txn["amount_ils"] == "120.00"


def test_large_foreign_payment_is_flagged_on_first_use(client, auth_headers):
    txn = post_txn(client, auth_headers, merchant="Overseas Shop", amount="10000", currency="USD")
    assert txn["status"] == "FLAGGED"
    assert txn["amount_ils"] == "37000.00"
    codes = {h["rule_code"] for h in txn["rule_hits"]}
    assert codes == {"LARGE_ABSOLUTE_AMOUNT", "FOREIGN_CURRENCY"}


def test_anomaly_against_history_is_flagged_with_reasons(client, auth_headers):
    build_history(client, auth_headers)
    txn = post_txn(
        client,
        auth_headers,
        merchant="Crypto Exchange",
        amount="2500",
        category="Other",
        occurred_at=(BASE_TIME + timedelta(days=20)).isoformat(),
    )
    assert txn["status"] == "FLAGGED"
    codes = [h["rule_code"] for h in txn["rule_hits"]]
    assert codes[0] == "HIGH_AMOUNT_VS_MEDIAN"  # highest-scoring reason first
    assert {"NEW_MERCHANT", "RARE_CATEGORY"} <= set(codes)


def test_known_merchant_matching_ignores_case(client, auth_headers):
    build_history(client, auth_headers)
    txn = post_txn(client, auth_headers, merchant="  SHUFERSAL ")
    assert "NEW_MERCHANT" not in {h["rule_code"] for h in txn["rule_hits"]}


def test_velocity_burst_is_flagged(client, auth_headers):
    results = [
        post_txn(client, auth_headers, occurred_at=(BASE_TIME + timedelta(minutes=i)).isoformat())
        for i in range(5)
    ]
    assert [t["status"] for t in results[:4]] == ["APPROVED"] * 4
    assert results[4]["status"] == "FLAGGED"
    assert results[4]["rule_hits"][0]["rule_code"] == "VELOCITY"


def test_validation_errors(client, auth_headers):
    bad_bodies = [
        {"merchant": "X", "amount": "10"},  # merchant too short
        {"merchant": "Shop", "amount": "-5"},
        {"merchant": "Shop", "amount": "10", "currency": "JPY"},
        {"merchant": "Shop", "amount": "10", "occurred_at": "2026-10-01T09:00:00"},  # naive time
    ]
    for body in bad_bodies:
        assert client.post("/transactions", json=body, headers=auth_headers).status_code == 422


def test_requires_auth(client):
    assert client.post("/transactions", json={"merchant": "Shop", "amount": "1"}).status_code == 401
    assert client.get("/transactions").status_code == 401


def test_list_pagination_and_status_filter(client, auth_headers):
    build_history(client, auth_headers, n=3)
    post_txn(client, auth_headers, merchant="Overseas Shop", amount="10000", currency="USD")

    page = client.get("/transactions?limit=2", headers=auth_headers).json()
    assert page["total"] == 4
    assert len(page["items"]) == 2

    flagged = client.get("/transactions?status=FLAGGED", headers=auth_headers).json()
    assert flagged["total"] == 1
    assert flagged["items"][0]["merchant"] == "Overseas Shop"


def test_users_cannot_see_each_others_transactions(client, auth_headers):
    txn = post_txn(client, auth_headers)
    other = register_and_login(client, "eve@example.com")

    assert client.get(f"/transactions/{txn['id']}", headers=other).status_code == 404
    assert client.get("/transactions", headers=other).json()["total"] == 0
    r = client.patch(f"/transactions/{txn['id']}/review", json={"verdict": "fraud"}, headers=other)
    assert r.status_code == 404


def test_review_and_fraud_is_excluded_from_profile(client, auth_headers):
    build_history(client, auth_headers, n=5)
    fraud = post_txn(client, auth_headers, merchant="Casino Pro", amount="3000", category="Other")

    r = client.patch(
        f"/transactions/{fraud['id']}/review", json={"verdict": "fraud"}, headers=auth_headers
    )
    assert r.status_code == 200
    assert r.json()["status"] == "REVIEWED_FRAUD"

    # The confirmed-fraud merchant must still count as "new" for this user.
    again = post_txn(client, auth_headers, merchant="Casino Pro", amount="100", category="Food")
    assert "NEW_MERCHANT" in {h["rule_code"] for h in again["rule_hits"]}


def test_stats_summary(client, auth_headers):
    build_history(client, auth_headers, n=3)
    post_txn(client, auth_headers, merchant="Overseas Shop", amount="10000", currency="USD")

    stats = client.get("/stats/summary", headers=auth_headers).json()
    assert stats["total_transactions"] == 4
    assert stats["by_status"]["FLAGGED"] == 1
    assert stats["by_status"]["APPROVED"] == 3
    assert stats["flagged_rate"] == 0.25
    assert {r["rule_code"] for r in stats["top_rules"]} == {
        "LARGE_ABSOLUTE_AMOUNT",
        "FOREIGN_CURRENCY",
    }
