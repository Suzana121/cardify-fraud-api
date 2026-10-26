from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.db.session import engine
from app.main import app

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="session", autouse=True)
def migrated_db():
    """Run the real migrations (down, then up) so the tests also prove the migrations work."""
    cfg = Config(str(ROOT / "alembic.ini"))
    cfg.set_main_option("script_location", str(ROOT / "alembic"))
    command.downgrade(cfg, "base")
    command.upgrade(cfg, "head")
    yield


@pytest.fixture(autouse=True)
def clean_tables():
    yield
    with engine.begin() as conn:
        conn.execute(text("TRUNCATE rule_hits, transactions, users RESTART IDENTITY CASCADE"))


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def register_and_login(client: TestClient, email: str, password: str = "s3cret-pass") -> dict:
    r = client.post("/auth/register", json={"email": email, "password": password})
    assert r.status_code == 201, r.text
    r = client.post("/auth/login", data={"username": email, "password": password})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture
def auth_headers(client) -> dict:
    return register_and_login(client, "dana@example.com")
