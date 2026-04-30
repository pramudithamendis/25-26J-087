from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from contextlib import asynccontextmanager
from app.auth.auth_router import auth_router
from app.routes.user_router import router as user_router
from app.routes.job_router import router as job_router
from app.routes.evaluation_router import router as evaluation_router
from app.routes.articles_router import router as article_router
from app.routes.hirebase_router import router as hirebase_router
from app.routes.trends_router import router as trends_router
from app.scheduler import start_scheduler
from app.routes.questions_router import router as questions_router

from app.routes.admin_router import router as admin_router
from app.services.model_loader import load_model, load_preprocessor
from app.routes.cv_routes import router as cv_router
from app.routes.turnover_router import router as turnover_router
from app.routes.geocoding_router import router as geocoding_router
from app.routes.esco_router import router as esco_router
from app.routes.locations_router import router as locations_router
from app.routes.forecast_router import router as forecast_router

import logging
import time
import asyncio
from dotenv import load_dotenv
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)


logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for startup and shutdown events.
    Properly handles cancellation and cleanup.
    """
    # Startup
    try:
        from app.database import client
        client.admin.command('ping')
        logger.info("MongoDB connection successful")
        load_model()
        load_preprocessor()
    except Exception as e:
        logger.error(f"MongoDB connection failed: {str(e)}")
        logger.warning("Server will start but database operations may fail")
        logger.warning(f"Model loading failed: {e}")

    #start background scheduler
    start_scheduler()
    
    #pre-load ML models
    try:
        from app.services.model_loader import get_model
        from app.services.turnover_service import get_shap_explainer
        get_model()
        get_shap_explainer()
        logger.info("Models pre-loaded successfully")
    except Exception as e:
        logger.warning(f"Could not pre-load models: {e}")

    yield

    # Shutdown
    try:
        logger.info("Shutting down application...")
        # Add any cleanup logic here if needed
    except asyncio.CancelledError:
        logger.info("Application shutdown cancelled")
        raise
    except Exception as e:
        logger.error(f"Error during shutdown: {str(e)}")
    finally:
        logger.info("Application shutdown complete")


class LoggingMiddleware(BaseHTTPMiddleware):
    """Middleware to log all requests"""
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        logger.info(f"Incoming request: {request.method} {request.url.path}")

        try:
            response = await call_next(request)
            process_time = time.time() - start_time
            logger.info(
                f"Request completed: {request.method} {request.url.path} "
                f"Status: {response.status_code} Time: {process_time:.3f}s"
            )
            return response
        except Exception as e:
            process_time = time.time() - start_time
            logger.error(
                f"Request failed: {request.method} {request.url.path} "
                f"Error: {str(e)} Time: {process_time:.3f}s",
                exc_info=True
            )
            raise

app = FastAPI(
    title="CV Analysis API",
    description="CV Analysis System with Agentic AI",
    version="1.0.0",
    lifespan=lifespan
)

# Add logging middleware
app.add_middleware(LoggingMiddleware)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(auth_router)
app.include_router(user_router)
app.include_router(job_router)
app.include_router(evaluation_router)
app.include_router(article_router)
app.include_router(hirebase_router)
app.include_router(trends_router)
app.include_router(questions_router)
app.include_router(admin_router)
app.include_router(cv_router)
app.include_router(turnover_router)
app.include_router(geocoding_router)
app.include_router(esco_router)
app.include_router(locations_router)
app.include_router(forecast_router)

@app.get("/")
def root():
    """Root endpoint"""
    return {
        "message": "CV Analysis API",
        "version": "1.0.0",
        "docs": "/docs"
    }

@app.get("/health")
def health_check():
    """Health check endpoint"""
    try:
        from app.database import client
        client.admin.command('ping')
        mongodb_status = "connected"
        logger.debug("MongoDB connection successful")
    except Exception as e:
        mongodb_status = f"error: {str(e)}"
        logger.error(f"MongoDB connection failed: {str(e)}")

    return {
        "status": "ok",
        "mongodb": mongodb_status
    }


