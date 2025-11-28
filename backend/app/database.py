from motor.motor_asyncio import AsyncIOMotorClient
from .config import settings

# Global variables
client: AsyncIOMotorClient = None
db = None

async def connect_to_mongo():
    """Establish asynchronous MongoDB connection"""
    global client, db
    
    print(" Connecting to MongoDB...")
    
    client = AsyncIOMotorClient(
        settings.MONGO_URI,
        serverSelectionTimeoutMS=5000
    )
    db = client[settings.MONGO_DB]
    
    # Test connection
    try:
        await client.admin.command('ping')
        print(f" MongoDB connected: {settings.MONGO_DB}")
    except Exception as e:
        print(f" MongoDB connection failed: {e}")
        raise  # Re-raise to prevent app from starting with broken DB

async def close_mongo_connection():
    """Close MongoDB connection"""
    global client
    
    if client:
        print("Closing MongoDB connection...")
        client.close()
        print(" MongoDB closed")

# Helper for routers
def get_cv_collection():
    """Get CVs collection"""
    if db is None:
        raise RuntimeError("Database not initialized. Call connect_to_mongo() first.")
    return db["cvs"]

def get_database():
    """Get database instance"""
    if db is None:
        raise RuntimeError("Database not initialized.")
    return db