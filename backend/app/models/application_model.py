from app.database import db

# Applications collection
applications_collection = db["applications"]

# Create indexes for better query performance
try:
    applications_collection.create_index([("user_id", 1), ("job_id", 1)], unique=True)
    applications_collection.create_index([("job_id", 1)])
    applications_collection.create_index([("user_id", 1)])
except Exception:
    # Indexes may already exist
    pass

