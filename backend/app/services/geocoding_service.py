import aiohttp
import asyncio
import re
from typing import Tuple, Optional, List
from math import radians, sin, cos, sqrt, atan2
from app.config import settings

class GeocodingService:
    """
    Service to geocode addresses and calculate commute distances.
    Optimized for Sri Lankan geography and traffic patterns.
    """
    
    BASE_URL = "https://geocode.maps.co/search"
    
    # Road distance multipliers for Sri Lanka (Straight line to Road distance conversion)
    ROAD_DISTANCE_MULTIPLIERS = {
        'colombo_metro': 1.20,     # Metro area with multiple routes
        'close_suburbs': 1.15,      # Very close neighboring areas
        'western_urban': 1.35,      # Limited main roads, high congestion
        'inter_province': 1.5,      # Geographic curves/terrain
        'remote_areas': 1.7,        # Indirect rural road networks
    }
    
    # Common Sri Lankan cities for extraction and fallback
    SL_CITIES = [
        'Colombo', 'Kandy', 'Galle', 'Jaffna', 'Negombo', 'Anuradhapura', 
        'Trincomalee', 'Batticaloa', 'Matara', 'Moratuwa', 'Maharagama', 
        'Nugegoda', 'Dehiwala', 'Kurunegala', 'Ratnapura', 'Badulla', 
        'Kalutara', 'Gampaha', 'Kelaniya', 'Malabe', 'Kaduwela', 'Panadura', 
        'Wattala', 'Piliyandala', 'Mount Lavinia', 'Ratmalana', 'Wellawatte', 
        'Bambalapitiya', 'Kollupitiya', 'Rajagiriya', 'Battaramulla', 'Nawala',
        'Pannipitiya', 'Kottawa', 'Hokandara', 'Athurugiriya', 'Hanwella'
    ]

    # Expanded Colombo Metropolitan Region
    COLOMBO_METRO_AREAS = [
        'colombo', 'dehiwala', 'mount lavinia', 'moratuwa', 'nugegoda',
        'maharagama', 'kotte', 'battaramulla', 'rajagiriya', 'nawala',
        'wellawatte', 'bambalapitiya', 'maradana', 'kollupitiya', 'fort',
        'kelaniya', 'kaduwela', 'malabe', 'pannipitiya', 'piliyandala',
        'ratmalana', 'wattala', 'ja-ela', 'peliyagoda', 'kiribathgoda',
        'kottawa', 'hokandara', 'athurugiriya', 'talawatugoda', 'koswatta',
        'borella', 'kotahena', 'pettah', 'slave island', 'cinnamon gardens'
    ]

    # Close neighboring pairs (within 5-8km typically)
    CLOSE_NEIGHBORS = {
        'maharagama': ['nugegoda', 'kottawa', 'pannipitiya', 'piliyandala', 'dehiwala'],
        'nugegoda': ['maharagama', 'dehiwala', 'nawala', 'rajagiriya', 'kotte'],
        'pannipitiya': ['maharagama', 'kottawa', 'hokandara', 'athurugiriya'],
        'kelaniya': ['peliyagoda', 'kiribathgoda', 'wattala', 'kaduwela'],
        'dehiwala': ['mount lavinia', 'nugegoda', 'maharagama', 'wellawatte', 'ratmalana'],
        'moratuwa': ['mount lavinia', 'ratmalana', 'piliyandala', 'dehiwala'],
        'battaramulla': ['rajagiriya', 'nawala', 'kotte', 'malabe', 'koswatta'],
        'rajagiriya': ['nawala', 'battaramulla', 'nugegoda', 'kotte'],
        'malabe': ['kaduwela', 'battaramulla', 'athurugiriya', 'koswatta'],
        'kaduwela': ['malabe', 'athurugiriya', 'kelaniya', 'battaramulla'],
    }

    def __init__(self):
        self.api_key = settings.GEOCODING_API_KEY
        self.cache = {}

    def are_close_neighbors(self, location1: str, location2: str) -> bool:
        """Check if two locations are known close neighbors."""
        loc1, loc2 = location1.lower(), location2.lower()
        
        for key, neighbors in self.CLOSE_NEIGHBORS.items():
            if key in loc1:
                if any(n in loc2 for n in neighbors):
                    return True
            if key in loc2:
                if any(n in loc1 for n in neighbors):
                    return True
        return False

    def determine_route_type(self, location1: str, location2: str) -> str:
        """Determine route type based on locations to apply correct multiplier."""
        loc1, loc2 = location1.lower(), location2.lower()
        
        # Check if both are in Colombo Metro
        both_metro = (any(c in loc1 for c in self.COLOMBO_METRO_AREAS) and 
                     any(c in loc2 for c in self.COLOMBO_METRO_AREAS))
        
        if both_metro:
            # Check if they're close neighbors
            if self.are_close_neighbors(location1, location2):
                return 'close_suburbs'
            return 'colombo_metro'
        
        return 'western_urban'  # Default for most cases

    def clean_address_for_fallback(self, address: str) -> str:
        """Simplifies address to just City, Sri Lanka for fallback geocoding."""
        address_lower = address.lower()
        for city in self.SL_CITIES:
            if city.lower() in address_lower:
                return f"{city}, Sri Lanka"
        return "Colombo, Sri Lanka"

    async def _call_api(self, query: str) -> Optional[Tuple[float, float]]:
        """Internal helper to call the Geocoding API."""
        if query in self.cache:
            return self.cache[query]

        try:
            params = {"q": query, "api_key": self.api_key}
            async with aiohttp.ClientSession() as session:
                async with session.get(self.BASE_URL, params=params, timeout=5) as response:
                    if response.status == 200:
                        data = await response.json()
                        if data and len(data) > 0:
                            lat, lon = float(data[0]["lat"]), float(data[0]["lon"])
                            self.cache[query] = (lat, lon)
                            return (lat, lon)
            return None
        except Exception as e:
            print(f"Geocoding API error: {e}")
            return None

    async def geocode_address(self, address: str) -> Optional[Tuple[float, float]]:
        """
        Two-step Geocoding: 
        1. Try the full address (precise).
        2. If that fails, try the city-only (fallback).
        """
        if not address: return None
        
        # Step 1: Precise search (Street + City)
        coords = await self._call_api(address)
        if coords: return coords
        
        # Step 2: Fallback (City only)
        fallback_query = self.clean_address_for_fallback(address)
        return await self._call_api(fallback_query)

    def calculate_haversine_distance(self, lat1, lon1, lat2, lon2) -> float:
        """Straight-line distance in km."""
        R = 6371.0
        dlat, dlon = radians(lat2 - lat1), radians(lon2 - lon1)
        a = sin(dlat / 2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2)**2
        return R * (2 * atan2(sqrt(a), sqrt(1 - a)))

    async def calculate_commute_distance(self, cv_location: str, job_location: str) -> Tuple[float, str]:
        """
        Calculates estimated road distance and assigns a risk category.
        """
        # 1. Handle Remote
        if any(x in job_location.lower() for x in ["remote", "work from home"]):
            return (0.0, "low")

        # 2. Get Coordinates
        cv_coords = await self.geocode_address(cv_location)
        job_coords = await self.geocode_address(job_location)

        if not cv_coords or not job_coords:
            return (0.0, "medium")

        # 3. Calculate Base Distance
        base_dist = self.calculate_haversine_distance(
            cv_coords[0], cv_coords[1], job_coords[0], job_coords[1]
        )
        
        # 4. Determine Route Type
        route_type = self.determine_route_type(cv_location, job_location)
        
        # 5. Apply Multiplier
        multiplier = self.ROAD_DISTANCE_MULTIPLIERS.get(route_type, 1.4)
        road_dist = base_dist * multiplier

        # 6. Apply Centroid Correction for Metro Areas
        # When geocoding returns city centroids, distances get inflated
        if route_type in ['colombo_metro', 'close_suburbs']:
            if road_dist > 15:
                # Large inflation - likely centroid-to-centroid
                road_dist = road_dist * 0.50
            elif road_dist > 10:
                # Moderate inflation
                road_dist = road_dist * 0.65
            elif road_dist > 6:
                # Minor inflation
                road_dist = road_dist * 0.80
        
        # 7. Floor to minimum realistic distance for close neighbors
        if route_type == 'close_suburbs' and road_dist < 3:
            road_dist = max(road_dist, 2.5)  # Minimum realistic commute
        
        # 8. Categorize Risk
        if road_dist < 6:
            risk = "low"
        elif road_dist < 18:
            risk = "medium"
        elif road_dist < 35:
            risk = "high"
        else:
            risk = "very_high"

        return (round(road_dist, 2), risk)

    def get_location_match_score(self, distance_km: float, commute_risk: str) -> float:
        """Convert commute risk to a matching score."""
        risk_scores = {
            "low": 1.0, 
            "medium": 0.8, 
            "high": 0.4, 
            "very_high": 0.1
        }
        return risk_scores.get(commute_risk, 0.5)

# Singleton
_geocoding_service = None

def get_geocoding_service() -> GeocodingService:
    global _geocoding_service
    if _geocoding_service is None:
        _geocoding_service = GeocodingService()
    return _geocoding_service