"""
ML-heavy entrypoint — loads all ML models.

Used by the Cloud Run "ml" service. Handles:
  - /turnover/*         Turnover prediction + SHAP explanations
  - /api/evaluate/*     CV evaluation (pipeline + agentic)
  - /internal/*         Internal skill extraction + warmup (called by api service)

GCS model download runs before model loading at startup.
"""
import logging
import os
import time
import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from app.routes.evaluation_router import router as evaluation_router
from app.routes.turnover_router import router as turnover_router
from app.routes.internal_router import router as internal_router

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 1. Download models from GCS if configured (no-op in local dev)
    try:
        from app.utils.gcs_loader import download_models_if_gcs
        download_models_if_gcs()
    except Exception as e:
        logger.error("GCS model download failed: %s", e)
        raise

    # 2. Connect to MongoDB
    try:
        from app.database import client
        client.admin.command('ping')
        logger.info("MongoDB connection successful")
    except Exception as e:
        logger.warning("MongoDB connection failed: %s — DB operations may fail", e)

    # 3. Pre-load all ML models (avoids cold-start on first request)
    try:
        from app.services.model_loader import load_model, load_preprocessor, get_model
        load_model()
        load_preprocessor()
        get_model()
        logger.info("Ensemble models pre-loaded")
    except Exception as e:
        logger.warning("Ensemble model pre-load failed: %s", e)

    try:
        from app.services.turnover_service import get_shap_explainer
        get_shap_explainer()
        logger.info("SHAP explainer pre-loaded")
    except Exception as e:
        logger.warning("SHAP pre-load failed: %s", e)

    yield

    # Shutdown
    try:
        logger.info("ML service shutting down...")
    except asyncio.CancelledError:
        raise
    except Exception as e:
        logger.error("Error during shutdown: %s", e)
    finally:
        logger.info("ML service shutdown complete")


class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        logger.info("Incoming request: %s %s", request.method, request.url.path)
        try:
            response = await call_next(request)
            elapsed = time.time() - start_time
            logger.info(
                "Request completed: %s %s — %s (%.3fs)",
                request.method, request.url.path, response.status_code, elapsed
            )
            return response
        except Exception as e:
            elapsed = time.time() - start_time
            logger.error(
                "Request failed: %s %s — %s (%.3fs)",
                request.method, request.url.path, e, elapsed, exc_info=True
            )
            raise


app = FastAPI(
    title="CV Analysis ML Service",
    description="CV Analysis System — ML Service (turnover prediction, evaluation, skill extraction)",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(LoggingMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "*").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(turnover_router)
app.include_router(evaluation_router)
app.include_router(internal_router)


@app.get("/")
def root():
    return {"message": "CV Analysis ML Service", "version": "1.0.0", "service": "ml"}


@app.get("/health")
def health_check():
    from app.services.model_loader import model_health_check
    model_status = model_health_check()
    try:
        from app.database import client
        client.admin.command('ping')
        mongodb_status = "connected"
    except Exception as e:
        mongodb_status = f"error: {e}"
    return {
        "status": "ok",
        "service": "ml",
        "mongodb": mongodb_status,
        "models": model_status,
    }