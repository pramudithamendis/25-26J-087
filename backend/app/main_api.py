"""
Lightweight API entrypoint — no ML models loaded.

Used by the Cloud Run "api" service. Handles all non-ML routes:
auth, users, jobs, CVs, articles, trends, geocoding, ESCO, locations,
forecasts, admin, HireBase, questions, candidates.

ML-heavy routes (/turnover/*, /api/evaluate/*) live in main_ml.py.
"""
import logging
import time
import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from app.auth.auth_router import auth_router
from app.routes.user_router import router as user_router
from app.routes.job_router import router as job_router
from app.routes.articles_router import router as article_router
from app.routes.hirebase_router import router as hirebase_router
from app.routes.trends_router import router as trends_router
from app.routes.questions_router import router as questions_router
from app.routes.admin_router import router as admin_router
from app.routes.cv_routes import router as cv_router
from app.routes.geocoding_router import router as geocoding_router
from app.routes.esco_router import router as esco_router
from app.routes.locations_router import router as locations_router
from app.routes.forecast_router import router as forecast_router
from app.routes.candidate_router import router as candidate_router
from app.scheduler import start_scheduler

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    try:
        from app.database import client
        client.admin.command('ping')
        logger.info("MongoDB connection successful")
    except Exception as e:
        logger.warning("MongoDB connection failed: %s — DB operations may fail", e)

    start_scheduler()

    yield

    # Shutdown
    try:
        logger.info("API service shutting down...")
    except asyncio.CancelledError:
        raise
    except Exception as e:
        logger.error("Error during shutdown: %s", e)
    finally:
        logger.info("API service shutdown complete")


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
    title="CV Analysis API",
    description="CV Analysis System — API Service",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(LoggingMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(user_router)
app.include_router(job_router)
app.include_router(article_router)
app.include_router(hirebase_router)
app.include_router(trends_router)
app.include_router(questions_router)
app.include_router(admin_router)
app.include_router(cv_router)
app.include_router(geocoding_router)
app.include_router(esco_router)
app.include_router(locations_router)
app.include_router(forecast_router)
app.include_router(candidate_router)


@app.get("/")
def root():
    return {"message": "CV Analysis API", "version": "1.0.0", "service": "api"}


@app.get("/health")
def health_check():
    try:
        from app.database import client
        client.admin.command('ping')
        mongodb_status = "connected"
    except Exception as e:
        mongodb_status = f"error: {e}"
    return {"status": "ok", "service": "api", "mongodb": mongodb_status}
