"""
Electional astrology query client for the Astro Clock API.

This module provides a client for submitting electional astrology queries
and checking job status with the external Astro Clock API service.
It handles API errors gracefully and provides structured error
information for debugging.
"""

import logging
from dataclasses import dataclass
from datetime import date
from typing import Any
from urllib.parse import urljoin

import requests
from django.conf import settings

logger = logging.getLogger(__name__)


class QueryAPIError(Exception):
    """
    Base exception for electional query API errors.

    Attributes:
        status_code: HTTP status code from the API response
        error_message: User-friendly error message
        response_data: Raw response data if available
    """

    def __init__(
        self,
        message: str,
        status_code: int | None = None,
        response_data: dict[str, Any] | None = None,
    ):
        super().__init__(message)
        self.status_code = status_code
        self.error_message = message
        self.response_data = response_data

    def __str__(self) -> str:
        if self.status_code:
            return f"QueryAPIError({self.status_code}): {self.error_message}"
        return f"QueryAPIError: {self.error_message}"


class QueryTimeoutError(QueryAPIError):
    """
    Exception raised when the electional query API times out.

    This is a subclass of QueryAPIError with a None status_code
    to indicate a timeout rather than an HTTP error.
    """

    def __init__(self, message: str = "Query timed out"):
        super().__init__(message, status_code=None)
        self.error_message = message


@dataclass
class QueryRequest:
    """
    Request parameters for electional astrology queries.

    Electional astrology selects auspicious dates and times for
    specific activities such as weddings, projects, or travel.

    Attributes:
        query_type: Type of electional query (wedding, project, travel,
                   move_in, medical, other)
        description: Natural language description of the query intent
        latitude: Geographic latitude (-90 to 90)
        longitude: Geographic longitude (-180 to 180)
        location_name: Human-readable location name
        start_date: Start of date range to search
        end_date: End of date range to search
        preferences: Optional dict of user preferences for the election
    """

    query_type: str
    description: str
    latitude: float
    longitude: float
    location_name: str
    start_date: date
    end_date: date
    preferences: dict[str, Any] | None = None


def submit_query(request: QueryRequest) -> dict[str, Any]:
    """
    Submit an electional astrology query to the Astro Clock API.

    This initiates an async job that will analyze the date range
    and return auspicious electional candidates.

    Args:
        request: QueryRequest containing electional query parameters

    Returns:
        dict: API response containing:
            - job_id: Unique identifier for tracking the job
            - status: Initial job status ("pending")

    Raises:
        QueryAPIError: If the API returns an error response
        QueryTimeoutError: If the API request times out
    """
    import logging as _log

    _log = logging.getLogger(__name__)

    # Get API configuration
    base_url = settings.ASTRO_CLOCK_SERVER
    timeout = getattr(settings, "QUERY_API_TIMEOUT", 30)

    # Build request payload (API spec: start_date, days, sync)
    days = (request.end_date - request.start_date).days
    if days < 1:
        days = 1
    payload: dict[str, Any] = {
        "start_date": request.start_date.isoformat(),
        "days": days,
    }

    # Log the API call
    _log.info(
        "Submitting electional query: type=%s, location=%s, date_range=%s to %s (%d days)",
        request.query_type,
        request.location_name,
        request.start_date.isoformat(),
        request.end_date.isoformat(),
        days,
    )

    # Build API URL: query_type is a path variable
    api_url = urljoin(
        base_url.rstrip("/") + "/",
        f"api/v1/query/{request.query_type}",
    )

    try:
        response = requests.post(
            api_url,
            json=payload,
            timeout=timeout,
            headers={"Content-Type": "application/json"},
        )

        # Handle non-success responses
        if not response.ok:
            try:
                error_data = response.json()
                error_message = error_data.get(
                    "error", error_data.get("message", "Unknown error")
                )
            except ValueError:
                error_message = response.text or "Unknown error"

            _log.error(
                "Electional query API error: status=%s, message=%s",
                response.status_code,
                error_message,
            )
            raise QueryAPIError(
                message=error_message,
                status_code=response.status_code,
                response_data=error_data if "error_data" in locals() else None,
            )

        # Return successful response
        result = response.json()
        job_id = result.get("job_id", "unknown")
        _log.info("Electional query submitted successfully: job_id=%s", job_id)
        return result

    except requests.Timeout:
        _log.error("Electional query API timed out after %s seconds", timeout)
        raise QueryTimeoutError(f"Query timed out after {timeout} seconds")
    except requests.ConnectionError as e:
        _log.error("Electional query API connection error: %s", str(e))
        raise QueryAPIError(
            message=f"Could not connect to electional API server: {base_url}",
            status_code=None,
        )
    except requests.RequestException as e:
        _log.error("Electional query API request failed: %s", str(e))
        raise QueryAPIError(message=str(e))


def get_job_status(job_id: str) -> dict[str, Any]:
    """
    Check the status of an electional query job.

    Args:
        job_id: The job identifier returned from submit_query

    Returns:
        dict: API response containing:
            - job_id: The job identifier
            - status: Current status (pending, processing, completed, failed)
            - result: Electional results if completed
            - error: Error message if failed

    Raises:
        QueryAPIError: If the API returns an error response
        QueryTimeoutError: If the API request times out
    """
    import logging as _log

    _log = logging.getLogger(__name__)

    # Get API configuration
    base_url = settings.ASTRO_CLOCK_SERVER
    timeout = getattr(settings, "QUERY_API_TIMEOUT", 30)

    # Log the status check
    _log.info("Checking job status: job_id=%s", job_id)

    # Build API URL
    api_url = urljoin(base_url.rstrip("/") + "/", f"api/v1/jobs/{job_id}")

    try:
        response = requests.get(
            api_url, timeout=timeout, headers={"Accept": "application/json"}
        )

        # Handle non-success responses
        if not response.ok:
            try:
                error_data = response.json()
                error_message = error_data.get(
                    "error", error_data.get("message", "Unknown error")
                )
            except ValueError:
                error_message = response.text or "Unknown error"

            _log.error(
                "Job status API error: status=%s, job_id=%s, message=%s",
                response.status_code,
                job_id,
                error_message,
            )
            raise QueryAPIError(
                message=error_message,
                status_code=response.status_code,
                response_data=error_data if "error_data" in locals() else None,
            )

        # Return successful response
        result = response.json()
        status = result.get("status", "unknown")
        _log.info("Job status retrieved: job_id=%s, status=%s", job_id, status)
        return result

    except requests.Timeout:
        _log.error(
            "Job status API timed out after %s seconds: job_id=%s", timeout, job_id
        )
        raise QueryTimeoutError(f"Job status check timed out after {timeout} seconds")
    except requests.ConnectionError as e:
        _log.error("Job status API connection error: %s, job_id=%s", str(e), job_id)
        raise QueryAPIError(
            message=f"Could not connect to electional API server: {base_url}",
            status_code=None,
        )
    except requests.RequestException as e:
        _log.error("Job status API request failed: %s, job_id=%s", str(e), job_id)
        raise QueryAPIError(message=str(e))
