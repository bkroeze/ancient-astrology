"""
Chart generation client for the Astro Clock API.

This module provides a client for generating natal charts by communicating
with an external Astro Clock API service. It handles API errors gracefully
and provides structured error information for debugging.
"""
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any
from urllib.parse import urljoin

import requests
from django.conf import settings

logger = logging.getLogger(__name__)


class ChartAPIError(Exception):
    """
    Base exception for chart generation API errors.
    
    Attributes:
        status_code: HTTP status code from the API response
        error_message: User-friendly error message
        response_data: Raw response data if available
    """
    
    def __init__(
        self, 
        message: str, 
        status_code: int | None = None, 
        response_data: dict[str, Any] | None = None
    ):
        super().__init__(message)
        self.status_code = status_code
        self.error_message = message
        self.response_data = response_data
    
    def __str__(self) -> str:
        if self.status_code:
            return f"ChartAPIError({self.status_code}): {self.error_message}"
        return f"ChartAPIError: {self.error_message}"


class ChartTimeoutError(ChartAPIError):
    """
    Exception raised when the chart generation API times out.
    
    This is a subclass of ChartAPIError with a None status_code
    to indicate a timeout rather than an HTTP error.
    """
    def __init__(self, message: str = "Chart generation timed out"):
        super().__init__(message, status_code=None)
        self.error_message = message


@dataclass
class ChartRequest:
    """
    Request parameters for chart generation.
    
    Attributes:
        latitude: Geographic latitude (-90 to 90)
        longitude: Geographic longitude (-180 to 180)
        datetime: Date and time for the chart (UTC)
        format: Output format ('svg', 'png', 'json')
        name: Optional name for the chart
    """
    latitude: float
    longitude: float
    datetime: datetime
    format: str = 'svg'
    name: str | None = None


def generate_chart(request: ChartRequest) -> dict[str, Any]:
    """
    Generate a natal chart by calling the Astro Clock API.
    
    Args:
        request: ChartRequest containing chart parameters
        
    Returns:
        dict: API response containing chart data
        
    Raises:
        ChartAPIError: If the API returns an error response
        ChartTimeoutError: If the API request times out
    """
    import logging
    _log = logging.getLogger(__name__)
    
    # Get API configuration
    base_url = settings.ASTRO_CLOCK_SERVER
    timeout = getattr(settings, 'CHART_API_TIMEOUT', 30)
    
    # Build request payload
    payload = {
        'latitude': request.latitude,
        'longitude': request.longitude,
        'datetime': request.datetime.isoformat(),
        'format': request.format,
    }
    if request.name:
        payload['name'] = request.name
    
    # Log the API call
    _log.info(
        "Generating chart: lat=%s, lon=%s, datetime=%s, format=%s",
        request.latitude, 
        request.longitude, 
        request.datetime.isoformat(),
        request.format
    )
    
    # Build API URL
    api_url = urljoin(base_url.rstrip('/') + '/', 'api/chart/generate')
    
    try:
        response = requests.post(
            api_url,
            json=payload,
            timeout=timeout,
            headers={'Content-Type': 'application/json'}
        )
        
        # Handle non-success responses
        if not response.ok:
            try:
                error_data = response.json()
                error_message = error_data.get('error', error_data.get('message', 'Unknown error'))
            except ValueError:
                error_message = response.text or 'Unknown error'
            
            _log.error(
                "Chart API error: status=%s, message=%s",
                response.status_code,
                error_message
            )
            raise ChartAPIError(
                message=error_message,
                status_code=response.status_code,
                response_data=error_data if 'error_data' in locals() else None
            )
        
        # Return successful response
        result = response.json()
        _log.info("Chart generated successfully")
        return result
        
    except requests.Timeout:
        _log.error("Chart API timed out after %s seconds", timeout)
        raise ChartTimeoutError(
            f"Chart generation timed out after {timeout} seconds"
        )
    except requests.ConnectionError as e:
        _log.error("Chart API connection error: %s", str(e))
        raise ChartAPIError(
            message=f"Could not connect to chart server: {base_url}",
            status_code=None
        )
    except requests.RequestException as e:
        _log.error("Chart API request failed: %s", str(e))
        raise ChartAPIError(message=str(e))


@dataclass
class AnalysisRequest:
    """
    Request parameters for chart analysis data (planets, houses, aspects).
    
    Attributes:
        latitude: Geographic latitude (-90 to 90)
        longitude: Geographic longitude (-180 to 180)
        datetime: Date and time for the chart (UTC)
        house_system: House system to use (default: 'P' for Placidus)
    """
    latitude: float
    longitude: float
    datetime: datetime
    house_system: str = 'P'


# =============================================================================
# Geocoding Client (Photon API)
# =============================================================================

class GeocodingError(Exception):
    """
    Exception raised when geocoding API requests fail.
    
    Attributes:
        status_code: HTTP status code from the API response (None for network/timeout errors)
        error_message: User-friendly error message
    """
    
    def __init__(
        self,
        message: str,
        status_code: int | None = None,
    ):
        super().__init__(message)
        self.status_code = status_code
        self.error_message = message
    
    def __str__(self) -> str:
        if self.status_code:
            return f"GeocodingError({self.status_code}): {self.error_message}"
        return f"GeocodingError: {self.error_message}"


@dataclass
class GeocodingRequest:
    """
    Request parameters for location geocoding.
    
    Attributes:
        query: Search query string (location name)
        limit: Maximum number of results to return (default: 5)
    """
    query: str
    limit: int = 5


@dataclass
class GeocodingResult:
    """
    Result from a geocoding query.
    
    Attributes:
        name: Full location name
        latitude: Geographic latitude
        longitude: Geographic longitude
        timezone: IANA timezone string (e.g., 'America/New_York')
        country: Country name
        state: State or region name
    """
    name: str
    latitude: float
    longitude: float
    timezone: str | None
    country: str | None
    state: str | None


@dataclass
class ReverseGeocodingRequest:
    """
    Request parameters for reverse geocoding.
    
    Attributes:
        latitude: Latitude in decimal degrees (-90 to 90)
        longitude: Longitude in decimal degrees (-180 to 180)
    """
    latitude: float
    longitude: float


def geocode_location(request: GeocodingRequest) -> list[GeocodingResult]:
    """
    Search for locations by name using the Photon geocoding API.
    
    Args:
        request: GeocodingRequest containing the search query
        
    Returns:
        list[GeocodingResult]: Matching locations with coordinates and metadata
        
    Raises:
        GeocodingError: If the API returns an error or request fails
    """
    import logging
    _log = logging.getLogger(__name__)
    
    base_url = getattr(settings, 'PHOTON_API_URL', 'https://photon.komoot.io')
    timeout = getattr(settings, 'GEOCODING_TIMEOUT', 10)
    
    api_url = urljoin(base_url.rstrip('/') + '/', 'api/')
    params = {
        'q': request.query,
        'limit': request.limit,
    }
    
    _log.info("Geocoding location: query=%s, limit=%d", request.query, request.limit)
    
    try:
        response = requests.get(
            api_url,
            params=params,
            timeout=timeout,
            headers={
                'Accept': 'application/json',
                'User-Agent': 'AncientAstrology/1.0 (https://github.com/bkroeze/ancient-astrology)'
            }
        )

        if not response.ok:
            try:
                error_detail = response.json().get('error', response.text)
            except ValueError:
                error_detail = response.text or 'Unknown error'

            _log.error(
                "Geocoding API error: status=%s, detail=%s",
                response.status_code,
                error_detail
            )
            raise GeocodingError(
                message=f"Geocoding failed: {error_detail}",
                status_code=response.status_code,
            )
        
        try:
            data = response.json()
        except ValueError as e:
            _log.error("Geocoding API returned malformed JSON: %s", str(e))
            raise GeocodingError(
                message=f"Invalid JSON response from geocoding service: {str(e)}",
            )
        results: list[GeocodingResult] = []
        
        # Photon returns GeoJSON FeatureCollection
        features = data.get('features', [])
        for feature in features:
            props = feature.get('properties', {})
            geometry = feature.get('geometry', {})
            coords = geometry.get('coordinates', [])
            
            # coords is [longitude, latitude]
            longitude = coords[0] if len(coords) > 0 else 0.0
            latitude = coords[1] if len(coords) > 1 else 0.0
            
            # Extract optional timezone from extent
            extent = props.get('extent', {})
            timezone = extent.get('timezone') if isinstance(extent, dict) else None

            # Fallback: use timezonefinder for secondary timezone lookup
            if not timezone:
                try:
                    from timezonefinder import TimezoneFinder
                    tf = TimezoneFinder()
                    timezone = tf.timezone_at(lng=longitude, lat=latitude)
                except Exception:
                    pass  # timezone will remain None

            result = GeocodingResult(
                name=props.get('name', ''),
                latitude=latitude,
                longitude=longitude,
                timezone=timezone,
                country=props.get('country'),
                state=props.get('state'),
            )
            results.append(result)
        
        _log.info(
            "Geocoding complete: query=%s, results=%d",
            request.query,
            len(results)
        )
        return results
        
    except requests.Timeout:
        _log.error("Geocoding API timed out after %s seconds", timeout)
        raise GeocodingError(
            message=f"Geocoding timed out after {timeout} seconds",
        )
    except requests.ConnectionError as e:
        _log.error("Geocoding API connection error: %s", str(e))
        raise GeocodingError(
            message=f"Could not connect to geocoding server: {base_url}",
        )
    except requests.RequestException as e:
        _log.error("Geocoding API request failed: %s", str(e))
        raise GeocodingError(message=str(e))


def reverse_geocode_location(lat: float, lon: float) -> GeocodingResult | None:
    """
    Reverse geocode latitude/longitude to a location using the Photon API.
    
    Args:
        lat: Latitude in decimal degrees (-90 to 90)
        lon: Longitude in decimal degrees (-180 to 180)
        
    Returns:
        GeocodingResult | None: The location result, or None if no results found
        
    Raises:
        GeocodingError: If the API returns an error or request fails
    """
    import logging
    _log = logging.getLogger(__name__)
    
    base_url = getattr(settings, 'PHOTON_API_URL', 'https://photon.komoot.io')
    timeout = getattr(settings, 'GEOCODING_TIMEOUT', 10)
    
    api_url = f"{base_url.rstrip('/')}/reverse"
    params = {
        'lat': lat,
        'lon': lon,
    }
    
    _log.info("Reverse geocoding: lat=%s, lon=%s", lat, lon)
    
    try:
        response = requests.get(
            api_url,
            params=params,
            timeout=timeout,
            headers={
                'Accept': 'application/json',
                'User-Agent': 'AncientAstrology/1.0 (https://github.com/bkroeze/ancient-astrology)'
            }
        )

        if not response.ok:
            try:
                error_detail = response.json().get('error', response.text)
            except ValueError:
                error_detail = response.text or 'Unknown error'

            _log.error(
                "Reverse geocoding API error: status=%s, detail=%s",
                response.status_code,
                error_detail
            )
            raise GeocodingError(
                message=f"Reverse geocoding failed: {error_detail}",
                status_code=response.status_code,
            )
        
        try:
            data = response.json()
        except ValueError as e:
            _log.error("Reverse geocoding API returned malformed JSON: %s", str(e))
            raise GeocodingError(
                message=f"Invalid JSON response from geocoding service: {str(e)}",
            )
        
        # Photon returns GeoJSON FeatureCollection
        features = data.get('features', [])
        if not features:
            _log.info("Reverse geocoding: no results found")
            return None
        
        # Take the first (best) result
        feature = features[0]
        props = feature.get('properties', {})
        geometry = feature.get('geometry', {})
        coords = geometry.get('coordinates', [])
        
        # coords is [longitude, latitude]
        longitude = coords[0] if len(coords) > 0 else lon
        latitude = coords[1] if len(coords) > 1 else lat
        
        # Extract optional timezone from extent
        extent = props.get('extent', {})
        timezone = extent.get('timezone') if isinstance(extent, dict) else None

        # Fallback: use timezonefinder for secondary timezone lookup
        if not timezone:
            try:
                from timezonefinder import TimezoneFinder
                tf = TimezoneFinder()
                timezone = tf.timezone_at(lng=lon, lat=lat)
                if timezone:
                    _log.info("Timezone resolved via timezonefinder: %s", timezone)
            except Exception as e:
                _log.warning("Timezone lookup failed: %s", str(e))

        # Build a readable name from components
        name_parts = []
        if props.get('name'):
            name_parts.append(props.get('name'))
        if props.get('street'):
            name_parts.append(props.get('street'))
        if props.get('city'):
            name_parts.append(props.get('city'))
        if props.get('state'):
            name_parts.append(props.get('state'))
        if props.get('country'):
            name_parts.append(props.get('country'))
        
        # Fallback to coordinates if no name
        name = ', '.join(name_parts) if name_parts else f"{lat}, {lon}"
        
        result = GeocodingResult(
            name=name,
            latitude=latitude,
            longitude=longitude,
            timezone=timezone,
            country=props.get('country'),
            state=props.get('state'),
        )
        
        _log.info(
            "Reverse geocoding complete: lat=%s, lon=%s, name=%s",
            lat, lon, name
        )
        return result
        
    except requests.Timeout:
        _log.error("Reverse geocoding API timed out after %s seconds", timeout)
        raise GeocodingError(
            message=f"Reverse geocoding timed out after {timeout} seconds",
        )
    except requests.ConnectionError as e:
        _log.error("Reverse geocoding API connection error: %s", str(e))
        raise GeocodingError(
            message=f"Could not connect to geocoding server: {base_url}",
        )
    except requests.RequestException as e:
        _log.error("Reverse geocoding API request failed: %s", str(e))
        raise GeocodingError(message=str(e))


def get_chart_data(request: AnalysisRequest) -> dict[str, Any]:
    """
    Fetch chart analysis data (planets, houses, aspects) from the Astro Clock API.
    
    Args:
        request: AnalysisRequest containing analysis parameters
        
    Returns:
        dict: API response containing:
            - planets: List of planet positions
            - houses: House cusp data
            - aspects: List of aspects between planets
            - grand_trines: List of grand trine configurations
            - moon_void_of_course: Whether Moon is void of course
            - metadata: Calculation metadata (lat, lon, julian_day, house_system)
        
    Raises:
        ChartAPIError: If the API returns an error response
        ChartTimeoutError: If the API request times out
    """
    import logging
    _log = logging.getLogger(__name__)
    
    # Get API configuration
    base_url = settings.ASTRO_CLOCK_SERVER
    timeout = getattr(settings, 'CHART_API_TIMEOUT', 30)
    
    # Build request query parameters
    params = {
        'lat': request.latitude,
        'lon': request.longitude,
    }
    
    # Log the API call
    _log.info(
        "Fetching chart analysis data: lat=%s, lon=%s, datetime=%s, house_system=%s",
        request.latitude, 
        request.longitude, 
        request.datetime.isoformat(),
        request.house_system
    )
    
    # Build API URL
    api_url = urljoin(base_url.rstrip('/') + '/', 'api/v1/chart/data')
    
    try:
        response = requests.get(
            api_url,
            params=params,
            timeout=timeout,
            headers={'Accept': 'application/json'}
        )
        
        # Handle non-success responses
        if not response.ok:
            try:
                error_data = response.json()
                error_message = error_data.get('error', error_data.get('message', 'Unknown error'))
            except ValueError:
                error_message = response.text or 'Unknown error'
            
            _log.error(
                "Chart analysis API error: status=%s, message=%s",
                response.status_code,
                error_message
            )
            raise ChartAPIError(
                message=error_message,
                status_code=response.status_code,
                response_data=error_data if 'error_data' in locals() else None
            )
        
        # Return successful response
        result = response.json()
        _log.info(
            "Chart analysis data fetched successfully: %d planets, %d aspects",
            len(result.get('planets', [])),
            len(result.get('aspects', []))
        )
        return result
        
    except requests.Timeout:
        _log.error("Chart analysis API timed out after %s seconds", timeout)
        raise ChartTimeoutError(
            f"Chart analysis timed out after {timeout} seconds"
        )
    except requests.ConnectionError as e:
        _log.error("Chart analysis API connection error: %s", str(e))
        raise ChartAPIError(
            message=f"Could not connect to chart server: {base_url}",
            status_code=None
        )
    except requests.RequestException as e:
        _log.error("Chart analysis API request failed: %s", str(e))
        raise ChartAPIError(message=str(e))
