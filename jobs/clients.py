"""
Job management client for the Astro Clock API.

This module provides a client for listing, inspecting, and deleting
jobs via the Astro Clock API service. It handles API errors gracefully
and provides structured error information for debugging.
"""

import logging
from typing import Any
from urllib.parse import urljoin

import requests
from django.conf import settings

logger = logging.getLogger(__name__)


class JobAPIError(Exception):
    """
    Base exception for job management API errors.

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
            return f"JobAPIError({self.status_code}): {self.error_message}"
        return f"JobAPIError: {self.error_message}"


class JobTimeoutError(JobAPIError):
    """
    Exception raised when the job management API times out.

    This is a subclass of JobAPIError with a None status_code
    to indicate a timeout rather than an HTTP error.
    """

    def __init__(self, message: str = "Job API request timed out"):
        super().__init__(message, status_code=None)
        self.error_message = message


def _get_api_url(path: str) -> str:
    """Build a full API URL from a relative path."""
    base_url = settings.ASTRO_CLOCK_SERVER
    return urljoin(base_url.rstrip("/") + "/", path)


def _get_timeout() -> int:
    """Get the configured API timeout in seconds."""
    return getattr(settings, "QUERY_API_TIMEOUT", 30)


def _handle_response(response: requests.Response, operation: str) -> dict[str, Any]:
    """
    Process an API response, raising JobAPIError for non-success status codes.

    Args:
        response: The requests Response object
        operation: Description of the operation (for error messages)

    Returns:
        Parsed JSON response dict

    Raises:
        JobAPIError: If the response indicates an error
    """
    if response.ok:
        return response.json()

    # Parse error from response
    error_data = None
    try:
        error_data = response.json()
        error_message = error_data.get(
            "error", error_data.get("message", "Unknown error")
        )
    except ValueError:
        error_message = response.text or "Unknown error"

    logger.error(
        "Job API error during %s: status=%s, message=%s",
        operation,
        response.status_code,
        error_message,
    )
    raise JobAPIError(
        message=error_message,
        status_code=response.status_code,
        response_data=error_data,
    )


def _handle_request_exception(
    exc: Exception, operation: str, job_id: str | None = None
) -> None:
    """
    Convert requests exceptions to appropriate JobAPIError subclasses.

    Args:
        exc: The caught requests exception
        operation: Description of the operation (for error messages)
        job_id: Optional job ID for context in log messages

    Raises:
        JobTimeoutError: For request timeouts
        JobAPIError: For connection and other request errors
    """
    base_url = settings.ASTRO_CLOCK_SERVER
    job_context = f", job_id={job_id}" if job_id else ""

    if isinstance(exc, requests.Timeout):
        timeout = _get_timeout()
        logger.error(
            "Job API timed out after %s seconds during %s%s",
            timeout,
            operation,
            job_context,
        )
        raise JobTimeoutError(
            f"Job API {operation} timed out after {timeout} seconds"
        )
    elif isinstance(exc, requests.ConnectionError):
        logger.error(
            "Job API connection error during %s%s: %s",
            operation,
            job_context,
            str(exc),
        )
        raise JobAPIError(
            message=f"Could not connect to API server: {base_url}",
            status_code=None,
        )
    else:
        logger.error(
            "Job API request failed during %s%s: %s",
            operation,
            job_context,
            str(exc),
        )
        raise JobAPIError(message=str(exc))


def list_jobs(
    *,
    status: str | None = None,
    job_type: str | None = None,
    created_after: str | None = None,
    created_before: str | None = None,
    cursor: str | None = None,
    count: int | None = None,
) -> dict[str, Any]:
    """
    List jobs from the Astro Clock API with filtering and cursor pagination.

    Args:
        status: Filter by job status (comma-separated for multi-value)
        job_type: Filter by job type (comma-separated for multi-value)
        created_after: Filter to jobs created on/after this timestamp
                      (RFC3339 or YYYY-MM-DD)
        created_before: Filter to jobs created on/before this timestamp
                       (RFC3339 or YYYY-MM-DD)
        cursor: Opaque cursor token for pagination
        count: Number of jobs per page (1-100, default 20)

    Returns:
        dict: API response containing:
            - jobs: List of job objects
            - next: URL for next page (null if last page)
            - prev: URL for previous page (null if first page)

    Raises:
        JobAPIError: If the API returns an error response
        JobTimeoutError: If the API request times out
    """
    api_url = _get_api_url("api/v1/jobs")
    timeout = _get_timeout()

    # Build query parameters, omitting None values
    params: dict[str, str | int] = {}
    if status is not None:
        params["status"] = status
    if job_type is not None:
        params["job_type"] = job_type
    if created_after is not None:
        params["created_after"] = created_after
    if created_before is not None:
        params["created_before"] = created_before
    if cursor is not None:
        params["cursor"] = cursor
    if count is not None:
        params["count"] = count

    logger.info(
        "Listing jobs: status=%s, job_type=%s, cursor=%s, count=%s",
        status,
        job_type,
        cursor,
        count,
    )

    try:
        response = requests.get(
            api_url,
            params=params,
            timeout=timeout,
            headers={"Accept": "application/json"},
        )
        result = _handle_response(response, "list_jobs")

        job_count = len(result.get("jobs", []))
        logger.info(
            "Listed %d jobs (next=%s, prev=%s)",
            job_count,
            result.get("next") is not None,
            result.get("prev") is not None,
        )
        return result

    except (requests.Timeout, requests.ConnectionError, requests.RequestException) as e:
        _handle_request_exception(e, "list_jobs")


def get_job(job_id: str) -> dict[str, Any]:
    """
    Retrieve details for a specific job from the Astro Clock API.

    Args:
        job_id: The job identifier (UUID)

    Returns:
        dict: API response containing:
            - job_id: The job identifier
            - job_type: Type of job (load, query, etc.)
            - status: Current status (pending, in_process, complete, failed)
            - result: Job output if completed
            - error: Error details if failed
            - created_at, updated_at, started_at, completed_at: Timestamps

    Raises:
        JobAPIError: If the API returns an error (e.g. 404 not found)
        JobTimeoutError: If the API request times out
    """
    api_url = _get_api_url(f"api/v1/jobs/{job_id}")
    timeout = _get_timeout()

    logger.info("Getting job details: job_id=%s", job_id)

    try:
        response = requests.get(
            api_url,
            timeout=timeout,
            headers={"Accept": "application/json"},
        )
        result = _handle_response(response, "get_job")

        logger.info(
            "Retrieved job: job_id=%s, status=%s",
            job_id,
            result.get("status", "unknown"),
        )
        return result

    except (requests.Timeout, requests.ConnectionError, requests.RequestException) as e:
        _handle_request_exception(e, "get_job", job_id=job_id)


def delete_job(job_id: str) -> bool:
    """
    Delete a job from the Astro Clock API.

    Args:
        job_id: The job identifier (UUID)

    Returns:
        True if the job was successfully deleted

    Raises:
        JobAPIError: If the API returns an error
            - 404: Job not found
            - 409: Cannot delete job in in_process status
        JobTimeoutError: If the API request times out
    """
    api_url = _get_api_url(f"api/v1/jobs/{job_id}")
    timeout = _get_timeout()

    logger.info("Deleting job: job_id=%s", job_id)

    try:
        response = requests.delete(
            api_url,
            timeout=timeout,
        )

        # Successful delete returns 204 No Content
        if response.status_code == 204:
            logger.info("Job deleted successfully: job_id=%s", job_id)
            return True

        # Any other non-success status
        _handle_response(response, "delete_job")
        # If _handle_response didn't raise, something unexpected happened
        # (2xx status other than 204 is odd but not an error)
        return True

    except (requests.Timeout, requests.ConnectionError, requests.RequestException) as e:
        _handle_request_exception(e, "delete_job", job_id=job_id)
