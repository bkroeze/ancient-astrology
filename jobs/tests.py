"""
Tests for jobs app: API client layer (list_jobs, get_job, delete_job),
JobListView (staff-only access, filters, cursor pagination), and
JobDetailView (HTMX partial with metadata and action buttons).
"""

import json
from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

from jobs.clients import JobAPIError, JobTimeoutError, delete_job, get_job, list_jobs


# =============================================================================
# ERROR CLASS TESTS
# =============================================================================


class JobAPIErrorTests(TestCase):
    """Tests for JobAPIError exception."""

    def test_error_with_status_code(self):
        """JobAPIError includes status code in string representation."""
        error = JobAPIError("Bad request", status_code=400)
        self.assertEqual(str(error), "JobAPIError(400): Bad request")
        self.assertEqual(error.status_code, 400)
        self.assertEqual(error.error_message, "Bad request")

    def test_error_without_status_code(self):
        """JobAPIError without status code omits it from string."""
        error = JobAPIError("Connection failed")
        self.assertIsNone(error.status_code)
        self.assertEqual(str(error), "JobAPIError: Connection failed")

    def test_error_with_response_data(self):
        """JobAPIError preserves response_data dict."""
        data = {"field": "status", "error": "invalid value"}
        error = JobAPIError("Bad request", status_code=400, response_data=data)
        self.assertEqual(error.response_data["field"], "status")

    def test_error_response_data_defaults_none(self):
        """JobAPIError response_data defaults to None."""
        error = JobAPIError("Error")
        self.assertIsNone(error.response_data)


class JobTimeoutErrorTests(TestCase):
    """Tests for JobTimeoutError exception."""

    def test_timeout_is_subclass_of_job_api_error(self):
        """JobTimeoutError inherits from JobAPIError."""
        error = JobTimeoutError()
        self.assertIsInstance(error, JobAPIError)

    def test_timeout_default_message(self):
        """JobTimeoutError has sensible default message."""
        error = JobTimeoutError()
        self.assertEqual(error.error_message, "Job API request timed out")
        self.assertIsNone(error.status_code)

    def test_timeout_custom_message(self):
        """JobTimeoutError accepts custom message."""
        error = JobTimeoutError("Custom timeout")
        self.assertEqual(error.error_message, "Custom timeout")


# =============================================================================
# LIST_JOBS TESTS
# =============================================================================


@override_settings(ASTRO_CLOCK_SERVER="http://localhost:8086", QUERY_API_TIMEOUT=30)
class ListJobsTests(TestCase):
    """Tests for list_jobs function."""

    @patch("jobs.clients.requests.get")
    def test_list_jobs_no_filters(self, mock_get):
        """List jobs with no filters returns paginated result."""
        mock_response = MagicMock()
        mock_response.ok = True
        mock_response.json.return_value = {
            "jobs": [
                {"job_id": "j1", "status": "complete", "job_type": "load"},
                {"job_id": "j2", "status": "pending", "job_type": "query"},
            ],
            "next": "/api/v1/jobs?cursor=abc",
            "prev": None,
        }
        mock_get.return_value = mock_response

        result = list_jobs()

        self.assertEqual(len(result["jobs"]), 2)
        self.assertEqual(result["jobs"][0]["job_id"], "j1")
        self.assertIsNotNone(result["next"])
        self.assertIsNone(result["prev"])
        mock_get.assert_called_once()

    @patch("jobs.clients.requests.get")
    def test_list_jobs_with_status_filter(self, mock_get):
        """List jobs passes status filter as query param."""
        mock_response = MagicMock()
        mock_response.ok = True
        mock_response.json.return_value = {"jobs": [], "next": None, "prev": None}
        mock_get.return_value = mock_response

        list_jobs(status="complete,failed")

        call_kwargs = mock_get.call_args
        self.assertEqual(call_kwargs.kwargs["params"]["status"], "complete,failed")

    @patch("jobs.clients.requests.get")
    def test_list_jobs_with_job_type_filter(self, mock_get):
        """List jobs passes job_type filter as query param."""
        mock_response = MagicMock()
        mock_response.ok = True
        mock_response.json.return_value = {"jobs": [], "next": None, "prev": None}
        mock_get.return_value = mock_response

        list_jobs(job_type="load")

        call_kwargs = mock_get.call_args
        self.assertEqual(call_kwargs.kwargs["params"]["job_type"], "load")

    @patch("jobs.clients.requests.get")
    def test_list_jobs_with_date_filters(self, mock_get):
        """List jobs passes created_after and created_before params."""
        mock_response = MagicMock()
        mock_response.ok = True
        mock_response.json.return_value = {"jobs": [], "next": None, "prev": None}
        mock_get.return_value = mock_response

        list_jobs(created_after="2025-01-01", created_before="2025-03-01")

        call_kwargs = mock_get.call_args
        params = call_kwargs.kwargs["params"]
        self.assertEqual(params["created_after"], "2025-01-01")
        self.assertEqual(params["created_before"], "2025-03-01")

    @patch("jobs.clients.requests.get")
    def test_list_jobs_with_cursor_and_count(self, mock_get):
        """List jobs passes cursor and count pagination params."""
        mock_response = MagicMock()
        mock_response.ok = True
        mock_response.json.return_value = {"jobs": [], "next": None, "prev": None}
        mock_get.return_value = mock_response

        list_jobs(cursor="eyJjcmVhdGVkX2F0IjoiMjAyNS0wMSJ9", count=50)

        call_kwargs = mock_get.call_args
        params = call_kwargs.kwargs["params"]
        self.assertEqual(params["cursor"], "eyJjcmVhdGVkX2F0IjoiMjAyNS0wMSJ9")
        self.assertEqual(params["count"], 50)

    @patch("jobs.clients.requests.get")
    def test_list_jobs_omits_none_params(self, mock_get):
        """List jobs does not send params that are None."""
        mock_response = MagicMock()
        mock_response.ok = True
        mock_response.json.return_value = {"jobs": [], "next": None, "prev": None}
        mock_get.return_value = mock_response

        list_jobs(status="complete")

        params = mock_get.call_args.kwargs["params"]
        self.assertEqual(len(params), 1)
        self.assertIn("status", params)
        self.assertNotIn("job_type", params)
        self.assertNotIn("cursor", params)
        self.assertNotIn("count", params)

    @patch("jobs.clients.requests.get")
    def test_list_jobs_api_error(self, mock_get):
        """List jobs raises JobAPIError on non-success response."""
        mock_response = MagicMock()
        mock_response.ok = False
        mock_response.status_code = 400
        mock_response.json.return_value = {
            "error": "invalid_status",
            "message": "Invalid status value: unknown",
        }
        mock_response.text = '{"error": "invalid_status"}'
        mock_get.return_value = mock_response

        with self.assertRaises(JobAPIError) as ctx:
            list_jobs(status="unknown")

        self.assertEqual(ctx.exception.status_code, 400)

    @patch("jobs.clients.requests.get")
    def test_list_jobs_timeout(self, mock_get):
        """List jobs raises JobTimeoutError on timeout."""
        import requests

        mock_get.side_effect = requests.Timeout("Connection timed out")

        with self.assertRaises(JobTimeoutError):
            list_jobs()

    @patch("jobs.clients.requests.get")
    def test_list_jobs_connection_error(self, mock_get):
        """List jobs raises JobAPIError on connection failure."""
        import requests

        mock_get.side_effect = requests.ConnectionError("Connection refused")

        with self.assertRaises(JobAPIError) as ctx:
            list_jobs()

        self.assertIsNone(ctx.exception.status_code)
        self.assertIn("Could not connect", ctx.exception.error_message)

    @patch("jobs.clients.requests.get")
    def test_list_jobs_non_json_error_response(self, mock_get):
        """List jobs handles non-JSON error responses gracefully."""
        mock_response = MagicMock()
        mock_response.ok = False
        mock_response.status_code = 500
        mock_response.json.side_effect = ValueError("No JSON")
        mock_response.text = "Internal Server Error"
        mock_get.return_value = mock_response

        with self.assertRaises(JobAPIError) as ctx:
            list_jobs()

        self.assertEqual(ctx.exception.status_code, 500)
        self.assertEqual(ctx.exception.error_message, "Internal Server Error")


# =============================================================================
# GET_JOB TESTS
# =============================================================================


@override_settings(ASTRO_CLOCK_SERVER="http://localhost:8086", QUERY_API_TIMEOUT=30)
class GetJobTests(TestCase):
    """Tests for get_job function."""

    @patch("jobs.clients.requests.get")
    def test_get_job_success(self, mock_get):
        """Get job returns full job details."""
        mock_response = MagicMock()
        mock_response.ok = True
        mock_response.json.return_value = {
            "job_id": "abc-123",
            "job_type": "load",
            "status": "complete",
            "result": {"rows_loaded": 42},
            "created_at": "2025-01-15T12:00:00Z",
        }
        mock_get.return_value = mock_response

        result = get_job("abc-123")

        self.assertEqual(result["job_id"], "abc-123")
        self.assertEqual(result["status"], "complete")
        self.assertEqual(result["result"]["rows_loaded"], 42)
        mock_get.assert_called_once()

    @patch("jobs.clients.requests.get")
    def test_get_job_not_found(self, mock_get):
        """Get job raises JobAPIError for 404."""
        mock_response = MagicMock()
        mock_response.ok = False
        mock_response.status_code = 404
        mock_response.json.return_value = {"error": "Job not found"}
        mock_response.text = '{"error": "Job not found"}'
        mock_get.return_value = mock_response

        with self.assertRaises(JobAPIError) as ctx:
            get_job("nonexistent-id")

        self.assertEqual(ctx.exception.status_code, 404)
        self.assertEqual(ctx.exception.error_message, "Job not found")

    @patch("jobs.clients.requests.get")
    def test_get_job_includes_job_id_in_url(self, mock_get):
        """Get job constructs URL with the provided job ID."""
        mock_response = MagicMock()
        mock_response.ok = True
        mock_response.json.return_value = {"job_id": "xyz-789", "status": "pending"}
        mock_get.return_value = mock_response

        get_job("xyz-789")

        call_url = mock_get.call_args.args[0]
        self.assertIn("/api/v1/jobs/xyz-789", call_url)

    @patch("jobs.clients.requests.get")
    def test_get_job_timeout(self, mock_get):
        """Get job raises JobTimeoutError on timeout."""
        import requests

        mock_get.side_effect = requests.Timeout("Connection timed out")

        with self.assertRaises(JobTimeoutError):
            get_job("job-123")

    @patch("jobs.clients.requests.get")
    def test_get_job_connection_error(self, mock_get):
        """Get job raises JobAPIError on connection failure."""
        import requests

        mock_get.side_effect = requests.ConnectionError("Connection refused")

        with self.assertRaises(JobAPIError) as ctx:
            get_job("job-123")

        self.assertIsNone(ctx.exception.status_code)
        self.assertIn("Could not connect", ctx.exception.error_message)

    @patch("jobs.clients.requests.get")
    def test_get_job_failed_status(self, mock_get):
        """Get job returns job details with error when status is failed."""
        mock_response = MagicMock()
        mock_response.ok = True
        mock_response.json.return_value = {
            "job_id": "fail-001",
            "status": "failed",
            "error": {"code": "internal_error", "message": "Something went wrong"},
        }
        mock_get.return_value = mock_response

        result = get_job("fail-001")

        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["error"]["code"], "internal_error")


# =============================================================================
# DELETE_JOB TESTS
# =============================================================================


@override_settings(ASTRO_CLOCK_SERVER="http://localhost:8086", QUERY_API_TIMEOUT=30)
class DeleteJobTests(TestCase):
    """Tests for delete_job function."""

    @patch("jobs.clients.requests.delete")
    def test_delete_job_success(self, mock_delete):
        """Delete job returns True on 204 No Content."""
        mock_response = MagicMock()
        mock_response.status_code = 204
        mock_delete.return_value = mock_response

        result = delete_job("abc-123")

        self.assertTrue(result)
        mock_delete.assert_called_once()

    @patch("jobs.clients.requests.delete")
    def test_delete_job_includes_job_id_in_url(self, mock_delete):
        """Delete job constructs URL with the provided job ID."""
        mock_response = MagicMock()
        mock_response.status_code = 204
        mock_delete.return_value = mock_response

        delete_job("xyz-789")

        call_url = mock_delete.call_args.args[0]
        self.assertIn("/api/v1/jobs/xyz-789", call_url)

    @patch("jobs.clients.requests.delete")
    def test_delete_job_not_found(self, mock_delete):
        """Delete job raises JobAPIError for 404."""
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.ok = False
        mock_response.json.return_value = {"error": "Job not found"}
        mock_response.text = '{"error": "Job not found"}'
        mock_delete.return_value = mock_response

        with self.assertRaises(JobAPIError) as ctx:
            delete_job("nonexistent-id")

        self.assertEqual(ctx.exception.status_code, 404)

    @patch("jobs.clients.requests.delete")
    def test_delete_job_conflict_in_process(self, mock_delete):
        """Delete job raises JobAPIError for 409 (in_process job)."""
        mock_response = MagicMock()
        mock_response.status_code = 409
        mock_response.ok = False
        mock_response.json.return_value = {
            "error": "conflict",
            "message": "Cannot delete job in in_process status",
        }
        mock_response.text = '{"error": "conflict"}'
        mock_delete.return_value = mock_response

        with self.assertRaises(JobAPIError) as ctx:
            delete_job("running-job")

        self.assertEqual(ctx.exception.status_code, 409)

    @patch("jobs.clients.requests.delete")
    def test_delete_job_timeout(self, mock_delete):
        """Delete job raises JobTimeoutError on timeout."""
        import requests

        mock_delete.side_effect = requests.Timeout("Connection timed out")

        with self.assertRaises(JobTimeoutError):
            delete_job("job-123")

    @patch("jobs.clients.requests.delete")
    def test_delete_job_connection_error(self, mock_delete):
        """Delete job raises JobAPIError on connection failure."""
        import requests

        mock_delete.side_effect = requests.ConnectionError("Connection refused")

        with self.assertRaises(JobAPIError) as ctx:
            delete_job("job-123")

        self.assertIsNone(ctx.exception.status_code)
        self.assertIn("Could not connect", ctx.exception.error_message)


# =============================================================================
# JOBLISTVIEW TESTS
# =============================================================================


@override_settings(ASTRO_CLOCK_SERVER="http://localhost:8086", QUERY_API_TIMEOUT=30)
class Test_Job_List_View_Access(TestCase):
    """Tests for JobListView staff-only access control."""

    def setUp(self):
        User = get_user_model()
        self.url = reverse("jobs:job_list")
        self.staff_user = User.objects.create_user(
            username="staff",
            email="staff@example.com",
            password="testpass123",
            is_staff=True,
        )
        self.regular_user = User.objects.create_user(
            username="regular",
            email="regular@example.com",
            password="testpass123",
            is_staff=False,
        )

    def test_unauthenticated_user_redirected_to_login(self):
        """Unauthenticated users are redirected to the login page."""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login", response.url)

    def test_non_staff_user_gets_403(self):
        """Non-staff authenticated users receive 403 Forbidden."""
        self.client.force_login(self.regular_user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 403)

    @patch("jobs.views.list_jobs")
    def test_staff_user_can_access(self, mock_list_jobs):
        """Staff users can access the job list page."""
        mock_list_jobs.return_value = {
            "jobs": [],
            "next": None,
            "prev": None,
        }
        self.client.force_login(self.staff_user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)


@override_settings(ASTRO_CLOCK_SERVER="http://localhost:8086", QUERY_API_TIMEOUT=30)
class Test_Job_List_View_Filter(TestCase):
    """Tests for JobListView filter parameter forwarding."""

    def setUp(self):
        User = get_user_model()
        self.url = reverse("jobs:job_list")
        self.staff_user = User.objects.create_user(
            username="staff",
            email="staff@example.com",
            password="testpass123",
            is_staff=True,
        )
        self.client.force_login(self.staff_user)

    @patch("jobs.views.list_jobs")
    def test_no_filters_passes_none_values(self, mock_list_jobs):
        """View with no query params calls list_jobs with no filters."""
        mock_list_jobs.return_value = {
            "jobs": [],
            "next": None,
            "prev": None,
        }
        self.client.get(self.url)
        mock_list_jobs.assert_called_once_with(
            status=None,
            job_type=None,
            created_after=None,
            created_before=None,
            cursor=None,
            count=20,
        )

    @patch("jobs.views.list_jobs")
    def test_status_filter_forwarded(self, mock_list_jobs):
        """View forwards status filter to list_jobs."""
        mock_list_jobs.return_value = {"jobs": [], "next": None, "prev": None}
        self.client.get(self.url + "?status=complete")
        call_kwargs = mock_list_jobs.call_args.kwargs
        self.assertEqual(call_kwargs["status"], "complete")

    @patch("jobs.views.list_jobs")
    def test_job_type_filter_forwarded(self, mock_list_jobs):
        """View forwards job_type filter to list_jobs."""
        mock_list_jobs.return_value = {"jobs": [], "next": None, "prev": None}
        self.client.get(self.url + "?job_type=load")
        call_kwargs = mock_list_jobs.call_args.kwargs
        self.assertEqual(call_kwargs["job_type"], "load")

    @patch("jobs.views.list_jobs")
    def test_date_filters_forwarded(self, mock_list_jobs):
        """View forwards created_after and created_before to list_jobs."""
        mock_list_jobs.return_value = {"jobs": [], "next": None, "prev": None}
        self.client.get(
            self.url + "?created_after=2025-01-01&created_before=2025-06-01"
        )
        call_kwargs = mock_list_jobs.call_args.kwargs
        self.assertEqual(call_kwargs["created_after"], "2025-01-01")
        self.assertEqual(call_kwargs["created_before"], "2025-06-01")

    @patch("jobs.views.list_jobs")
    def test_cursor_forwarded(self, mock_list_jobs):
        """View forwards cursor parameter for pagination."""
        mock_list_jobs.return_value = {"jobs": [], "next": None, "prev": None}
        self.client.get(self.url + "?cursor=abc123")
        call_kwargs = mock_list_jobs.call_args.kwargs
        self.assertEqual(call_kwargs["cursor"], "abc123")

    @patch("jobs.views.list_jobs")
    def test_count_forwarded_and_clamped(self, mock_list_jobs):
        """View forwards count, clamped to 1-100 range."""
        mock_list_jobs.return_value = {"jobs": [], "next": None, "prev": None}
        self.client.get(self.url + "?count=50")
        call_kwargs = mock_list_jobs.call_args.kwargs
        self.assertEqual(call_kwargs["count"], 50)

    @patch("jobs.views.list_jobs")
    def test_count_clamped_to_max_100(self, mock_list_jobs):
        """Count above 100 is clamped to 100."""
        mock_list_jobs.return_value = {"jobs": [], "next": None, "prev": None}
        self.client.get(self.url + "?count=500")
        call_kwargs = mock_list_jobs.call_args.kwargs
        self.assertEqual(call_kwargs["count"], 100)

    @patch("jobs.views.list_jobs")
    def test_count_clamped_to_min_1(self, mock_list_jobs):
        """Count below 1 is clamped to 1."""
        mock_list_jobs.return_value = {"jobs": [], "next": None, "prev": None}
        self.client.get(self.url + "?count=-5")
        call_kwargs = mock_list_jobs.call_args.kwargs
        self.assertEqual(call_kwargs["count"], 1)

    @patch("jobs.views.list_jobs")
    def test_count_defaults_to_20(self, mock_list_jobs):
        """Count defaults to 20 when not provided."""
        mock_list_jobs.return_value = {"jobs": [], "next": None, "prev": None}
        self.client.get(self.url)
        call_kwargs = mock_list_jobs.call_args.kwargs
        self.assertEqual(call_kwargs["count"], 20)

    @patch("jobs.views.list_jobs")
    def test_empty_filter_params_treated_as_none(self, mock_list_jobs):
        """Empty string filter params are treated as None."""
        mock_list_jobs.return_value = {"jobs": [], "next": None, "prev": None}
        self.client.get(self.url + "?status=&job_type=")
        call_kwargs = mock_list_jobs.call_args.kwargs
        self.assertIsNone(call_kwargs["status"])
        self.assertIsNone(call_kwargs["job_type"])


@override_settings(ASTRO_CLOCK_SERVER="http://localhost:8086", QUERY_API_TIMEOUT=30)
class Test_Job_List_View_Pagination(TestCase):
    """Tests for cursor pagination link extraction."""

    def setUp(self):
        User = get_user_model()
        self.url = reverse("jobs:job_list")
        self.staff_user = User.objects.create_user(
            username="staff",
            email="staff@example.com",
            password="testpass123",
            is_staff=True,
        )
        self.client.force_login(self.staff_user)

    @patch("jobs.views.list_jobs")
    def test_next_cursor_extracted_from_api_response(self, mock_list_jobs):
        """View extracts next cursor from API's next URL."""
        mock_list_jobs.return_value = {
            "jobs": [{"job_id": "j1"}],
            "next": "http://localhost:8086/api/v1/jobs?cursor=nexttoken123",
            "prev": None,
        }
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["next_cursor"], "nexttoken123")
        self.assertTrue(response.context["has_next"])
        self.assertFalse(response.context["has_prev"])

    @patch("jobs.views.list_jobs")
    def test_prev_cursor_extracted_from_api_response(self, mock_list_jobs):
        """View extracts prev cursor from API's prev URL."""
        mock_list_jobs.return_value = {
            "jobs": [{"job_id": "j1"}],
            "next": None,
            "prev": "http://localhost:8086/api/v1/jobs?cursor=prevtoken456",
        }
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["prev_cursor"], "prevtoken456")
        self.assertFalse(response.context["has_next"])
        self.assertTrue(response.context["has_prev"])

    @patch("jobs.views.list_jobs")
    def test_no_pagination_when_both_none(self, mock_list_jobs):
        """No pagination links when API returns null next/prev."""
        mock_list_jobs.return_value = {
            "jobs": [{"job_id": "j1"}],
            "next": None,
            "prev": None,
        }
        response = self.client.get(self.url)
        self.assertIsNone(response.context["next_cursor"])
        self.assertIsNone(response.context["prev_cursor"])
        self.assertFalse(response.context["has_next"])
        self.assertFalse(response.context["has_prev"])

    @patch("jobs.views.list_jobs")
    def test_filter_query_string_preserved_in_context(self, mock_list_jobs):
        """Filter params are preserved as query string for pagination links."""
        mock_list_jobs.return_value = {
            "jobs": [],
            "next": "http://localhost:8086/api/v1/jobs?cursor=abc&status=complete",
            "prev": None,
        }
        response = self.client.get(self.url + "?status=complete&job_type=load")
        self.assertIn("status=complete", response.context["filter_qs"])
        self.assertIn("job_type=load", response.context["filter_qs"])


@override_settings(ASTRO_CLOCK_SERVER="http://localhost:8086", QUERY_API_TIMEOUT=30)
class Test_Job_List_View_Error(TestCase):
    """Tests for JobListView error handling."""

    def setUp(self):
        User = get_user_model()
        self.url = reverse("jobs:job_list")
        self.staff_user = User.objects.create_user(
            username="staff",
            email="staff@example.com",
            password="testpass123",
            is_staff=True,
        )
        self.client.force_login(self.staff_user)

    @patch("jobs.views.list_jobs")
    def test_api_error_shows_error_message(self, mock_list_jobs):
        """View displays error message when API returns an error."""
        mock_list_jobs.side_effect = JobAPIError(
            "Server error", status_code=500
        )
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["error"], "Server error")
        self.assertEqual(response.context["jobs"], [])

    @patch("jobs.views.list_jobs")
    def test_timeout_error_shows_friendly_message(self, mock_list_jobs):
        """View shows a friendly timeout message on API timeout."""
        mock_list_jobs.side_effect = JobTimeoutError()
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertIn("timed out", response.context["error"])
        self.assertEqual(response.context["jobs"], [])


# =============================================================================
# JOB LIST TEMPLATE TESTS
# =============================================================================


# Sample job data for template tests
SAMPLE_JOBS = [
    {
        "job_id": "job-001",
        "job_type": "load",
        "status": "complete",
        "created_at": "2025-01-15T10:30:00Z",
        "updated_at": "2025-01-15T10:35:00Z",
    },
    {
        "job_id": "job-002",
        "job_type": "query",
        "status": "pending",
        "created_at": "2025-01-16T08:00:00Z",
        "updated_at": "2025-01-16T08:00:00Z",
    },
]


@override_settings(ASTRO_CLOCK_SERVER="http://localhost:8086", QUERY_API_TIMEOUT=30)
class Test_Job_List_Template_Table(TestCase):
    """Tests for job list template table rendering."""

    def setUp(self):
        User = get_user_model()
        self.url = reverse("jobs:job_list")
        self.staff_user = User.objects.create_user(
            username="staff",
            email="staff@example.com",
            password="testpass123",
            is_staff=True,
        )
        self.client.force_login(self.staff_user)

    @patch("jobs.views.list_jobs")
    def test_template_renders_job_table_with_data(self, mock_list_jobs):
        """Template renders a table row for each job."""
        mock_list_jobs.return_value = {
            "jobs": SAMPLE_JOBS,
            "next": None,
            "prev": None,
        }
        response = self.client.get(self.url)
        content = response.content.decode()

        self.assertIn("job-001", content)
        self.assertIn("job-002", content)
        self.assertIn("load", content)
        self.assertIn("query", content)
        self.assertIn("complete", content)
        self.assertIn("pending", content)

    @patch("jobs.views.list_jobs")
    def test_template_renders_table_headers(self, mock_list_jobs):
        """Template renders expected table column headers."""
        mock_list_jobs.return_value = {
            "jobs": SAMPLE_JOBS,
            "next": None,
            "prev": None,
        }
        response = self.client.get(self.url)
        content = response.content.decode()

        self.assertIn("<th>Job ID</th>", content)
        self.assertIn("<th>Type</th>", content)
        self.assertIn("<th>Status</th>", content)
        self.assertIn("<th>Created</th>", content)

    @patch("jobs.views.list_jobs")
    def test_template_renders_status_badge(self, mock_list_jobs):
        """Template renders status with badge CSS class."""
        mock_list_jobs.return_value = {
            "jobs": SAMPLE_JOBS,
            "next": None,
            "prev": None,
        }
        response = self.client.get(self.url)
        content = response.content.decode()

        self.assertIn("badge-complete", content)
        self.assertIn("badge-pending", content)

    @patch("jobs.views.list_jobs")
    def test_template_renders_hx_get_on_rows(self, mock_list_jobs):
        """Template renders hx-get attribute on job rows for detail expansion."""
        mock_list_jobs.return_value = {
            "jobs": SAMPLE_JOBS,
            "next": None,
            "prev": None,
        }
        response = self.client.get(self.url)
        content = response.content.decode()

        self.assertIn("hx-get=", content)
        self.assertIn("hx-trigger=\"click\"", content)
        self.assertIn("job-001", content)

    @patch("jobs.views.list_jobs")
    def test_template_renders_empty_state(self, mock_list_jobs):
        """Template renders empty state message when no jobs."""
        mock_list_jobs.return_value = {
            "jobs": [],
            "next": None,
            "prev": None,
        }
        response = self.client.get(self.url)
        content = response.content.decode()

        self.assertIn("No jobs found", content)
        # Should NOT render a table when empty
        self.assertNotIn("<tbody>", content)


@override_settings(ASTRO_CLOCK_SERVER="http://localhost:8086", QUERY_API_TIMEOUT=30)
class Test_Job_List_Template_Filters(TestCase):
    """Tests for job list template filter form rendering."""

    def setUp(self):
        User = get_user_model()
        self.url = reverse("jobs:job_list")
        self.staff_user = User.objects.create_user(
            username="staff",
            email="staff@example.com",
            password="testpass123",
            is_staff=True,
        )
        self.client.force_login(self.staff_user)

    @patch("jobs.views.list_jobs")
    def test_template_renders_status_filter(self, mock_list_jobs):
        """Template renders status select dropdown."""
        mock_list_jobs.return_value = {
            "jobs": [],
            "next": None,
            "prev": None,
        }
        response = self.client.get(self.url)
        content = response.content.decode()

        self.assertIn('name="status"', content)
        self.assertIn('id="status"', content)
        self.assertIn("Pending", content)
        self.assertIn("Complete", content)
        self.assertIn("Failed", content)

    @patch("jobs.views.list_jobs")
    def test_template_renders_job_type_filter(self, mock_list_jobs):
        """Template renders job_type select dropdown."""
        mock_list_jobs.return_value = {
            "jobs": [],
            "next": None,
            "prev": None,
        }
        response = self.client.get(self.url)
        content = response.content.decode()

        self.assertIn('name="job_type"', content)
        self.assertIn('id="job_type"', content)

    @patch("jobs.views.list_jobs")
    def test_template_renders_date_filters(self, mock_list_jobs):
        """Template renders date range inputs."""
        mock_list_jobs.return_value = {
            "jobs": [],
            "next": None,
            "prev": None,
        }
        response = self.client.get(self.url)
        content = response.content.decode()

        self.assertIn('name="created_after"', content)
        self.assertIn('name="created_before"', content)
        self.assertIn('type="date"', content)

    @patch("jobs.views.list_jobs")
    def test_template_renders_filter_button(self, mock_list_jobs):
        """Template renders filter submit and clear buttons."""
        mock_list_jobs.return_value = {
            "jobs": [],
            "next": None,
            "prev": None,
        }
        response = self.client.get(self.url)
        content = response.content.decode()

        self.assertIn("Filter", content)
        self.assertIn("Clear", content)

    @patch("jobs.views.list_jobs")
    def test_template_preserves_filter_selection(self, mock_list_jobs):
        """Template preserves current filter values as selected options."""
        mock_list_jobs.return_value = {
            "jobs": [],
            "next": None,
            "prev": None,
        }
        response = self.client.get(self.url + "?status=complete")
        content = response.content.decode()

        # The "complete" option should be selected
        self.assertIn('value="complete" selected', content)

    @patch("jobs.views.list_jobs")
    def test_template_uses_get_method(self, mock_list_jobs):
        """Filter form uses GET method."""
        mock_list_jobs.return_value = {
            "jobs": [],
            "next": None,
            "prev": None,
        }
        response = self.client.get(self.url)
        content = response.content.decode()

        self.assertIn('method="get"', content)


@override_settings(ASTRO_CLOCK_SERVER="http://localhost:8086", QUERY_API_TIMEOUT=30)
class Test_Job_List_Template_Pagination(TestCase):
    """Tests for job list template cursor pagination rendering."""

    def setUp(self):
        User = get_user_model()
        self.url = reverse("jobs:job_list")
        self.staff_user = User.objects.create_user(
            username="staff",
            email="staff@example.com",
            password="testpass123",
            is_staff=True,
        )
        self.client.force_login(self.staff_user)

    @patch("jobs.views.list_jobs")
    def test_template_renders_next_link(self, mock_list_jobs):
        """Template renders Next pagination link when has_next."""
        mock_list_jobs.return_value = {
            "jobs": SAMPLE_JOBS,
            "next": "http://localhost:8086/api/v1/jobs?cursor=nexttoken",
            "prev": None,
        }
        response = self.client.get(self.url)
        content = response.content.decode()

        self.assertIn("Next", content)
        self.assertIn("cursor=nexttoken", content)

    @patch("jobs.views.list_jobs")
    def test_template_renders_prev_link(self, mock_list_jobs):
        """Template renders Previous pagination link when has_prev."""
        mock_list_jobs.return_value = {
            "jobs": SAMPLE_JOBS,
            "next": None,
            "prev": "http://localhost:8086/api/v1/jobs?cursor=prevtoken",
        }
        response = self.client.get(self.url)
        content = response.content.decode()

        self.assertIn("Previous", content)
        self.assertIn("cursor=prevtoken", content)

    @patch("jobs.views.list_jobs")
    def test_template_no_pagination_without_cursors(self, mock_list_jobs):
        """Template does not render pagination when no cursors."""
        mock_list_jobs.return_value = {
            "jobs": SAMPLE_JOBS,
            "next": None,
            "prev": None,
        }
        response = self.client.get(self.url)
        content = response.content.decode()

        self.assertNotIn("cursor=", content)

    @patch("jobs.views.list_jobs")
    def test_template_pagination_preserves_filters(self, mock_list_jobs):
        """Pagination links include filter query string params."""
        mock_list_jobs.return_value = {
            "jobs": SAMPLE_JOBS,
            "next": "http://localhost:8086/api/v1/jobs?cursor=abc",
            "prev": None,
        }
        response = self.client.get(self.url + "?status=complete")
        content = response.content.decode()

        # Next link should include filter params
        self.assertIn("status=complete", content)


@override_settings(ASTRO_CLOCK_SERVER="http://localhost:8086", QUERY_API_TIMEOUT=30)
class Test_Job_List_Template_Error(TestCase):
    """Tests for job list template error state rendering."""

    def setUp(self):
        User = get_user_model()
        self.url = reverse("jobs:job_list")
        self.staff_user = User.objects.create_user(
            username="staff",
            email="staff@example.com",
            password="testpass123",
            is_staff=True,
        )
        self.client.force_login(self.staff_user)

    @patch("jobs.views.list_jobs")
    def test_template_renders_error_banner(self, mock_list_jobs):
        """Template renders error alert banner on API error."""
        mock_list_jobs.side_effect = JobAPIError("Server error", status_code=500)
        response = self.client.get(self.url)
        content = response.content.decode()

        self.assertIn("alert", content)
        self.assertIn("Server error", content)

    @patch("jobs.views.list_jobs")
    def test_template_renders_error_empty_state(self, mock_list_jobs):
        """Template shows error-specific empty state message."""
        mock_list_jobs.side_effect = JobAPIError("Server error", status_code=500)
        response = self.client.get(self.url)
        content = response.content.decode()

        self.assertIn("Could not load jobs", content)

    @patch("jobs.views.list_jobs")
    def test_template_no_error_banner_on_success(self, mock_list_jobs):
        """Template does not render error banner when no error."""
        mock_list_jobs.return_value = {
            "jobs": [],
            "next": None,
            "prev": None,
        }
        response = self.client.get(self.url)
        content = response.content.decode()

        self.assertNotIn("alert-error", content)

    @patch("jobs.views.list_jobs")
    def test_template_renders_timeout_message(self, mock_list_jobs):
        """Template renders friendly timeout error message."""
        mock_list_jobs.side_effect = JobTimeoutError()
        response = self.client.get(self.url)
        content = response.content.decode()

        self.assertIn("timed out", content)
        self.assertIn("alert", content)


# =============================================================================
# JOB DETAIL VIEW TESTS
# =============================================================================

SAMPLE_JOB = {
    "job_id": "12345678-1234-5678-1234-567812345678",
    "job_type": "query",
    "status": "complete",
    "payload": {"query": "SELECT * FROM planets"},
    "result": {"rows": [{"planet": "Mars"}]},
    "error": None,
    "created_at": "2025-04-19T10:00:00Z",
    "updated_at": "2025-04-19T10:01:00Z",
    "started_at": "2025-04-19T10:00:01Z",
    "completed_at": "2025-04-19T10:00:30Z",
}


class Test_Job_Detail_View_Access(TestCase):
    """Tests for JobDetailView staff-only access control."""

    def setUp(self):
        User = get_user_model()
        self.job_id = SAMPLE_JOB["job_id"]
        self.url = reverse("jobs:job_detail", kwargs={"job_id": self.job_id})
        self.staff_user = User.objects.create_user(
            username="staff",
            email="staff@example.com",
            password="testpass123",
            is_staff=True,
        )
        self.regular_user = User.objects.create_user(
            username="regular",
            email="regular@example.com",
            password="testpass123",
            is_staff=False,
        )

    def test_detail_unauthenticated_user_redirected_to_login(self):
        """Unauthenticated users are redirected to the login page."""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login", response.url)

    def test_detail_non_staff_user_gets_403(self):
        """Non-staff authenticated users receive 403 Forbidden."""
        self.client.force_login(self.regular_user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 403)

    @patch("jobs.views.get_job")
    def test_detail_staff_user_can_access(self, mock_get_job):
        """Staff users can access the job detail view."""
        mock_get_job.return_value = SAMPLE_JOB
        self.client.force_login(self.staff_user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)


@override_settings(ASTRO_CLOCK_SERVER="http://localhost:8086", QUERY_API_TIMEOUT=30)
class Test_Job_Detail_View_Context(TestCase):
    """Tests for JobDetailView context data and API interaction."""

    def setUp(self):
        User = get_user_model()
        self.job_id = SAMPLE_JOB["job_id"]
        self.url = reverse("jobs:job_detail", kwargs={"job_id": self.job_id})
        self.staff_user = User.objects.create_user(
            username="staff",
            email="staff@example.com",
            password="testpass123",
            is_staff=True,
        )
        self.client.force_login(self.staff_user)

    @patch("jobs.views.get_job")
    def test_detail_calls_get_job_with_id(self, mock_get_job):
        """JobDetailView calls get_job with the correct job_id."""
        from uuid import UUID
        mock_get_job.return_value = SAMPLE_JOB
        self.client.get(self.url)
        mock_get_job.assert_called_once_with(UUID(self.job_id))

    @patch("jobs.views.get_job")
    def test_detail_complete_job_can_download(self, mock_get_job):
        """Complete jobs set can_download=True in context."""
        mock_get_job.return_value = {**SAMPLE_JOB, "status": "complete"}
        response = self.client.get(self.url)
        self.assertTrue(response.context["can_download"])

    @patch("jobs.views.get_job")
    def test_detail_pending_job_cannot_download(self, mock_get_job):
        """Pending jobs set can_download=False in context."""
        mock_get_job.return_value = {**SAMPLE_JOB, "status": "pending"}
        response = self.client.get(self.url)
        self.assertFalse(response.context["can_download"])

    @patch("jobs.views.get_job")
    def test_detail_failed_job_cannot_download(self, mock_get_job):
        """Failed jobs set can_download=False in context."""
        mock_get_job.return_value = {**SAMPLE_JOB, "status": "failed"}
        response = self.client.get(self.url)
        self.assertFalse(response.context["can_download"])

    @patch("jobs.views.get_job")
    def test_detail_in_process_job_cannot_download(self, mock_get_job):
        """In-process jobs set can_download=False in context."""
        mock_get_job.return_value = {**SAMPLE_JOB, "status": "in_process"}
        response = self.client.get(self.url)
        self.assertFalse(response.context["can_download"])

    @patch("jobs.views.get_job")
    def test_detail_complete_job_can_delete(self, mock_get_job):
        """Complete jobs set can_delete=True (not in_process)."""
        mock_get_job.return_value = {**SAMPLE_JOB, "status": "complete"}
        response = self.client.get(self.url)
        self.assertTrue(response.context["can_delete"])

    @patch("jobs.views.get_job")
    def test_detail_failed_job_can_delete(self, mock_get_job):
        """Failed jobs set can_delete=True (not in_process)."""
        mock_get_job.return_value = {**SAMPLE_JOB, "status": "failed"}
        response = self.client.get(self.url)
        self.assertTrue(response.context["can_delete"])

    @patch("jobs.views.get_job")
    def test_detail_in_process_job_cannot_delete(self, mock_get_job):
        """In-process jobs set can_delete=False."""
        mock_get_job.return_value = {**SAMPLE_JOB, "status": "in_process"}
        response = self.client.get(self.url)
        self.assertFalse(response.context["can_delete"])

    @patch("jobs.views.get_job")
    def test_detail_404_raises_http404(self, mock_get_job):
        """JobDetailView raises Http404 when API returns 404."""
        mock_get_job.side_effect = JobAPIError("Not found", status_code=404)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 404)

    @patch("jobs.views.get_job")
    def test_detail_api_error_shows_error_message(self, mock_get_job):
        """JobDetailView shows error message on API error (non-404)."""
        mock_get_job.side_effect = JobAPIError("Server error", status_code=500)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertIn("Server error", response.context["error"])
        self.assertIsNone(response.context["job"])

    @patch("jobs.views.get_job")
    def test_detail_timeout_shows_friendly_message(self, mock_get_job):
        """JobDetailView shows friendly message on timeout."""
        mock_get_job.side_effect = JobTimeoutError()
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertIn("timed out", response.context["error"])
        self.assertIsNone(response.context["job"])


class Test_Job_Detail_Template(TestCase):
    """Tests for the job_detail.html template rendering."""

    def setUp(self):
        User = get_user_model()
        self.job_id = SAMPLE_JOB["job_id"]
        self.url = reverse("jobs:job_detail", kwargs={"job_id": self.job_id})
        self.staff_user = User.objects.create_user(
            username="staff",
            email="staff@example.com",
            password="testpass123",
            is_staff=True,
        )
        self.client.force_login(self.staff_user)

    @patch("jobs.views.get_job")
    def test_detail_template_renders_job_id(self, mock_get_job):
        """Template displays the job ID."""
        mock_get_job.return_value = SAMPLE_JOB
        response = self.client.get(self.url)
        content = response.content.decode()
        self.assertIn(self.job_id, content)

    @patch("jobs.views.get_job")
    def test_detail_template_renders_job_type(self, mock_get_job):
        """Template displays the job type."""
        mock_get_job.return_value = SAMPLE_JOB
        response = self.client.get(self.url)
        content = response.content.decode()
        self.assertIn("query", content)

    @patch("jobs.views.get_job")
    def test_detail_template_renders_status_badge(self, mock_get_job):
        """Template renders status with badge class."""
        mock_get_job.return_value = SAMPLE_JOB
        response = self.client.get(self.url)
        content = response.content.decode()
        self.assertIn("badge-complete", content)

    @patch("jobs.views.get_job")
    def test_detail_template_renders_timestamps(self, mock_get_job):
        """Template displays created, started, and completed timestamps."""
        mock_get_job.return_value = SAMPLE_JOB
        response = self.client.get(self.url)
        content = response.content.decode()
        self.assertIn("2025-04-19T10:00:00Z", content)
        self.assertIn("2025-04-19T10:00:01Z", content)
        self.assertIn("2025-04-19T10:00:30Z", content)

    @patch("jobs.views.get_job")
    def test_detail_template_renders_payload(self, mock_get_job):
        """Template displays the job payload."""
        mock_get_job.return_value = SAMPLE_JOB
        response = self.client.get(self.url)
        content = response.content.decode()
        self.assertIn("SELECT", content)

    @patch("jobs.views.get_job")
    def test_detail_template_renders_result(self, mock_get_job):
        """Template displays the job result."""
        mock_get_job.return_value = SAMPLE_JOB
        response = self.client.get(self.url)
        content = response.content.decode()
        self.assertIn("Mars", content)

    @patch("jobs.views.get_job")
    def test_detail_template_download_enabled_for_complete(self, mock_get_job):
        """Download button is enabled (no disabled attr) for complete jobs."""
        mock_get_job.return_value = SAMPLE_JOB
        response = self.client.get(self.url)
        content = response.content.decode()
        # Download link should NOT have disabled class
        self.assertIn("Download", content)
        # Should not have aria-disabled on download link
        download_start = content.index("Download")
        download_section = content[max(0, download_start - 200):download_start + 20]
        self.assertNotIn("aria-disabled", download_section)

    @patch("jobs.views.get_job")
    def test_detail_template_download_disabled_for_incomplete(self, mock_get_job):
        """Download button is disabled for non-complete jobs."""
        mock_get_job.return_value = {**SAMPLE_JOB, "status": "pending"}
        response = self.client.get(self.url)
        content = response.content.decode()
        self.assertIn("Download", content)
        # Should have aria-disabled on download link
        download_start = content.index("Download")
        download_section = content[max(0, download_start - 200):download_start + 20]
        self.assertIn("aria-disabled", download_section)

    @patch("jobs.views.get_job")
    def test_detail_template_delete_disabled_for_in_process(self, mock_get_job):
        """Delete button is disabled for in_process jobs."""
        mock_get_job.return_value = {**SAMPLE_JOB, "status": "in_process"}
        response = self.client.get(self.url)
        content = response.content.decode()
        self.assertIn("Delete", content)
        # Delete button should have disabled attribute
        delete_start = content.index("Delete")
        delete_section = content[max(0, delete_start - 200):delete_start + 20]
        self.assertIn("disabled", delete_section)

    @patch("jobs.views.get_job")
    def test_detail_template_delete_enabled_for_complete(self, mock_get_job):
        """Delete button is enabled for complete jobs."""
        mock_get_job.return_value = SAMPLE_JOB
        response = self.client.get(self.url)
        content = response.content.decode()
        self.assertIn("Delete", content)
        # Delete button should NOT have disabled attribute
        delete_start = content.index("Delete")
        delete_section = content[max(0, delete_start - 200):delete_start + 20]
        self.assertNotIn("disabled", delete_section)

    @patch("jobs.views.get_job")
    def test_detail_template_shows_error_on_api_failure(self, mock_get_job):
        """Template renders error message when API fails."""
        mock_get_job.side_effect = JobAPIError("Server error", status_code=500)
        response = self.client.get(self.url)
        content = response.content.decode()
        self.assertIn("Server error", content)
        self.assertIn("alert-error", content)

    @patch("jobs.views.get_job")
    def test_detail_template_no_error_on_success(self, mock_get_job):
        """Template does not show error when job loads successfully."""
        mock_get_job.return_value = SAMPLE_JOB
        response = self.client.get(self.url)
        content = response.content.decode()
        self.assertNotIn("alert-error", content)


# =============================================================================
# JOB DOWNLOAD VIEW TESTS
# =============================================================================


class Test_Job_Download_View_Access(TestCase):
    """Tests for JobDownloadView staff-only access control."""

    def setUp(self):
        User = get_user_model()
        self.job_id = SAMPLE_JOB["job_id"]
        self.url = reverse("jobs:job_download", kwargs={"job_id": self.job_id})
        self.staff_user = User.objects.create_user(
            username="staff",
            email="staff@example.com",
            password="testpass123",
            is_staff=True,
        )
        self.regular_user = User.objects.create_user(
            username="regular",
            email="regular@example.com",
            password="testpass123",
            is_staff=False,
        )

    def test_download_unauthenticated_user_redirected_to_login(self):
        """Unauthenticated users are redirected to the login page."""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login", response.url)

    def test_download_non_staff_user_gets_403(self):
        """Non-staff authenticated users receive 403 Forbidden."""
        self.client.force_login(self.regular_user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 403)


@override_settings(ASTRO_CLOCK_SERVER="http://localhost:8086", QUERY_API_TIMEOUT=30)
class Test_Job_Download_View(TestCase):
    """Tests for JobDownloadView download behavior."""

    def setUp(self):
        User = get_user_model()
        self.job_id = SAMPLE_JOB["job_id"]
        self.url = reverse("jobs:job_download", kwargs={"job_id": self.job_id})
        self.staff_user = User.objects.create_user(
            username="staff",
            email="staff@example.com",
            password="testpass123",
            is_staff=True,
        )
        self.client.force_login(self.staff_user)

    @patch("jobs.views.get_job")
    def test_download_complete_job_returns_json(self, mock_get_job):
        """Complete job returns result as downloadable JSON."""
        mock_get_job.return_value = {**SAMPLE_JOB, "status": "complete"}
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/json")

    @patch("jobs.views.get_job")
    def test_download_complete_job_has_content_disposition(self, mock_get_job):
        """Response includes Content-Disposition attachment header."""
        mock_get_job.return_value = {**SAMPLE_JOB, "status": "complete"}
        response = self.client.get(self.url)
        expected_filename = f"job-{self.job_id}-result.json"
        self.assertIn(expected_filename, response["Content-Disposition"])
        self.assertIn("attachment", response["Content-Disposition"])

    @patch("jobs.views.get_job")
    def test_download_returns_result_field(self, mock_get_job):
        """Response body contains only the result field from the job."""
        mock_get_job.return_value = {**SAMPLE_JOB, "status": "complete"}
        response = self.client.get(self.url)
        data = json.loads(response.content.decode())
        self.assertEqual(data, SAMPLE_JOB["result"])

    @patch("jobs.views.get_job")
    def test_download_calls_get_job_with_uuid(self, mock_get_job):
        """View calls get_job with the job UUID from URL."""
        from uuid import UUID

        mock_get_job.return_value = {**SAMPLE_JOB, "status": "complete"}
        self.client.get(self.url)
        mock_get_job.assert_called_once_with(UUID(self.job_id))

    @patch("jobs.views.get_job")
    def test_download_incomplete_job_returns_400(self, mock_get_job):
        """Non-complete jobs return 400 with error message."""
        for status in ("pending", "in_process", "failed"):
            with self.subTest(status=status):
                mock_get_job.return_value = {**SAMPLE_JOB, "status": status}
                response = self.client.get(self.url)
                self.assertEqual(response.status_code, 400)

    @patch("jobs.views.get_job")
    def test_download_incomplete_job_error_message(self, mock_get_job):
        """Non-complete job response includes user-friendly error."""
        mock_get_job.return_value = {**SAMPLE_JOB, "status": "pending"}
        response = self.client.get(self.url)
        data = json.loads(response.content.decode())
        self.assertIn("error", data)
        self.assertIn("complete", data["error"].lower())

    @patch("jobs.views.get_job")
    def test_download_api_404_returns_404(self, mock_get_job):
        """API returning 404 raises Http404."""
        mock_get_job.side_effect = JobAPIError("Not found", status_code=404)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 404)

    @patch("jobs.views.get_job")
    def test_download_api_error_returns_error_json(self, mock_get_job):
        """API error (non-404) returns JSON error response."""
        mock_get_job.side_effect = JobAPIError("Server error", status_code=500)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 500)
        data = json.loads(response.content.decode())
        self.assertEqual(data["error"], "Server error")

    @patch("jobs.views.get_job")
    def test_download_timeout_returns_504(self, mock_get_job):
        """API timeout returns 504 with error message."""
        mock_get_job.side_effect = JobTimeoutError()
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 504)
        data = json.loads(response.content.decode())
        self.assertIn("error", data)

    @patch("jobs.views.get_job")
    def test_download_result_none_returns_null_json(self, mock_get_job):
        """Complete job with result=None returns JSON null."""
        mock_get_job.return_value = {
            **SAMPLE_JOB,
            "status": "complete",
            "result": None,
        }
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content.decode())
        self.assertIsNone(data)

    @patch("jobs.views.get_job")
    def test_download_result_empty_dict_returns_empty_json(self, mock_get_job):
        """Complete job with empty result returns empty JSON object."""
        mock_get_job.return_value = {
            **SAMPLE_JOB,
            "status": "complete",
            "result": {},
        }
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content.decode())
        self.assertEqual(data, {})


# =============================================================================
# JOB DELETE VIEW TESTS
# =============================================================================


class Test_Job_Delete_View_Access(TestCase):
    """Tests for JobDeleteView staff-only access control."""

    def setUp(self):
        User = get_user_model()
        self.job_id = SAMPLE_JOB["job_id"]
        self.url = reverse("jobs:job_delete", kwargs={"job_id": self.job_id})
        self.staff_user = User.objects.create_user(
            username="staff",
            email="staff@example.com",
            password="testpass123",
            is_staff=True,
        )
        self.regular_user = User.objects.create_user(
            username="regular",
            email="regular@example.com",
            password="testpass123",
            is_staff=False,
        )

    def test_delete_unauthenticated_user_redirected_to_login(self):
        """Unauthenticated users are redirected to the login page."""
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login", response.url)

    def test_delete_non_staff_user_gets_403(self):
        """Non-staff authenticated users receive 403 Forbidden."""
        self.client.force_login(self.regular_user)
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, 403)

    @patch("jobs.views.delete_job")
    def test_delete_staff_user_can_post(self, mock_delete_job):
        """Staff users can POST to the delete endpoint."""
        mock_delete_job.return_value = True
        self.client.force_login(self.staff_user)
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, 204)


@override_settings(ASTRO_CLOCK_SERVER="http://localhost:8086", QUERY_API_TIMEOUT=30)
class Test_Job_Delete_View(TestCase):
    """Tests for JobDeleteView HTMX row removal and error handling."""

    def setUp(self):
        User = get_user_model()
        self.job_id = SAMPLE_JOB["job_id"]
        self.url = reverse("jobs:job_delete", kwargs={"job_id": self.job_id})
        self.staff_user = User.objects.create_user(
            username="staff",
            email="staff@example.com",
            password="testpass123",
            is_staff=True,
        )
        self.client.force_login(self.staff_user)

    @patch("jobs.views.delete_job")
    def test_delete_success_returns_204(self, mock_delete_job):
        """Successful delete returns HTTP 204 No Content."""
        mock_delete_job.return_value = True
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, 204)

    @patch("jobs.views.delete_job")
    def test_delete_success_has_hx_trigger_header(self, mock_delete_job):
        """Successful delete sets HX-Trigger header for HTMX row removal."""
        mock_delete_job.return_value = True
        response = self.client.post(self.url)
        self.assertEqual(response["HX-Trigger"], "jobDeleted")

    @patch("jobs.views.delete_job")
    def test_delete_success_empty_body(self, mock_delete_job):
        """Successful delete returns empty response body."""
        mock_delete_job.return_value = True
        response = self.client.post(self.url)
        self.assertEqual(response.content, b"")

    @patch("jobs.views.delete_job")
    def test_delete_calls_delete_job_with_uuid(self, mock_delete_job):
        """View calls delete_job with the job UUID from URL."""
        from uuid import UUID

        mock_delete_job.return_value = True
        self.client.post(self.url)
        mock_delete_job.assert_called_once_with(UUID(self.job_id))

    @patch("jobs.views.delete_job")
    def test_delete_409_returns_conflict(self, mock_delete_job):
        """409 (race condition: job started running) returns inline error."""
        mock_delete_job.side_effect = JobAPIError(
            "Cannot delete job in in_process status", status_code=409
        )
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, 409)
        self.assertIn("running", response.content.decode().lower())

    @patch("jobs.views.delete_job")
    def test_delete_409_returns_text_content_type(self, mock_delete_job):
        """409 response has text/plain content type for inline display."""
        mock_delete_job.side_effect = JobAPIError(
            "Cannot delete job in in_process status", status_code=409
        )
        response = self.client.post(self.url)
        self.assertEqual(response["Content-Type"], "text/plain")

    @patch("jobs.views.delete_job")
    def test_delete_404_returns_not_found(self, mock_delete_job):
        """404 (job already gone) returns inline error message."""
        mock_delete_job.side_effect = JobAPIError(
            "Job not found", status_code=404
        )
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, 404)
        self.assertIn("no longer exists", response.content.decode().lower())

    @patch("jobs.views.delete_job")
    def test_delete_404_returns_text_content_type(self, mock_delete_job):
        """404 response has text/plain content type for inline display."""
        mock_delete_job.side_effect = JobAPIError(
            "Job not found", status_code=404
        )
        response = self.client.post(self.url)
        self.assertEqual(response["Content-Type"], "text/plain")

    @patch("jobs.views.delete_job")
    def test_delete_api_error_returns_error_message(self, mock_delete_job):
        """Generic API error (non-409, non-404) returns error as text."""
        mock_delete_job.side_effect = JobAPIError(
            "Internal server error", status_code=500
        )
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, 500)
        self.assertIn("Internal server error", response.content.decode())

    @patch("jobs.views.delete_job")
    def test_delete_timeout_returns_504(self, mock_delete_job):
        """API timeout returns 504 with friendly error message."""
        mock_delete_job.side_effect = JobTimeoutError()
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, 504)
        self.assertIn("timed out", response.content.decode().lower())

    def test_delete_get_method_not_allowed(self):
        """GET requests are rejected (only POST accepted)."""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 405)

    @patch("jobs.views.delete_job")
    def test_delete_api_error_no_status_returns_500(self, mock_delete_job):
        """API error with no status code defaults to 500."""
        mock_delete_job.side_effect = JobAPIError("Connection refused")
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, 500)
        self.assertIn("Connection refused", response.content.decode())


# =============================================================================
# STAFF NAV LINK TESTS
# =============================================================================


class TestStaffNavLinks(TestCase):
    """Tests for staff-only navigation links in base.html."""

    def setUp(self):
        User = get_user_model()
        self.staff_user = User.objects.create_user(
            username="staff",
            email="staff@example.com",
            password="testpass123",
            is_staff=True,
        )
        self.regular_user = User.objects.create_user(
            username="regular",
            email="regular@example.com",
            password="testpass123",
            is_staff=False,
        )

    def test_staff_sees_admin_link(self):
        """Staff users see the Admin link in the navigation bar."""
        self.client.force_login(self.staff_user)
        response = self.client.get(reverse("core:home"))
        content = response.content.decode()
        self.assertIn('href="/admin/"', content)
        self.assertIn(">Admin</a>", content)

    def test_staff_sees_jobs_link(self):
        """Staff users see the Jobs link in the navigation bar."""
        self.client.force_login(self.staff_user)
        response = self.client.get(reverse("core:home"))
        content = response.content.decode()
        self.assertIn(reverse("jobs:job_list"), content)
        self.assertIn(">Jobs</a>", content)

    def test_non_staff_does_not_see_admin_link(self):
        """Non-staff authenticated users do not see the Admin link."""
        self.client.force_login(self.regular_user)
        response = self.client.get(reverse("core:home"))
        content = response.content.decode()
        self.assertNotIn('href="/admin/"', content)
        self.assertNotIn(">Admin</a>", content)

    def test_non_staff_does_not_see_jobs_link(self):
        """Non-staff authenticated users do not see the Jobs link."""
        self.client.force_login(self.regular_user)
        response = self.client.get(reverse("core:home"))
        content = response.content.decode()
        self.assertNotIn(reverse("jobs:job_list"), content)
        self.assertNotIn(">Jobs</a>", content)

    def test_unauthenticated_does_not_see_staff_links(self):
        """Unauthenticated users do not see Admin or Jobs links."""
        response = self.client.get(reverse("core:home"))
        content = response.content.decode()
        self.assertNotIn('href="/admin/"', content)
        self.assertNotIn(">Jobs</a>", content)
