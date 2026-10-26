import os

# Tests always run against a dedicated database (tables are wiped between tests),
# never against whatever DATABASE_URL the developer has exported.
os.environ["DATABASE_URL"] = os.environ.get(
    "TEST_DATABASE_URL", "postgresql+psycopg://cardify:cardify@localhost:5432/cardify_test"
)
os.environ["JWT_SECRET"] = "test-secret-that-is-long-enough-for-hs256"
os.environ["FLAG_THRESHOLD"] = "50"
