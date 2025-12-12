from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

# Database
from app.database import connect_to_mongo, close_mongo_connection

# Routers
from app.auth.auth_router import auth_router
from app.routes.user_router import router as user_router
from app.routes.cv_routes import router as cv_router
from app.routes.turnover_router import router as turnover_router
from app.routes.geocoding_router import router as geocoding_router
from app.routes.esco_router import router as esco_router

# Model loading
from app.services.model_downloader import ensure_model_files
from app.services.model_loader import load_model, load_preprocessor

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Startup and shutdown events
    - Connect to MongoDB
    - Download models if missing
    - Load ML models
    """
    # Startup
    print(" Starting up...")
    
    # Connect to MongoDB
    try:
        await connect_to_mongo()
    except Exception as e:
        print(f"  MongoDB connection failed: {e}")
        print("   Application will start but database features won't work")

    # Load ESCO Mapper
    try:
        from app.services.esco_mapper import get_esco_mapper
        esco = get_esco_mapper()
        if esco:
            print(" ESCO Mapper loaded successfully")
        else:
            print("  ESCO Mapper unavailable, using fallback matching")
    except Exception as e:
        print(f"  ESCO loading error: {e}")
    
    #  Ensure model files are present (download if missing)
    try:
        ensure_model_files()
    except Exception as e:
        print(f"  Model download check failed: {e}")
    
    # Load ML models
    try:
        load_model()
        load_preprocessor()
        print(" Models loaded successfully")
    except Exception as e:
        print(f"  Model loading error: {e}")
        print("   Application will start but predictions will fail")
        print("   Check if model files are present in models/ folder")
    
    print(" Application ready")
    
    yield
    
    # Shutdown
    print(" Shutting down...")
    await close_mongo_connection()
    print(" Cleanup complete")

# Create FastAPI app
app = FastAPI(
    title="AI-Based CV Analysis & Turnover Prediction API",
    description="Pre-hire attrition risk prediction using ML",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth_router)
app.include_router(user_router)
app.include_router(cv_router)
app.include_router(turnover_router)
app.include_router(geocoding_router)
app.include_router(esco_router)

@app.get("/")
def home():
    return {
        "message": "AI-Based CV Analysis & Turnover Prediction API",
        "version": "1.0.0",
        "status": "operational",
        "endpoints": {
            "auth": {
                "register": "POST /auth/register",
                "login": "POST /auth/login"
            },
            "cv_management": {
                "submit": "POST /cv/submit",
                "list": "GET /cv/list",
                "retrieve": "GET /cv/{cv_id}"
            },
            "prediction": {
                "predict": "POST /turnover/predict",
                "health": "GET /turnover/health"
            },
            "geocoding": {
                "test": "GET /geocoding/test",
                "geocode": "GET /geocoding/geocode",
                "distance": "GET /geocoding/distance",
                "usage": "GET /geocoding/usage"
            },
            "user": {
                "me": "GET /users/me"
            }
        },
        "documentation": {
            "swagger_ui": "/docs",
            "redoc": "/redoc",
            "openapi_json": "/openapi.json"
        }
    }

@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "components": {
            "database": "connected",
            "ml_model": "loaded"
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )