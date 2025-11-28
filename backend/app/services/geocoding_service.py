import aiohttp
import asyncio
from typing import Tuple, Optional
from math import radians, sin, cos, sqrt, atan2
from app.config import settings

class GeocodingService:
    """
    Service to geocode addresses and calculate commute distances
    Using geocode.maps.co API
    
    Free tier: 25,000 requests @ 5 requests/second
    Then: 1 request/second
    """
    
    BASE_URL = "https://geocode.maps.co/search"
    
    def __init__(self):
        self.api_key = settings.GEOCODING_API_KEY
        self.cache = {}  # Simple in-memory cache to save API calls
    
    async def geocode_address(self, address: str) -> Optional[Tuple[float, float]]:
        """
        Convert address to (latitude, longitude) coordinates
        
        Args:
            address: Address string (e.g., "Colombo, Sri Lanka")
        
        Returns:
            Tuple of (lat, lon) or None if geocoding fails
        """
        
        # Check cache first
        if address in self.cache:
            return self.cache[address]
        
        if not self.api_key:
            print("  Geocoding API key not configured")
            return None
        
        try:
            params = {
                "q": address,
                "api_key": self.api_key
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(self.BASE_URL, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        if data and len(data) > 0:
                            # Take first result
                            result = data[0]
                            lat = float(result.get("lat"))
                            lon = float(result.get("lon"))
                            
                            # Cache result
                            self.cache[address] = (lat, lon)
                            
                            return (lat, lon)
                    
                    elif response.status == 429:
                        # Rate limited
                        print("  Geocoding API rate limit exceeded")
                        return None
                    
                    else:
                        print(f"  Geocoding failed: HTTP {response.status}")
                        return None
        
        except Exception as e:
            print(f" Geocoding error: {e}")
            return None
    
    def calculate_distance(
        self, 
        lat1: float, lon1: float, 
        lat2: float, lon2: float
    ) -> float:
        """
        Calculate distance between two coordinates using Haversine formula
        
        Args:
            lat1, lon1: First location coordinates
            lat2, lon2: Second location coordinates
        
        Returns:
            Distance in kilometers
        """
        
        # Earth's radius in kilometers
        R = 6371.0
        
        # Convert to radians
        lat1_rad = radians(lat1)
        lon1_rad = radians(lon1)
        lat2_rad = radians(lat2)
        lon2_rad = radians(lon2)
        
        # Haversine formula
        dlat = lat2_rad - lat1_rad
        dlon = lon2_rad - lon1_rad
        
        a = sin(dlat / 2)**2 + cos(lat1_rad) * cos(lat2_rad) * sin(dlon / 2)**2
        c = 2 * atan2(sqrt(a), sqrt(1 - a))
        
        distance = R * c
        
        return round(distance, 2)
    
    async def calculate_commute_distance(
        self, 
        cv_location: str, 
        job_location: str
    ) -> Tuple[float, str]:
        """
        Calculate commute distance between CV location and job location
        
        Args:
            cv_location: Candidate's current location (from CV)
            job_location: Job location (from job description)
        
        Returns:
            Tuple of (distance_km, risk_category)
            risk_category: "low", "medium", "high", "very_high"
        """
        
        # Handle remote jobs
        if "remote" in job_location.lower() or "remote" in cv_location.lower():
            return (0.0, "low")
        
        # Geocode both locations
        cv_coords = await self.geocode_address(cv_location)
        job_coords = await self.geocode_address(job_location)
        
        if not cv_coords or not job_coords:
            # Geocoding failed - return default moderate risk
            print(f"  Could not geocode: CV={cv_location}, Job={job_location}")
            return (0.0, "medium")  # Unknown distance = moderate risk
        
        # Calculate distance
        distance = self.calculate_distance(
            cv_coords[0], cv_coords[1],
            job_coords[0], job_coords[1]
        )
        
        # Categorize commute risk
        # Based on Sri Lankan context and traffic patterns
        if distance < 5:
            risk = "low"  # < 5 km - Very manageable
        elif distance < 15:
            risk = "medium"  # 5-15 km - Moderate commute
        elif distance < 30:
            risk = "high"  # 15-30 km - Long commute (especially in Colombo traffic)
        else:
            risk = "very_high"  # > 30 km - Very long commute
        
        return (distance, risk)
    
    def get_location_match_score(self, distance_km: float, commute_risk: str) -> float:
        """
        Convert commute distance/risk to a location match score (0.0 - 1.0)
        
        Args:
            distance_km: Commute distance in km
            commute_risk: Risk category ("low", "medium", "high", "very_high")
        
        Returns:
            Float score between 0.0 and 1.0
        """
        
        # Map risk categories to scores
        risk_scores = {
            "low": 1.0,
            "medium": 0.7,
            "high": 0.4,
            "very_high": 0.2
        }
        
        return risk_scores.get(commute_risk, 0.5)

# Singleton instance
_geocoding_service = None

def get_geocoding_service() -> GeocodingService:
    """Get or create geocoding service instance"""
    global _geocoding_service
    
    if _geocoding_service is None:
        _geocoding_service = GeocodingService()
    
    return _geocoding_service