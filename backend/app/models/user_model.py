from app.database import get_database

def get_users_collection():
    """Get users collection (lazy initialization)"""
    db = get_database()
    return db["users"]