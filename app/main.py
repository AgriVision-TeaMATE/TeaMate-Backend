from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import uvicorn

from .config import get_settings
from .database import engine, Base
from .routers import (
    auth,
    fields,
    workers,
    harvest_rounds,
    analysis,
    schedules,
    notifications,
    yield_settings,
)

from contextlib import asynccontextmanager

settings = get_settings()
MEDIA_DIR = Path(__file__).resolve().parents[1] / "media"
MEDIA_DIR.mkdir(parents=True, exist_ok=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Ensure all tables (including users) are created
    import app.models  # noqa: F401
    Base.metadata.create_all(bind=engine)
    MEDIA_DIR.mkdir(parents=True, exist_ok=True)
    yield


app = FastAPI(
    title="TeaMate Yield Optimization Backend",
    description="FastAPI + PostgreSQL service connecting mobile app and ML model.",
    version="1.0.0",
    lifespan=lifespan,
)

# Allow mobile app connections (CORS)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.mount("/media", StaticFiles(directory=MEDIA_DIR), name="media")

# Register API routers
app.include_router(auth.router, prefix="/api/v1")
app.include_router(fields.router, prefix="/api/v1")
app.include_router(workers.router, prefix="/api/v1")
app.include_router(harvest_rounds.router, prefix="/api/v1")
app.include_router(analysis.router, prefix="/api/v1")
app.include_router(schedules.router, prefix="/api/v1")
app.include_router(notifications.router, prefix="/api/v1")
app.include_router(yield_settings.router, prefix="/api/v1")


@app.get("/health", tags=["System"])
def health_check():
    return {
        "status": "healthy",
        "service": "TeaMate Backend",
        "database": settings.DATABASE_URL.split("@")[-1],
        "ml_model_api": settings.ML_MODEL_URL,
    }


if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=settings.APP_HOST,
        port=settings.APP_PORT,
        reload=settings.DEBUG,
    )
