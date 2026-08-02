from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text
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
    weather,
    disease_scan,
    disease_insights,
    tea_grade_scan,
)

from contextlib import asynccontextmanager

settings = get_settings()
MEDIA_DIR = Path(__file__).resolve().parents[1] / "media"
MEDIA_DIR.mkdir(parents=True, exist_ok=True)


def _ensure_field_area_precision() -> None:
    with engine.begin() as connection:
      if connection.dialect.name != "postgresql":
          return
      connection.execute(
          text(
              """
              ALTER TABLE fields
              ALTER COLUMN area_hectares TYPE NUMERIC(10, 4)
              """
          )
      )


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Ensure all tables (including users) are created
    import app.models  # noqa: F401
    Base.metadata.create_all(bind=engine)
    _ensure_field_area_precision()
    MEDIA_DIR.mkdir(parents=True, exist_ok=True)
    # Create disease-scans upload directory
    (MEDIA_DIR / "disease-scans").mkdir(parents=True, exist_ok=True)
    (MEDIA_DIR / "tea-quality-scans").mkdir(parents=True, exist_ok=True)
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
app.include_router(weather.router, prefix="/api/v1")
app.include_router(disease_scan.router, prefix="/api/v1")
app.include_router(disease_insights.router, prefix="/api/v1")
app.include_router(tea_grade_scan.router, prefix="/api/v1")


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
