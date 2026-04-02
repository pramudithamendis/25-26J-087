import logging
from datetime import datetime

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.auth.dependencies import get_current_user
from app.database import db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/locations", tags=["Branch Locations"])

locations_collection = db["branch_locations"]

# ============================================================
# DEFAULT LOCATIONS
# ============================================================

# Pre-seeded Sri Lankan branch locations covering major metro areas.
# Inserted on startup only if the collection is empty.
DEFAULT_LOCATIONS = [
    "Colombo 01, Sri Lanka",
    "Colombo 02, Sri Lanka",
    "Colombo 03, Sri Lanka",
    "Colombo 04, Sri Lanka",
    "Colombo 05, Sri Lanka",
    "Colombo 07, Sri Lanka",
    "Colombo 10, Sri Lanka",
    "Maharagama, Sri Lanka",
    "Nugegoda, Sri Lanka",
    "Rajagiriya, Sri Lanka",
    "Battaramulla, Sri Lanka",
    "Malabe, Sri Lanka",
    "Kaduwela, Sri Lanka",
    "Dehiwala, Sri Lanka",
    "Mount Lavinia, Sri Lanka",
    "Moratuwa, Sri Lanka",
    "Kelaniya, Sri Lanka",
    "Gampaha, Sri Lanka",
    "Kandy, Sri Lanka",
    "Galle, Sri Lanka",
    "Remote",
]


def seed_locations():
    """
    Insert default branch locations into the database on first startup.

    Checks whether the collection is empty before inserting to avoid
    duplicating entries on subsequent server restarts.
    """
    if locations_collection.count_documents({}) == 0:
        locations_collection.insert_many(
            [{"name": loc, "created_at": datetime.utcnow()} for loc in DEFAULT_LOCATIONS]
        )
        logger.info(f"Seeded {len(DEFAULT_LOCATIONS)} default branch locations")


seed_locations()


# ============================================================
# SCHEMAS
# ============================================================

class LocationCreate(BaseModel):
    """Request body schema for adding a new branch location."""

    name: str


# ============================================================
# ENDPOINTS
# ============================================================

@router.get("")
async def get_locations(user: dict = Depends(get_current_user)):
    """
    Retrieve all branch locations sorted alphabetically by name.

    Used to populate the job location dropdown in the job posting
    and attrition risk assessment forms.
    """
    try:
        cursor = locations_collection.find({}).sort("name", 1)
        locations = []
        for doc in cursor:
            locations.append(
                {
                    "_id": str(doc["_id"]),
                    "name": doc["name"],
                    "created_at": doc.get("created_at", ""),
                }
            )
        logger.info(f"Returned {len(locations)} branch locations")
        return {"status": "success", "locations": locations}

    except Exception as e:
        logger.error(f"Error fetching branch locations: {e}")
        raise HTTPException(500, f"Error fetching locations: {str(e)}")


@router.post("")
async def add_location(body: LocationCreate, user: dict = Depends(get_current_user)):
    """
    Add a new branch location to the database.

    Performs a case-insensitive duplicate check before inserting.
    Returns the newly created location with its assigned ID.
    """
    try:
        name = body.name.strip()

        if not name:
            raise HTTPException(400, "Location name cannot be empty")

        # Case-insensitive duplicate check
        existing = locations_collection.find_one(
            {"name": {"$regex": f"^{name}$", "$options": "i"}}
        )
        if existing:
            raise HTTPException(400, f"Location '{name}' already exists")

        result = locations_collection.insert_one(
            {"name": name, "created_at": datetime.utcnow()}
        )
        logger.info(f"Added new branch location: {name}")
        return {
            "status": "success",
            "location": {"_id": str(result.inserted_id), "name": name},
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error adding branch location '{body.name}': {e}")
        raise HTTPException(500, f"Error adding location: {str(e)}")


@router.delete("/{location_id}")
async def delete_location(
    location_id: str,
    user: dict = Depends(get_current_user),
):
    """
    Delete a branch location by its MongoDB ID.

    Returns 404 if no location with the given ID exists.
    """
    try:
        result = locations_collection.delete_one({"_id": ObjectId(location_id)})

        if result.deleted_count == 0:
            raise HTTPException(404, "Location not found")

        logger.info(f"Deleted branch location with ID: {location_id}")
        return {"status": "success", "message": "Location deleted"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting location {location_id}: {e}")
        raise HTTPException(500, f"Error deleting location: {str(e)}")