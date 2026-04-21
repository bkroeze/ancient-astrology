"""
Views for job management with staff-only access and cursor pagination.
"""

import json
import logging
from urllib.parse import urlparse, parse_qs

from django.contrib.auth.mixins import UserPassesTestMixin
from django.http import Http404, HttpResponse, JsonResponse
from django.views import View
from django.views.generic import TemplateView

from .clients import JobAPIError, JobTimeoutError, delete_job, get_job, list_jobs

logger = logging.getLogger(__name__)

# Default page size for job listings
DEFAULT_PAGE_SIZE = 20


def _extract_cursor(url):
    """
    Extract the cursor query parameter from a pagination URL.

    Returns None if the URL is None or has no cursor parameter.
    """
    if not url:
        return None
    parsed = urlparse(url)
    params = parse_qs(parsed.query)
    cursors = params.get("cursor", [])
    return cursors[0] if cursors else None


class JobListView(UserPassesTestMixin, TemplateView):
    """
    Staff-only list view for jobs with filtering and cursor pagination.

    Forwards filter params (status, job_type, created_after, created_before)
    and pagination params (cursor, count) to the jobs API client.
    Extracts cursor tokens from the API's next/prev URLs for pagination links.
    """

    template_name = "jobs/job_list.html"

    def test_func(self):
        """Only allow staff users to access the job list."""
        return self.request.user.is_staff

    def get_context_data(self, **kwargs):
        """Fetch jobs from the API with filters and pagination."""
        context = super().get_context_data(**kwargs)
        request = self.request

        # Extract filter parameters from query string
        status = request.GET.get("status") or None
        job_type = request.GET.get("job_type") or None
        created_after = request.GET.get("created_after") or None
        created_before = request.GET.get("created_before") or None
        cursor = request.GET.get("cursor") or None
        try:
            count = int(request.GET.get("count", DEFAULT_PAGE_SIZE))
            count = max(1, min(100, count))
        except (ValueError, TypeError):
            count = DEFAULT_PAGE_SIZE

        context["filters"] = {
            "status": status or "",
            "job_type": job_type or "",
            "created_after": created_after or "",
            "created_before": created_before or "",
        }

        try:
            result = list_jobs(
                status=status,
                job_type=job_type,
                created_after=created_after,
                created_before=created_before,
                cursor=cursor,
                count=count,
            )
            context["jobs"] = result.get("jobs", [])
            context["next_cursor"] = _extract_cursor(result.get("next"))
            context["prev_cursor"] = _extract_cursor(result.get("prev"))
            context["has_next"] = result.get("next") is not None
            context["has_prev"] = result.get("prev") is not None
            context["count"] = count
            context["error"] = None
        except JobAPIError as e:
            logger.error("JobListView API error: %s", e)
            context["jobs"] = []
            context["next_cursor"] = None
            context["prev_cursor"] = None
            context["has_next"] = False
            context["has_prev"] = False
            context["count"] = count
            context["error"] = str(e.error_message)
        except JobTimeoutError as e:
            logger.error("JobListView timeout: %s", e)
            context["jobs"] = []
            context["next_cursor"] = None
            context["prev_cursor"] = None
            context["has_next"] = False
            context["has_prev"] = False
            context["count"] = count
            context["error"] = "The job API timed out. Please try again."

        # Build filter query string for pagination links (excludes cursor/count)
        filter_params = []
        if status:
            filter_params.append(f"status={status}")
        if job_type:
            filter_params.append(f"job_type={job_type}")
        if created_after:
            filter_params.append(f"created_after={created_after}")
        if created_before:
            filter_params.append(f"created_before={created_before}")
        context["filter_qs"] = "&".join(filter_params)

        return context


class JobDetailView(UserPassesTestMixin, TemplateView):
    """
    Staff-only HTMX partial returning full job metadata with action buttons.

    Renders templates/jobs/job_detail.html as an inline fragment intended
    to be swapped in after the clicked job row (hx-swap="afterend").
    Action buttons:
      - Download: enabled only when job.status == "complete"
      - Delete: enabled for non-in_process jobs
    """

    template_name = "jobs/job_detail.html"

    def test_func(self):
        """Only allow staff users to access job details."""
        return self.request.user.is_staff

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        job_id = kwargs.get("job_id")

        try:
            job = get_job(job_id)
        except JobAPIError as e:
            logger.error("JobDetailView API error for %s: %s", job_id, e)
            if e.status_code == 404:
                raise Http404(f"Job {job_id} not found")
            context["job"] = None
            context["error"] = str(e.error_message)
            return context
        except JobTimeoutError:
            logger.error("JobDetailView timeout for %s", job_id)
            context["job"] = None
            context["error"] = "The job API timed out. Please try again."
            return context

        context["job"] = job
        context["error"] = None
        context["can_download"] = job.get("status") == "complete"
        context["can_delete"] = job.get("status") != "in_process"
        return context


class JobDownloadView(UserPassesTestMixin, View):
    """
    Staff-only view that returns the job result as a downloadable JSON file.
    Only works for jobs with status == "complete".
    """

    def test_func(self):
        return self.request.user.is_staff

    def get(self, request, job_id):
        try:
            job = get_job(job_id)
        except JobTimeoutError:
            return JsonResponse(
                {"error": "The job API timed out. Please try again."}, status=504
            )
        except JobAPIError as e:
            if e.status_code == 404:
                raise Http404(f"Job {job_id} not found")
            return JsonResponse(
                {"error": e.error_message}, status=e.status_code or 500
            )

        if job.get("status") != "complete":
            return JsonResponse(
                {"error": "Only complete jobs can be downloaded"}, status=400
            )

        result_data = job.get("result", {})
        filename = f"job-{job_id}-result.json"
        response = HttpResponse(
            json.dumps(result_data, indent=2),
            content_type="application/json",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
        logger.info("Job download: job_id=%s by user=%s", job_id, request.user)
        return response


class JobDeleteView(UserPassesTestMixin, View):
    """
    Staff-only HTMX view that deletes a non-running job via the API.

    Returns HTMX-aware responses:
      - Success (204): No content with HX-Trigger header to remove the job row
      - 409 Conflict: Inline error about race condition (job started running)
      - 404 Not Found: Inline error about job already gone
      - Timeout/API error: Inline error message
    Only accepts POST requests.
    """

    def test_func(self):
        return self.request.user.is_staff

    def post(self, request, job_id):
        try:
            delete_job(job_id)
            logger.info(
                "Job deleted: job_id=%s by user=%s", job_id, request.user
            )
            return HttpResponse(status=204, headers={"HX-Trigger": "jobDeleted"})
        except JobTimeoutError:
            logger.error("JobDeleteView timeout for %s", job_id)
            return HttpResponse(
                "The job API timed out. Please try again.",
                status=504,
                content_type="text/plain",
            )
        except JobAPIError as e:
            logger.error("JobDeleteView error for %s: %s", job_id, e)
            if e.status_code == 409:
                return HttpResponse(
                    "Cannot delete: job is currently running.",
                    status=409,
                    content_type="text/plain",
                )
            if e.status_code == 404:
                return HttpResponse(
                    "Job no longer exists.",
                    status=404,
                    content_type="text/plain",
                )
            return HttpResponse(
                str(e.error_message),
                status=e.status_code or 500,
                content_type="text/plain",
            )
