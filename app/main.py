from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy import text, select

from app.api.leads import router as leads_router
from app.db.database import Base, engine
from app.db.models import Lead


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)

    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))

    yield


app = FastAPI(
    title="AI-Assisted Mini Lead Management System",
    version="0.1.0",
    lifespan=lifespan,
)


app.include_router(leads_router)


@app.get("/dashboard")
def dashboard():
    with engine.connect() as connection:
        rows = connection.execute(
            select(Lead.lead_status, Lead.source_channel)
        ).all()

    by_status: dict[str, int] = {}
    by_source_channel: dict[str, int] = {}
    for status, source in rows:
        status_key = status or "Unknown"
        source_key = source or "Unknown"
        by_status[status_key] = by_status.get(status_key, 0) + 1
        by_source_channel[source_key] = by_source_channel.get(source_key, 0) + 1

    return {
        "total_leads": len(rows),
        "by_status": dict(sorted(by_status.items())),
        "by_source_channel": dict(sorted(by_source_channel.items())),
    }


@app.get("/health")
def health_check():
    return {
        "status": "ok",
        "database": "connected",
    }