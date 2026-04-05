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
