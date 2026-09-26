from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from sqlalchemy import text

from app.api.leads import router as leads_router
from app.api.leads import dashboard as leads_dashboard
from app.db.database import Base, engine
from app.schemas.lead import DashboardResponse


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


@app.get("/", include_in_schema=False)
def root():
    return RedirectResponse(url="/docs")


# The assignment asks for this exact path (`GET /dashboard`), so it's
# registered at root too. It reuses the same handler as `/leads/dashboard`
# rather than duplicating the aggregation logic a second time.
app.add_api_route(
    "/dashboard",
    leads_dashboard,
    methods=["GET"],
    response_model=DashboardResponse,
    tags=["Dashboard"],
)


@app.get("/health")
def health_check():
    return {
        "status": "ok",
        "database": "connected",
    }