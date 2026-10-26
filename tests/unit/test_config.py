import pytest

from app.core.config import normalize_db_url


@pytest.mark.parametrize(
    "url",
    [
        "postgres://u:p@host:5432/db",
        "postgresql://u:p@host:5432/db",
        "postgresql+psycopg://u:p@host:5432/db",
    ],
)
def test_normalize_db_url(url):
    assert normalize_db_url(url) == "postgresql+psycopg://u:p@host:5432/db"
