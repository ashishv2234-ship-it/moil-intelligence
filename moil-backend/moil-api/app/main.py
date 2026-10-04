from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.db.session import Base, engine
from app.api.v1.routes import auth, ops, ingest, blasting, reports, geology, admin, weather, satellite, workflow, history
import app.models  # noqa
app = FastAPI(title="MOIL Mining Intelligence API", version="0.1.0")
app.add_middleware(CORSMiddleware, allow_origins=settings.CORS_ORIGINS.split(","), allow_methods=["*"], allow_headers=["*"])
if settings.AUTO_CREATE_TABLES: Base.metadata.create_all(engine)  # local convenience; in deployment set AUTO_CREATE_TABLES=false and run: alembic upgrade head
app.include_router(auth.router, prefix="/api/v1"); app.include_router(ops.router, prefix="/api/v1"); app.include_router(ingest.router, prefix="/api/v1"); app.include_router(blasting.router, prefix="/api/v1"); app.include_router(reports.router, prefix="/api/v1"); app.include_router(geology.router, prefix="/api/v1"); app.include_router(admin.router, prefix="/api/v1"); app.include_router(weather.router, prefix="/api/v1"); app.include_router(satellite.router, prefix="/api/v1"); app.include_router(workflow.router, prefix="/api/v1"); app.include_router(history.router, prefix="/api/v1")
@app.exception_handler(Exception)
async def hide_errors(request: Request, exc: Exception): return JSONResponse({"detail": "Internal server error"}, status_code=500)
