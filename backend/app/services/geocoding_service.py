import aiohttp
import asyncio
import re
from typing import Tuple, Optional
from math import radians, sin, cos, sqrt, atan2
from app.config import settings

class GeocodingService:
    """
    Service to geocode addresses and calculate commute distances
    Using geocode.maps.co API with Road Distance Correction Factor
    """
    
    BASE_URL = "https://geocode.maps.co/search"
    
    # Road distance multipliers for Sri Lanka
    # Based on geography, infrastructure, and traffic patterns
    ROAD_DISTANCE_MULTIPLIERS = {
        'colombo_metro': 1.3,      # Heavy traffic, indirect routes
        'western_urban': 1.4,       # Urban sprawl, bottlenecks
        'inter_province': 1.6,      # Mountain roads, limited highways
        'remote_areas': 1.8,        # Very limited road access
    }
    
    # Common Sri Lankan cities
    SL_CITIES = [
        'Colombo', 'Kandy', 'Galle', 'Jaffna', 'Negombo',
        'Anuradhapura', 'Trincomalee', 'Batticaloa', 'Matara',
        'Moratuwa', 'Maharagama', 'Nugegoda', 'Dehiwala', 'Kurunegala',
        'Ratnapura', 'Badulla', 'Kegalle', 'Kalutara', 'Gampaha',
        'Kelaniya', 'Malabe', 'Kaduwela', 'Panadura', 'Homagama',
        'Kadawatha', 'Wattala', 'Ja-Ela', 'Piliyandala', 'Horana',
        'Katugastota', 'Peradeniya', 'Matale', 'Nuwara Eliya',
        'Hambantota', 'Unawatuna', 'Weligama', 'Kilinochchi',
        'Vavuniya', 'Ampara', 'Kalmunai', 'Chilaw', 'Kuliyapitiya',
        'Polonnaruwa', 'Bandarawela', 'Ella', 'Pannipitiya', 'Arawwala',
        'Battaramulla', 'Rajagiriya', 'Nawala', 'Boralesgamuwa', 'Kotte',
        'Sri Jayawardenepura Kotte', 'Mount Lavinia', 'Dehiwala-Mount Lavinia',
        'Ratmalana', 'Kalubowila', 'Wellawatte', 'Bambalapitiya', 'Maradana',
        'Kollupitiya', 'Kotahena', 'Pettah', 'Fort', 'Slave Island',
        'Cinnamon Gardens', 'Havelock Town', 'Kirulapone', 'Pamankada',
        'Thimbirigasyaya', 'Narahenpita', 'Pelawatte', 'Thalawathugoda',
        'Athurugiriya', 'Hokandara', 'Godagama', 'Pitakotte',
        'Kohuwala', 'Mirihana', 'Kottawa', 'Udahamulla',
        'Seeduwa', 'Liyanagemulla', 'Bokundara'
    ]
    
    def __init__(self):
        self.api_key = settings.GEOCODING_API_KEY
        self.cache = {}
    
    def determine_route_type(self, location1: str, location2: str) -> str:
        """
        Determine route type based on locations to apply correct multiplier
        """
        loc1_lower = location1.lower()
        loc2_lower = location2.lower()
        
        # Colombo metro area cities
        colombo_metro = [
            'colombo', 'dehiwala', 'mount lavinia', 'moratuwa', 'nugegoda',
            'maharagama', 'kotte', 'battaramulla', 'rajagiriya', 'nawala',
            'wellawatte', 'bambalapitiya', 'maradana', 'kollupitiya', 'fort',
            'pettah', 'kotahena', 'kirulapone', 'narahenpita'
        ]
        
        # Western urban (outside Colombo but close)
        western_urban = [
            'gampaha', 'negombo', 'ja-ela', 'wattala', 'kelaniya',
            'kaduwela', 'malabe', 'pannipitiya', 'piliyandala', 'homagama',
            'kalutara', 'panadura', 'horana', 'kadawatha', 'seeduwa',
            'liyanagemulla', 'arawwala', 'bokundara'
        ]
        
        # Check if both locations are in Colombo metro
        both_colombo = any(c in loc1_lower for c in colombo_metro) and \
                      any(c in loc2_lower for c in colombo_metro)
        
        if both_colombo:
            return 'colombo_metro'
        
        # Check if one is Colombo metro, one is western urban
        one_colombo = any(c in loc1_lower for c in colombo_metro) or \
                     any(c in loc2_lower for c in colombo_metro)
        one_western = any(c in loc1_lower for c in western_urban) or \
                     any(c in loc2_lower for c in western_urban)
        
        if one_colombo and one_western:
            return 'western_urban'
        
        # Check for inter-province travel (e.g., Colombo to Kandy)
        major_cities = ['kandy', 'galle', 'jaffna', 'matara', 'anuradhapura', 
                       'trincomalee', 'batticaloa', 'kurunegala', 'ratnapura', 'badulla']
        
        one_colombo_or_western = (one_colombo or one_western)
        one_major_city = any(c in loc1_lower for c in major_cities) or \
                        any(c in loc2_lower for c in major_cities)
        
        if one_colombo_or_western and one_major_city:
            return 'inter_province'
        
        # Both in same western province
        both_western = any(c in loc1_lower for c in western_urban) and \
                      any(c in loc2_lower for c in western_urban)
        
        if both_western:
            return 'western_urban'
        
        # Default to remote areas
        return 'remote_areas'

    def clean_address_for_geocoding(self, address: str) -> str:
        """
        Simplify address to just city name for better geocoding success
        """
        if not address:
            return "Colombo, Sri Lanka"
        
        address_lower = address.lower()
        
        # Check if already in simple format
        for city in self.SL_CITIES:
            city_lower = city.lower()
            if address_lower == f"{city_lower}, sri lanka":
                return address
        
        # Remove common business identifiers
        address_clean = re.sub(
            r'\b(PLC|Ltd|Limited|Pvt|Private|Inc|Corporation|Company|Group)\b',
            '',
            address,
            flags=re.IGNORECASE
        )
        
        # Remove street-level details
        address_clean = re.sub(
            r'\b(Road|Street|Mawatha|Lane|Avenue|Drive|Place|Gardens)\b',
            '',
            address_clean,
            flags=re.IGNORECASE
        )
        
        # Remove P.O. Box, building numbers, floor numbers
        address_clean = re.sub(r'P\.?\s*O\.?\s*Box\s*\d+', '', address_clean, flags=re.IGNORECASE)
        address_clean = re.sub(r'\bNo\.?\s*\d+[A-Za-z]?[,\s]*', '', address_clean)
        address_clean = re.sub(r'\b\d+(?:st|nd|rd|th)?\s+Floor\b', '', address_clean, flags=re.IGNORECASE)
        address_clean = re.sub(r'\b\d+/\d+\b', '', address_clean)
        
        # Try to find a city name
        words = [w.strip() for w in address_clean.split(',')]
        for word in words:
            word_clean = word.strip()
            for city in self.SL_CITIES:
                if city.lower() in word_clean.lower():
                    return f"{city}, Sri Lanka"
        
        # Partial matching on original address
        for city in self.SL_CITIES:
            if city.lower() in address_lower:
                return f"{city}, Sri Lanka"
        
        # Check for postal codes
        colombo_match = re.search(r'colombo\s+\d{1,2}', address_lower, re.IGNORECASE)
        if colombo_match:
            return "Colombo, Sri Lanka"
        
        # Default fallback
        print(f"  Could not extract city from address: {address}, using Colombo as default")
        return "Colombo, Sri Lanka"

    async def geocode_address(self, address: str) -> Optional[Tuple[float, float]]:
        """
        Convert address to (latitude, longitude) coordinates
        """
        clean_address = self.clean_address_for_geocoding(address)
        
        # Check cache
        if clean_address in self.cache:
            return self.cache[clean_address]
        
        if not self.api_key:
            print("  Geocoding API key not configured")
            return None
        
        try:
            params = {
                "q": clean_address,
                "api_key": self.api_key
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(self.BASE_URL, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        if data and len(data) > 0:
                            result = data[0]
                            lat = float(result.get("lat"))
                            lon = float(result.get("lon"))
                            
                            # Cache result
                            self.cache[clean_address] = (lat, lon)
                            
                            return (lat, lon)
                        else:
                            print(f"  No results for: {clean_address}")
                            return None
                    elif response.status == 429:
                        print("  Geocoding API rate limit exceeded")
                        return None
                    else:
                        print(f"  Geocoding failed: HTTP {response.status} for {clean_address}")
                        return None
        
        except Exception as e:
            print(f"  Geocoding error for '{clean_address}': {e}")
            return None
    
    def calculate_haversine_distance(
        self,
        lat1: float, lon1: float,
        lat2: float, lon2: float
    ) -> float:
        """
        Calculate straight-line distance using Haversine formula
        Returns distance in kilometers
        """
        R = 6371.0  # Earth's radius in km
        
        lat1_rad = radians(lat1)
        lon1_rad = radians(lon1)
        lat2_rad = radians(lat2)
        lon2_rad = radians(lon2)
        
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
        Calculate commute distance with ROAD DISTANCE CORRECTION
        
        Returns:
            Tuple of (estimated_road_distance_km, risk_category)
        """
        
        # Handle remote jobs
        if "remote" in job_location.lower() or "remote" in cv_location.lower():
            print(" Remote job detected, distance = 0")
            return (0.0, "low")
        
        # Geocode both locations
        cv_coords = await self.geocode_address(cv_location)
        job_coords = await self.geocode_address(job_location)
        
        if not cv_coords or not job_coords:
            print(f"  Geocoding failed: CV={cv_location}, Job={job_location}")
            print(f"   Using default: distance=0, risk=medium")
            return (0.0, "medium")
        
        # Calculate straight-line distance
        haversine_distance = self.calculate_haversine_distance(
            cv_coords[0], cv_coords[1],
            job_coords[0], job_coords[1]
        )
        
        # Determine route type
        route_type = self.determine_route_type(cv_location, job_location)
        multiplier = self.ROAD_DISTANCE_MULTIPLIERS[route_type]
        
        # Calculate estimated road distance
        estimated_road_distance = haversine_distance * multiplier
    
        print(f"   Estimated road distance: {estimated_road_distance:.2f} km")
        
        # Categorize commute risk based on ROAD distance
        if estimated_road_distance < 5:
            risk = "low"
        elif estimated_road_distance < 15:
            risk = "medium"
        elif estimated_road_distance < 30:
            risk = "high"
        else:
            risk = "very_high"
        
        print(f"   Risk: {risk}")
        
        return (round(estimated_road_distance, 2), risk)
    
    def get_location_match_score(self, distance_km: float, commute_risk: str) -> float:
        """
        Convert commute distance/risk to location match score (0.0 - 1.0)
        """
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