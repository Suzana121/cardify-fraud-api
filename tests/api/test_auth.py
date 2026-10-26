from app.core.security import create_access_token
from tests.api.conftest import register_and_login


def test_health(client):
    assert client.get("/health").json() == {"status": "ok", "db": "ok"}


def test_register_login_and_me(client):
    headers = register_and_login(client, "Noa@Example.com")
    r = client.get("/auth/me", headers=headers)
    assert r.status_code == 200
    body = r.json()
    assert body["email"] == "noa@example.com"  # stored lower-cased
    assert "hashed_password" not in body


def test_duplicate_email_is_rejected(client):
    register_and_login(client, "noa@example.com")
    r = client.post("/auth/register", json={"email": "NOA@example.com", "password": "another-pass"})
    assert r.status_code == 409


def test_short_password_is_rejected(client):
    r = client.post("/auth/register", json={"email": "a@example.com", "password": "short"})
    assert r.status_code == 422


def test_wrong_password(client):
    register_and_login(client, "noa@example.com")
    r = client.post("/auth/login", data={"username": "noa@example.com", "password": "wrong-pass"})
    assert r.status_code == 401


def test_me_requires_token(client):
    assert client.get("/auth/me").status_code == 401


def test_garbage_token(client):
    r = client.get("/auth/me", headers={"Authorization": "Bearer not-a-jwt"})
    assert r.status_code == 401


def test_expired_token(client):
    register_and_login(client, "noa@example.com")
    token = create_access_token(user_id=1, expires_minutes=-1)
    r = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 401


def test_token_for_deleted_user(client):
    token = create_access_token(user_id=999)
    r = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 401
