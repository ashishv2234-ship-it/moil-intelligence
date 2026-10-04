from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.routes import (
    admin,
    auth,
    blasting,
    geology,
    history,
    ingest,
    ops,
    reports,
    satellite,
    weather,
    workflow,
)
from app.core.config import settings
from app.db.session import Base, engine

# Import models so SQLAlchemy knows about all tables.
import app.models  # noqa: F401


app = FastAPI(
    title="MOIL Mining Intelligence API",
    version="0.1.0",
)


# ============================================================
# CORS
# ============================================================

cors_origins = [
    origin.strip()
    for origin in settings.CORS_ORIGINS.split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# DATABASE
# ============================================================

if settings.AUTO_CREATE_TABLES:
    Base.metadata.create_all(bind=engine)


# ============================================================
# ROUTES
# ============================================================

app.include_router(
    auth.router,
    prefix="/api/v1",
)

app.include_router(
    ops.router,
    prefix="/api/v1",
)

app.include_router(
    ingest.router,
    prefix="/api/v1",
)

app.include_router(
    blasting.router,
    prefix="/api/v1",
)

app.include_router(
    reports.router,
    prefix="/api/v1",
)

app.include_router(
    geology.router,
    prefix="/api/v1",
)

app.include_router(
    admin.router,
    prefix="/api/v1",
)

app.include_router(
    weather.router,
    prefix="/api/v1",
)

app.include_router(
    satellite.router,
    prefix="/api/v1",
)

app.include_router(
    workflow.router,
    prefix="/api/v1",
)

app.include_router(
    history.router,
    prefix="/api/v1",
)


# ============================================================
# ROOT / HEALTH CHECK
# ============================================================

@app.get("/")
def root():
    return {
        "message": "MOIL Mining Intelligence API",
        "status": "online",
        "version": "0.1.0",
    }


@app.get("/health")
def health():
    return {
        "status": "healthy",
    }


# ============================================================
# GLOBAL EXCEPTION HANDLER
# ============================================================

@app.exception_handler(Exception)
async def hide_errors(
    request: Request,
    exc: Exception,
):
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error",
        },
    )