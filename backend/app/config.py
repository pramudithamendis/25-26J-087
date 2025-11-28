from pydantic_settings import BaseSettings
from pathlib import Path

class Settings(BaseSettings):
    # MongoDB Settings
    MONGO_URI: str
    MONGO_DB: str
    
    # JWT Settings
    JWT_SECRET: str
    JWT_ALGORITHM: str = "HS256"
    
    # Geocoding API Settings
    GEOCODING_API_KEY: str = ""  # Optional - defaults to empty if not set
    
    # Model Directory
    # Structure: backend/ (current location)
    #            ../notebooks/fair-prehire-attrition-prediction/models/
    MODEL_DIR: Path = Path(__file__).parent.parent.parent / "notebooks" / "fair-prehire-attrition-prediction" / "models"
    
    class Config:
        env_file = ".env"

settings = Settings()

# Verify paths on startup
print(f" Model directory: {settings.MODEL_DIR}")
print(f"   Exists: {settings.MODEL_DIR.exists()}")

if settings.MODEL_DIR.exists():
    model_files = list(settings.MODEL_DIR.glob('*.pkl')) + list(settings.MODEL_DIR.glob('*.joblib'))
    print(f"   Found {len(model_files)} model files")
    for f in model_files:
        print(f"     • {f.name}")
else:
    print("    WARNING: Model directory not found!")
    print(f"   Expected: {settings.MODEL_DIR.absolute()}")