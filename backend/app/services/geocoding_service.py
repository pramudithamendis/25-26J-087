import logging
import aiohttp
import asyncio
import re
from typing import Tuple, Optional, List
from math import radians, sin, cos, sqrt, atan2
from app.config import settings

logger = logging.getLogger(__name__)


class GeocodingService:
    """
    Service to geocode addresses and calculate commute distances.
    Optimized for Sri Lankan geography and traffic patterns.
    """

    BASE_URL = "https://geocode.maps.co/search"

    # --- Distance thresholds (km) for centroid correction ---
    CENTROID_CORRECTION_LARGE_THRESHOLD = 15
    CENTROID_CORRECTION_MODERATE_THRESHOLD = 10
    CENTROID_CORRECTION_MINOR_THRESHOLD = 6

    CENTROID_CORRECTION_LARGE_FACTOR = 0.50
    CENTROID_CORRECTION_MODERATE_FACTOR = 0.65
    CENTROID_CORRECTION_MINOR_FACTOR = 0.80

    # --- Minimum realistic commute distance (km) for close suburb pairs ---
    CLOSE_SUBURBS_MIN_DISTANCE_KM = 2.5

    # --- Risk category distance thresholds (km) ---
    RISK_LOW_MAX_KM = 6
    RISK_MEDIUM_MAX_KM = 18
    RISK_HIGH_MAX_KM = 35

    # --- API request timeout (seconds) ---
    API_TIMEOUT_SECONDS = 5

    # Earth radius used in Haversine formula (km)
    EARTH_RADIUS_KM = 6371.0

    # Road distance multipliers for Sri Lanka (straight-line to road distance conversion)
    ROAD_DISTANCE_MULTIPLIERS = {
        'colombo_metro': 1.20,     # Metro area with multiple routes
        'close_suburbs': 1.15,     # Very close neighbouring areas
        'western_urban': 1.35,     # Limited main roads, high congestion
        'inter_province': 1.5,     # Geographic curves/terrain
        'remote_areas': 1.7,       # Indirect rural road networks
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

    # Close neighbouring pairs (within 5–8 km typically)
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
        """Initialise the service with an API key and an empty in-memory cache."""
        self.api_key = settings.GEOCODING_API_KEY
        self.cache = {}

    def are_close_neighbors(self, location1: str, location2: str) -> bool:
        """
        Check whether two location strings are known close neighbours.

        Args:
            location1: First location name or address string.
            location2: Second location name or address string.

        Returns:
            True if the pair appears in the CLOSE_NEIGHBORS mapping, False otherwise.
        """
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
        """
        Determine the route category for two locations to select the correct
        road-distance multiplier.

        Args:
            location1: First location name or address string.
            location2: Second location name or address string.

        Returns:
            A key from ROAD_DISTANCE_MULTIPLIERS:
            'close_suburbs', 'colombo_metro', or 'western_urban'.
        """
        loc1, loc2 = location1.lower(), location2.lower()

        both_metro = (
            any(c in loc1 for c in self.COLOMBO_METRO_AREAS) and
            any(c in loc2 for c in self.COLOMBO_METRO_AREAS)
        )

        if both_metro:
            if self.are_close_neighbors(location1, location2):
                return 'close_suburbs'
            return 'colombo_metro'

        return 'western_urban'

    def clean_address_for_fallback(self, address: str) -> str:
        """
        Simplify an address string to "City, Sri Lanka" for fallback geocoding.

        Scans the address for any known Sri Lankan city name and returns
        a minimal query. Defaults to "Colombo, Sri Lanka" if no match is found.

        Args:
            address: Raw address string to simplify.

        Returns:
            A short geocoding query such as "Maharagama, Sri Lanka".
        """
        address_lower = address.lower()
        for city in self.SL_CITIES:
            if city.lower() in address_lower:
                return f"{city}, Sri Lanka"
        return "Colombo, Sri Lanka"

    async def _call_api(self, query: str) -> Optional[Tuple[float, float]]:
        """
        Call the geocoding API for a single query string.

        Results are cached in memory by query string to avoid redundant
        network calls within the same service lifetime.

        Args:
            query: The address or place name to geocode.

        Returns:
            A (latitude, longitude) tuple on success, or None if the API
            returns no results or an error occurs.
        """
        if query in self.cache:
            logger.debug("Cache hit for geocoding query: %s", query)
            return self.cache[query]

        try:
            params = {"q": query, "api_key": self.api_key}
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    self.BASE_URL, params=params, timeout=self.API_TIMEOUT_SECONDS
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        if data and len(data) > 0:
                            lat, lon = float(data[0]["lat"]), float(data[0]["lon"])
                            self.cache[query] = (lat, lon)
                            logger.debug(
                                "Geocoded '%s' -> (%.6f, %.6f)", query, lat, lon
                            )
                            return (lat, lon)
                    else:
                        logger.warning(
                            "Geocoding API returned status %d for query: %s",
                            response.status, query
                        )
            return None
        except Exception as e:
            logger.error("Geocoding API error for query '%s': %s", query, e)
            return None

    async def geocode_address(self, address: str) -> Optional[Tuple[float, float]]:
        """
        Geocode an address using a two-step strategy.

        Step 1 tries the full address for a precise result.
        Step 2 falls back to a city-only query if step 1 returns nothing.

        Args:
            address: Full address string to geocode.

        Returns:
            A (latitude, longitude) tuple on success, or None if both
            attempts fail.
        """
        if not address:
            return None

        logger.debug("Geocoding address: %s", address)

        # Step 1: Precise search (street + city)
        coords = await self._call_api(address)
        if coords:
            return coords

        # Step 2: Fallback (city only)
        fallback_query = self.clean_address_for_fallback(address)
        logger.debug("Falling back to city-only query: %s", fallback_query)
        return await self._call_api(fallback_query)

    def calculate_haversine_distance(
        self, lat1: float, lon1: float, lat2: float, lon2: float
    ) -> float:
        """
        Calculate the straight-line (great-circle) distance between two
        geographic coordinates using the Haversine formula.

        Args:
            lat1: Latitude of the first point in decimal degrees.
            lon1: Longitude of the first point in decimal degrees.
            lat2: Latitude of the second point in decimal degrees.
            lon2: Longitude of the second point in decimal degrees.

        Returns:
            Distance in kilometres.
        """
        dlat = radians(lat2 - lat1)
        dlon = radians(lon2 - lon1)
        a = (
            sin(dlat / 2) ** 2
            + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
        )
        return self.EARTH_RADIUS_KM * (2 * atan2(sqrt(a), sqrt(1 - a)))

    async def calculate_commute_distance(
        self, cv_location: str, job_location: str
    ) -> Tuple[float, str]:
        """
        Estimate the road distance between a candidate's location and a job
        location, and classify the commute into a risk category.

        Steps:
            1. Return zero distance / low risk for remote roles.
            2. Geocode both addresses.
            3. Compute the Haversine (straight-line) distance.
            4. Determine the route type and apply the appropriate road
               distance multiplier.
            5. Apply centroid correction for metro-area results.
            6. Enforce a minimum realistic distance for close suburb pairs.
            7. Classify the result into low / medium / high / very_high risk.

        Args:
            cv_location: Candidate's home location string.
            job_location: Job's location string.

        Returns:
            A tuple of (road_distance_km, risk_category) where risk_category
            is one of "low", "medium", "high", or "very_high".
            Returns (0.0, "medium") when geocoding fails for either location.
        """
        # 1. Handle remote roles
        if any(x in job_location.lower() for x in ["remote", "work from home"]):
            logger.debug("Job location is remote; returning zero commute distance.")
            return (0.0, "low")

        # 2. Get coordinates
        logger.debug(
            "Calculating commute distance: '%s' -> '%s'", cv_location, job_location
        )
        cv_coords = await self.geocode_address(cv_location)
        job_coords = await self.geocode_address(job_location)

        if not cv_coords or not job_coords:
            logger.warning(
                "Geocoding failed for one or both locations: cv='%s', job='%s'",
                cv_location, job_location
            )
            return (0.0, "medium")

        # 3. Calculate base straight-line distance
        base_dist = self.calculate_haversine_distance(
            cv_coords[0], cv_coords[1], job_coords[0], job_coords[1]
        )
        logger.debug("Haversine distance: %.2f km", base_dist)

        # 4. Determine route type and apply multiplier
        route_type = self.determine_route_type(cv_location, job_location)
        multiplier = self.ROAD_DISTANCE_MULTIPLIERS.get(route_type, 1.4)
        road_dist = base_dist * multiplier
        logger.debug(
            "Route type: %s | Multiplier: %.2f | Road distance: %.2f km",
            route_type, multiplier, road_dist
        )

        # 5. Apply centroid correction for metro areas
        if route_type in ['colombo_metro', 'close_suburbs']:
            if road_dist > self.CENTROID_CORRECTION_LARGE_THRESHOLD:
                road_dist *= self.CENTROID_CORRECTION_LARGE_FACTOR
            elif road_dist > self.CENTROID_CORRECTION_MODERATE_THRESHOLD:
                road_dist *= self.CENTROID_CORRECTION_MODERATE_FACTOR
            elif road_dist > self.CENTROID_CORRECTION_MINOR_THRESHOLD:
                road_dist *= self.CENTROID_CORRECTION_MINOR_FACTOR
            logger.debug("After centroid correction: %.2f km", road_dist)

        # 6. Enforce minimum realistic distance for close suburb pairs
        if route_type == 'close_suburbs' and road_dist < self.CLOSE_SUBURBS_MIN_DISTANCE_KM:
            road_dist = max(road_dist, self.CLOSE_SUBURBS_MIN_DISTANCE_KM)
            logger.debug(
                "Applied minimum close-suburb distance floor: %.2f km", road_dist
            )

        # 7. Categorise risk
        if road_dist < self.RISK_LOW_MAX_KM:
            risk = "low"
        elif road_dist < self.RISK_MEDIUM_MAX_KM:
            risk = "medium"
        elif road_dist < self.RISK_HIGH_MAX_KM:
            risk = "high"
        else:
            risk = "very_high"

        logger.info(
            "Commute '%s' -> '%s': %.2f km (%s risk)",
            cv_location, job_location, road_dist, risk
        )
        return (round(road_dist, 2), risk)

    def get_location_match_score(self, distance_km: float, commute_risk: str) -> float:
        """
        Convert a commute risk category into a normalised matching score.

        Args:
            distance_km: Estimated road distance in kilometres (unused directly,
                         retained for a consistent interface).
            commute_risk: One of "low", "medium", "high", or "very_high".

        Returns:
            A float score between 0.0 and 1.0; higher means a better location
            match. Defaults to 0.5 for unrecognised risk values.
        """
        risk_scores = {
            "low": 1.0,
            "medium": 0.8,
            "high": 0.4,
            "very_high": 0.1,
        }
        score = risk_scores.get(commute_risk, 0.5)
        logger.debug(
            "Location match score for risk '%s': %.2f", commute_risk, score
        )
        return score


# Singleton
_geocoding_service = None


def get_geocoding_service() -> GeocodingService:
    """
    Return the module-level singleton instance of GeocodingService.

    Creates the instance on first call and reuses it on subsequent calls,
    preserving the in-memory geocoding cache across requests.

    Returns:
        The shared GeocodingService instance.
    """
    global _geocoding_service
    if _geocoding_service is None:
        logger.debug("Initialising GeocodingService singleton.")
        _geocoding_service = GeocodingService()
    return _geocoding_service