from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy import text

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


@app.get("/health")
def health_check():
    return {
        "status": "ok",
        "database": "connected",
    }