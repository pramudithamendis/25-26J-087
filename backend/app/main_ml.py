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
    # 1. Download models from GCS (retry to survive IAM propagation delay on Cloud Run)
    import time as _time
    from app.utils.gcs_loader import download_models_if_gcs
    for _attempt in range(1, 4):
        try:
            download_models_if_gcs()
            break
        except Exception as _e:
            if _attempt < 3:
                _wait = 30 * _attempt
                logger.warning(
                    "GCS download attempt %d/3 failed: %s — retrying in %ds",
                    _attempt, _e, _wait,
                )
                _time.sleep(_wait)
            else:
                logger.error(
                    "GCS download failed after 3 attempts: %s — "
                    "container starting without models; ML endpoints will return errors",
                    _e,
                )

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

    # SHAP explainer is NOT pre-loaded at startup — shap.TreeExplainer causes a
    # C-level SIGSEGV (OpenMP conflict with PyTorch) that bypasses try/except and
    # kills the process. It is initialised lazily on the first prediction request.

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