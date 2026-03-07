from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from app.auth.dependencies import get_current_user
from app.database import db
from bson import ObjectId
from datetime import datetime

router = APIRouter(prefix="/locations", tags=["Branch Locations"])

locations_collection = db["branch_locations"]

# ── Seed default locations if empty ──
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
    if locations_collection.count_documents({}) == 0:
        locations_collection.insert_many([
            {"name": loc, "created_at": datetime.utcnow()}
            for loc in DEFAULT_LOCATIONS
        ])

seed_locations()


class LocationCreate(BaseModel):
    name: str


@router.get("")
async def get_locations(user: dict = Depends(get_current_user)):
    """Get all branch locations"""
    try:
        cursor = locations_collection.find({}).sort("name", 1)
        locations = []
        for doc in cursor:
            locations.append({
                "_id": str(doc["_id"]),
                "name": doc["name"],
                "created_at": doc.get("created_at", "")
            })
        return {"status": "success", "locations": locations}
    except Exception as e:
        raise HTTPException(500, f"Error fetching locations: {str(e)}")


@router.post("")
async def add_location(body: LocationCreate, user: dict = Depends(get_current_user)):
    """Add a new branch location"""
    try:
        name = body.name.strip()
        if not name:
            raise HTTPException(400, "Location name cannot be empty")

        # Check duplicate
        existing = locations_collection.find_one({"name": {"$regex": f"^{name}$", "$options": "i"}})
        if existing:
            raise HTTPException(400, f"Location '{name}' already exists")

        result = locations_collection.insert_one({
            "name": name,
            "created_at": datetime.utcnow()
        })

        return {
            "status": "success",
            "location": {"_id": str(result.inserted_id), "name": name}
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Error adding location: {str(e)}")


@router.delete("/{location_id}")
async def delete_location(location_id: str, user: dict = Depends(get_current_user)):
    """Delete a branch location"""
    try:
        result = locations_collection.delete_one({"_id": ObjectId(location_id)})
        if result.deleted_count == 0:
            raise HTTPException(404, "Location not found")
        return {"status": "success", "message": "Location deleted"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Error deleting location: {str(e)}")