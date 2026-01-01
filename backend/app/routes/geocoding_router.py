from fastapi import APIRouter, Depends, HTTPException, Query
from app.auth.dependencies import get_current_user
from app.services.geocoding_service import get_geocoding_service
from app.config import settings

router = APIRouter(prefix="/geocoding", tags=["Geocoding"])

@router.get("/test")
async def test_geocoding_api():
    """
    Test if geocoding API is configured and working
    """
    
    if not settings.GEOCODING_API_KEY:
        return {
            "status": "not_configured",
            "message": "GEOCODING_API_KEY not set in .env file",
            "instructions": [
                "1. Get API key from: https://geocode.maps.co/",
                "2. Add to .env: GEOCODING_API_KEY=your_key_here",
                "3. Restart server"
            ]
        }
    
    # Test with a simple address
    geocoding = get_geocoding_service()
    coords = await geocoding.geocode_address("Colombo, Sri Lanka")
    
    if coords:
        return {
            "status": "working",
            "message": "Geocoding API is configured and working correctly",
            "test_result": {
                "address": "Colombo, Sri Lanka",
                "coordinates": {
                    "latitude": coords[0],
                    "longitude": coords[1]
                }
            },
            "api_info": {
                "provider": "geocode.maps.co",
                "free_tier": "25,000 requests @ 5 requests/second"
            }
        }
    else:
        return {
            "status": "error",
            "message": "Geocoding API key is set but API call failed",
            "possible_reasons": [
                "Invalid API key",
                "Rate limit exceeded",
                "Network connectivity issue"
            ]
        }

@router.get("/geocode")
async def geocode_address(
    address: str = Query(..., description="Address to geocode (e.g., 'Colombo, Sri Lanka')"),
    user: dict = Depends(get_current_user)
):
    """
    Geocode a specific address to get coordinates
    """
    
    if not settings.GEOCODING_API_KEY:
        raise HTTPException(400, "Geocoding API not configured")
    
    geocoding = get_geocoding_service()
    coords = await geocoding.geocode_address(address)
    
    if coords:
        return {
            "status": "success",
            "address": address,
            "coordinates": {
                "latitude": coords[0],
                "longitude": coords[1]
            }
        }
    else:
        raise HTTPException(404, f"Could not geocode address: {address}")

@router.get("/distance")
async def calculate_distance(
    from_address: str = Query(..., description="Starting address"),
    to_address: str = Query(..., description="Destination address"),
    user: dict = Depends(get_current_user)
):
    """
    Calculate commute distance between two addresses
    
    Example:
    - from_address: "Maharagama, Sri Lanka"
    - to_address: "Colombo 03, Sri Lanka"
    """
    
    if not settings.GEOCODING_API_KEY:
        raise HTTPException(400, "Geocoding API not configured")
    
    geocoding = get_geocoding_service()
    distance_km, risk = await geocoding.calculate_commute_distance(
        from_address, 
        to_address
    )
    
    location_score = geocoding.get_location_match_score(distance_km, risk)
    
    return {
        "status": "success",
        "from": from_address,
        "to": to_address,
        "distance_km": distance_km,
        "commute_risk": risk,
        "location_match_score": location_score,
        "interpretation": {
            "low": "< 6 km - Very manageable commute",
            "medium": "6-18 km - Moderate commute",
            "high": "18-35 km - Long commute",
            "very_high": "> 35 km - Very long commute"
        }[risk]
    }

@router.get("/usage")
async def get_api_usage():
    """
    Get information about geocoding API usage
    """
    
    return {
        "api": "geocode.maps.co",
        "pricing": {
            "free_tier": {
                "requests": 25000,
                "rate_limit": "5 requests/second initially, then 1 request/second"
            }
        },
        "documentation": "https://geocode.maps.co/",
        "configuration": {
            "api_key_set": bool(settings.GEOCODING_API_KEY),
            "caching": "Enabled (in-memory cache to reduce API calls)"
        }
    }