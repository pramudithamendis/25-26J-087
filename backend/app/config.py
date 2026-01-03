from pydantic_settings import BaseSettings
from pathlib import Path

class Settings(BaseSettings):
    # Existing auth settings
    MONGO_URI: str
    MONGO_DB: str
    JWT_SECRET: str
    JWT_ALGORITHM: str = "HS256"
    
    # CV Analysis settings
    UPLOAD_FOLDER: str = "uploads"
    SECRET_KEY: str = ""  # For Flask compatibility (can reuse JWT_SECRET)
    
    # GitHub API
    GITHUB_TOKEN: str = ""
    
    # OpenAI API (for embeddings and LLM)
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-3.5-turbo"
    OPENAI_EMBEDDING_MODEL: str = "text-embedding-ada-002"
    
    # Provider choices
    LLM_PROVIDER: str = "openai"  # 'openai' or 'heuristic' (fallback)
    EMBEDDING_PROVIDER: str = "openai"  # 'openai' or 'sentence-transformers'
    
    # CV Extraction method
    CV_EXTRACTION_METHOD: str = "openai"  # 'openai' or 'regex'
    
    # Agentic AI settings
    USE_AGENTIC_EVALUATION: bool = True  # Use agentic system instead of pipeline
    AGENTIC_FALLBACK_TO_PIPELINE: bool = True  # Fallback to pipeline on agent failure
    MAX_AGENT_ITERATIONS: int = 20  # Maximum iterations in agentic loop
    AGENT_TEMPERATURE: float = 0.3  # LLM temperature for agents
    
    # Dataset validation settings
    DATASET_PATH: str = "backend/dataset"  # Path to dataset directory
    DATASET_VALIDATION_ENABLED: bool = True  # Enable/disable dataset validation
    DATASET_SIMILARITY_THRESHOLD: float = 0.7  # Minimum similarity for calibration
    DATASET_TOP_K: int = 5  # Number of similar cases to retrieve
    DATASET_CALIBRATION_WEIGHT: float = 0.3  # Weight for dataset-based calibration (0.3 = 30% dataset, 70% original)
    
    @property
    def CV_UPLOAD_FOLDER(self) -> str:
        """Get CV upload folder path"""
        return str(Path(self.UPLOAD_FOLDER) / "cv")
    
    @property
    def LINKEDIN_UPLOAD_FOLDER(self) -> str:
        """Get LinkedIn upload folder path"""
        return str(Path(self.UPLOAD_FOLDER) / "linkedin")

    class Config:
        env_file = ".env"

settings = Settings()
