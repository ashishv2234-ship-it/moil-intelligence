from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.db.session import Base, engine
from app.api.v1.routes import (
    auth,
    ops,
    ingest,
    blasting,
    reports,
    geology,
    admin,
    weather,
    satellite,
    workflow,
    history,
)

import app.models  # noqa: F401


# ============================================================
# APPLICATION
# ============================================================

app = FastAPI(
    title="MOIL Mining Intelligence API",
    version="0.1.0",
)


# ============================================================
# CORS CONFIGURATION
# ============================================================

# Read CORS origins from environment/config.
#
# Example:
# CORS_ORIGINS=https://moil-intelligence-git-main-ashish-dd8b.vercel.app
#
# Multiple origins can be supplied:
# CORS_ORIGINS=http://localhost:5173,https://example.vercel.app

raw_cors_origins = getattr(
    settings,
    "CORS_ORIGINS",
    "",
)

cors_origins = [
    origin.strip().rstrip("/")
    for origin in raw_cors_origins.split(",")
    if origin.strip()
]


# Local development fallback.
#
# IMPORTANT:
# In production, Render should have CORS_ORIGINS configured.
if not cors_origins:
    cors_origins = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
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

# For local development only.
#
# Production should use:
#     alembic upgrade head
#
# AUTO_CREATE_TABLES should normally be false on Render.
if settings.AUTO_CREATE_TABLES:
    Base.metadata.create_all(bind=engine)


# ============================================================
# API ROUTES
# ============================================================

API_PREFIX = "/api/v1"

app.include_router(auth.router, prefix=API_PREFIX)
app.include_router(ops.router, prefix=API_PREFIX)
app.include_router(ingest.router, prefix=API_PREFIX)
app.include_router(blasting.router, prefix=API_PREFIX)
app.include_router(reports.router, prefix=API_PREFIX)
app.include_router(geology.router, prefix=API_PREFIX)
app.include_router(admin.router, prefix=API_PREFIX)
app.include_router(weather.router, prefix=API_PREFIX)
app.include_router(satellite.router, prefix=API_PREFIX)
app.include_router(workflow.router, prefix=API_PREFIX)
app.include_router(history.router, prefix=API_PREFIX)


# ============================================================
# HEALTH CHECK
# ============================================================

@app.get("/")
async def root():
    return {
        "message": "MOIL Mining Intelligence API",
        "status": "online",
        "version": "0.1.0",
    }


@app.get("/health")
async def health():
    return {
        "status": "healthy",
    }


# ============================================================
# GLOBAL ERROR HANDLER
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