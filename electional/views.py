"""
Views for electional saved query CRUD operations with permission-based visibility.
"""

import logging

from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.template.loader import render_to_string
from django.urls import reverse_lazy
from django.views.generic import (
    CreateView,
    DeleteView,
    DetailView,
    ListView,
    UpdateView,
)
from django.core.exceptions import PermissionDenied

from .clients import QueryAPIError, QueryTimeoutError, get_job_status, submit_query
from .forms import SavedQueryCreateForm, SavedQueryForm
from .models import SavedQuery

logger = logging.getLogger(__name__)


class PermissionFilteredListMixin:
    """
    Mixin that filters querysets based on user permissions.

    - Public sets are visible to all authenticated users
    - Private sets are visible only to the owner
    - Named group sets are visible to owner and shared users
    """

    def get_queryset(self):
        """Filter queryset to only include visible queries for the user."""
        from django.db.models import Q

        queryset = super().get_queryset()
        user = self.request.user

        if not user.is_authenticated:
            return queryset.none()

        # Include queries user can view
        return (
            queryset.filter(
                Q(owner=user)
                | Q(permission=SavedQuery.Permission.PUBLIC)
                | (
                    Q(permission=SavedQuery.Permission.NAMED_GROUP)
                    & Q(shared_with=user)
                )
            )
            .select_related("owner")
            .order_by("-created_at")
        )


class SavedQueryListView(LoginRequiredMixin, PermissionFilteredListMixin, ListView):
    """
    List view showing saved queries visible to the current user.

    Shows public queries, private queries owned by the user, and named group
    queries where the user is the owner or is in shared_with.
    """

    model = SavedQuery
    template_name = "electional/query_list.html"
    context_object_name = "saved_queries"
    paginate_by = 20

    def get_queryset(self):
        """Filter to visible queries for the authenticated user."""
        from django.db.models import Q

        queryset = super().get_queryset()
        user = self.request.user

        # Include queries user can view
        return (
            queryset.filter(
                Q(owner=user)
                | Q(permission=SavedQuery.Permission.PUBLIC)
                | (
                    Q(permission=SavedQuery.Permission.NAMED_GROUP)
                    & Q(shared_with=user)
                )
            )
            .select_related("owner")
            .order_by("-created_at")
        )


class SavedQueryCreateView(LoginRequiredMixin, CreateView):
    """
    Create view for new saved queries.

    Automatically assigns the current user as the owner.
    """

    model = SavedQuery
    template_name = "electional/query_form.html"
    success_url = reverse_lazy("electional:saved_query_list")

    def get_form_class(self):
        """Return the create form which auto-assigns owner."""
        return SavedQueryCreateForm

    def get_form_kwargs(self):
        """Pass the current user to the form."""
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def get_context_data(self, **kwargs):
        """Add page title to context."""
        context = super().get_context_data(**kwargs)
        context["page_title"] = "Create Saved Query"
        return context


class SavedQueryDetailView(LoginRequiredMixin, DetailView):
    """
    Detail view for saved queries.

    Only owners can view private or named-group queries.
    Public queries are viewable by all authenticated users.
    """

    model = SavedQuery
    template_name = "electional/query_detail.html"
    context_object_name = "saved_query"

    def get_queryset(self):
        """Filter to queries the user can view."""
        from django.db.models import Q

        user = self.request.user
        return SavedQuery.objects.filter(
            Q(owner=user)
            | Q(permission=SavedQuery.Permission.PUBLIC)
            | (Q(permission=SavedQuery.Permission.NAMED_GROUP) & Q(shared_with=user))
        ).select_related("owner")

    def get_object(self, queryset=None):
        """Get the object and verify permission."""
        obj = super().get_object(queryset)
        if not obj.can_view(self.request.user):
            raise PermissionDenied(
                "You don't have permission to view this saved query."
            )
        return obj


class SavedQueryUpdateView(LoginRequiredMixin, UpdateView):
    """
    Update view for saved queries.

    Only the owner can edit a saved query.
    """

    model = SavedQuery
    template_name = "electional/query_form.html"

    def get_form_class(self):
        """Return the regular form (not create form)."""
        return SavedQueryForm

    def get_form_kwargs(self):
        """Pass the current user to the form."""
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def get_queryset(self):
        """Only allow editing of queries owned by the user."""
        user = self.request.user
        return SavedQuery.objects.filter(owner=user)

    def get_object(self, queryset=None):
        """Get the object and verify the user is the owner."""
        obj = super().get_object(queryset)
        if not obj.can_edit(self.request.user):
            raise PermissionDenied(
                "You don't have permission to edit this saved query."
            )
        return obj

    def get_success_url(self):
        """Redirect to the detail view after editing."""
        return reverse_lazy(
            "electional:saved_query_detail", kwargs={"pk": self.object.pk}
        )

    def get_context_data(self, **kwargs):
        """Add page title to context."""
        context = super().get_context_data(**kwargs)
        context["page_title"] = f"Edit {self.object.name}"
        return context


class SavedQueryDeleteView(LoginRequiredMixin, DeleteView):
    """
    Delete view for saved queries.

    Only the owner can delete a saved query.
    """

    model = SavedQuery
    template_name = "electional/query_confirm_delete.html"
    success_url = reverse_lazy("electional:saved_query_list")
    context_object_name = "saved_query"

    def get_queryset(self):
        """Only allow deletion of queries owned by the user."""
        user = self.request.user
        return SavedQuery.objects.filter(owner=user)

    def get_object(self, queryset=None):
        """Get the object and verify the user is the owner."""
        obj = super().get_object(queryset)
        if not obj.can_edit(self.request.user):
            raise PermissionDenied(
                "You don't have permission to delete this saved query."
            )
        return obj


class SavedQuerySubmitView(LoginRequiredMixin, DetailView):
    """
    Handle POST to submit an electional query for processing.

    Submits the query to the Astro Clock API, stores the job_id on the
    SavedQuery instance, and returns an HTMX partial with job status.
    Only the owner can submit queries.
    """

    model = SavedQuery

    def get_queryset(self):
        return SavedQuery.objects.filter(owner=self.request.user)

    def post(self, request, *args, **kwargs):
        saved_query = self.get_object()

        if saved_query.job_id and saved_query.job_status in (
            SavedQuery.JobStatus.PENDING,
            SavedQuery.JobStatus.PROCESSING,
        ):
            # Already has an active job; return current status
            return self._render_status(request, saved_query)

        # Build QueryRequest from saved query params
        params = saved_query.query_params or {}
        try:
            from datetime import date as date_type
            from .clients import QueryRequest as QR

            start = params.get("start_date")
            end = params.get("end_date")
            if isinstance(start, str):
                from datetime import datetime

                start = datetime.strptime(start, "%Y-%m-%d").date()
            if isinstance(end, str):
                from datetime import datetime

                end = datetime.strptime(end, "%Y-%m-%d").date()

            qr = QR(
                query_type=saved_query.query_type,
                description=params.get("description", saved_query.name),
                latitude=saved_query.latitude,
                longitude=saved_query.longitude,
                location_name=params.get("location_name", ""),
                start_date=start or date_type.today(),
                end_date=end or date_type.today(),
                preferences=params.get("preferences"),
            )

            result = submit_query(qr)
            saved_query.job_id = result.get("job_id", "")
            saved_query.job_status = SavedQuery.JobStatus.PENDING
            saved_query.save(update_fields=["job_id", "job_status", "updated_at"])

            logger.info(
                "Submitted electional query: pk=%s, job_id=%s",
                saved_query.pk,
                saved_query.job_id,
            )

        except (QueryAPIError, QueryTimeoutError) as e:
            logger.error(
                "Failed to submit electional query pk=%s: %s",
                saved_query.pk,
                str(e),
            )
            saved_query.job_status = SavedQuery.JobStatus.FAILED
            saved_query.job_error = str(e)
            saved_query.save(update_fields=["job_status", "job_error", "updated_at"])
        except (ValueError, TypeError, KeyError) as e:
            logger.error(
                "Invalid query params for pk=%s: %s",
                saved_query.pk,
                str(e),
            )
            saved_query.job_status = SavedQuery.JobStatus.FAILED
            saved_query.job_error = f"Invalid query parameters: {e}"
            saved_query.save(update_fields=["job_status", "job_error", "updated_at"])

        return self._render_status(request, saved_query)

    def _render_status(self, request, saved_query):
        """Render the job status HTMX partial."""
        html = render_to_string(
            "electional/job_status.html",
            {
                "job_status": saved_query.job_status,
                "job_id": saved_query.job_id,
                "job_error": saved_query.job_error,
                "result_data": saved_query.result_data,
                "saved_query": saved_query,
            },
            request=request,
        )
        return HttpResponse(html)


class SavedQueryJobStatusView(LoginRequiredMixin, DetailView):
    """
    HTMX endpoint that polls the Astro Clock API for job status.

    Returns an HTMX partial with updated status. For pending/processing
    jobs, the response includes hx-trigger="every 5s" to keep polling.
    For completed/failed jobs, polling stops and results or errors are shown.
    """

    model = SavedQuery
    context_object_name = "saved_query"

    def get_queryset(self):
        from django.db.models import Q

        user = self.request.user
        return SavedQuery.objects.filter(
            Q(owner=user)
            | Q(permission=SavedQuery.Permission.PUBLIC)
            | (Q(permission=SavedQuery.Permission.NAMED_GROUP) & Q(shared_with=user))
        ).select_related("owner")

    def get(self, request, *args, **kwargs):
        saved_query = self.get_object()

        if not saved_query.job_id:
            return HttpResponse("")

        # Only poll the API if the job isn't already terminal
        if saved_query.job_status in (
            SavedQuery.JobStatus.PENDING,
            SavedQuery.JobStatus.PROCESSING,
        ):
            try:
                result = get_job_status(saved_query.job_id)
                api_status = result.get("status", "unknown")

                old_status = saved_query.job_status

                # Map API status to model status
                status_map = {
                    "pending": SavedQuery.JobStatus.PENDING,
                    "processing": SavedQuery.JobStatus.PROCESSING,
                    "in_process": SavedQuery.JobStatus.PROCESSING,
                    "completed": SavedQuery.JobStatus.COMPLETED,
                    "complete": SavedQuery.JobStatus.COMPLETED,
                    "failed": SavedQuery.JobStatus.FAILED,
                }
                new_status = status_map.get(api_status, saved_query.job_status)

                saved_query.job_status = new_status

                if new_status == SavedQuery.JobStatus.COMPLETED:
                    saved_query.result_data = result.get("result", result)
                elif new_status == SavedQuery.JobStatus.FAILED:
                    saved_query.job_error = result.get("error", "Analysis failed")

                saved_query.save(
                    update_fields=[
                        "job_status",
                        "job_error",
                        "result_data",
                        "updated_at",
                    ]
                )

                if old_status != new_status:
                    logger.info(
                        "Job status transition: job_id=%s, %s -> %s",
                        saved_query.job_id,
                        old_status,
                        new_status,
                    )

            except (QueryAPIError, QueryTimeoutError) as e:
                logger.warning(
                    "Job status poll failed (will retry): job_id=%s, error=%s",
                    saved_query.job_id,
                    str(e),
                )
                # Don't update status on transient errors — let polling retry

        html = render_to_string(
            "electional/job_status.html",
            {
                "job_status": saved_query.job_status,
                "job_id": saved_query.job_id,
                "job_error": saved_query.job_error,
                "result_data": saved_query.result_data,
                "saved_query": saved_query,
            },
            request=request,
        )
        return HttpResponse(html)
