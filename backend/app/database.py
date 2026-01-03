from pymongo import MongoClient
from .config import settings
import logging

logger = logging.getLogger(__name__)

try:
    client = MongoClient(settings.MONGO_URI, serverSelectionTimeoutMS=5000)
    # Test connection
    client.admin.command('ping')
    db = client[settings.MONGO_DB]
    logger.info(f"Connected to MongoDB: {settings.MONGO_DB}")
except Exception as e:
    logger.error(f"Failed to connect to MongoDB: {str(e)}")
    # Still create client for graceful degradation
    client = MongoClient(settings.MONGO_URI)
    db = client[settings.MONGO_DB]
