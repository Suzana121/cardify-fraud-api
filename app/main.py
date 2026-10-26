from fastapi import FastAPI
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.api.deps import DbSession
from app.api.routes import auth, stats, transactions

app = FastAPI(
    title="Cardify Fraud API",
    version="0.1.0",
    description=(
        "Scores credit-card transactions against each user's spending history "
        "with an explainable rule engine and flags suspicious ones."
    ),
)

app.include_router(auth.router)
app.include_router(transactions.router)
app.include_router(stats.router)


@app.get("/health", tags=["health"])
def health(db: DbSession):
    try:
        db.execute(text("SELECT 1"))
    except Exception:
        return JSONResponse(status_code=503, content={"status": "degraded", "db": "unreachable"})
    return {"status": "ok", "db": "ok"}
