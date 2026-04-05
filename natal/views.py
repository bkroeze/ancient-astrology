"""
Views for natal set CRUD operations with permission-based visibility.
"""
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404
from django.urls import reverse_lazy
from django.views.generic import (
    CreateView,
    DeleteView,
    DetailView,
    ListView,
    UpdateView,
)

from .forms import NatalSetCreateForm, NatalSetForm
from .models import NatalSet


class PermissionFilteredListMixin:
    """
    Mixin that filters querysets based on user permissions.
    
    - Public sets are visible to all authenticated users
    - Private sets are visible only to the owner
    - Named group sets are visible to owner and shared users
    """
    
    def get_queryset(self):
        """Filter queryset to only include visible natal sets for the user."""
        queryset = super().get_queryset()
        user = self.request.user
        
        if not user.is_authenticated:
            return queryset.none()
        
        # Use the model's can_view method for permission filtering
        # This is more explicit and maintainable than a complex Q filter
        return queryset.filter(
            models_can_view_filter(user)
        ).select_related('owner', 'place').distinct()


def models_can_view_filter(user):
    """
    Build a filter expression for natal sets a user can view.
    
    Returns sets where:
    - User is the owner, OR
    - Permission is PUBLIC, OR
    - Permission is NAMED_GROUP and user is in shared_with
    """
    from django.db.models import Q
    
    return Q(owner=user) | Q(permission=NatalSet.Permission.PUBLIC) | (
        Q(permission=NatalSet.Permission.NAMED_GROUP) & Q(shared_with=user)
    )


class NatalSetListView(LoginRequiredMixin, PermissionFilteredListMixin, ListView):
    """
    List view showing natal sets visible to the current user.
    
    Shows public sets, private sets owned by the user, and named group
    sets where the user is the owner or is in shared_with.
    """
    model = NatalSet
    template_name = "natal/natal_set_list.html"
    context_object_name = "natal_sets"
    paginate_by = 20
    
    def get_queryset(self):
        """Filter to visible sets for the authenticated user."""
        from django.db.models import Q
        
        queryset = super().get_queryset()
        user = self.request.user
        
        # Include sets user can view
        return queryset.filter(
            Q(owner=user) |
            Q(permission=NatalSet.Permission.PUBLIC) |
            (Q(permission=NatalSet.Permission.NAMED_GROUP) & Q(shared_with=user))
        ).select_related('owner', 'place').order_by('-created_at')


class NatalSetCreateView(LoginRequiredMixin, CreateView):
    """
    Create view for new natal sets.
    
    Automatically assigns the current user as the owner.
    """
    model = NatalSet
    template_name = "natal/natal_set_form.html"
    success_url = reverse_lazy("natal:natal_set_list")
    
    def get_form_class(self):
        """Return the create form which auto-assigns owner."""
        return NatalSetCreateForm
    
    def get_form_kwargs(self):
        """Pass the current user to the form."""
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs
    
    def get_context_data(self, **kwargs):
        """Add page title to context."""
        context = super().get_context_data(**kwargs)
        context['page_title'] = 'Create Natal Set'
        return context


class NatalSetDetailView(LoginRequiredMixin, DetailView):
    """
    Detail view for natal sets.
    
    Only owners can view private or named-group sets.
    Public sets are viewable by all authenticated users.
    """
    model = NatalSet
    template_name = "natal/natal_set_detail.html"
    context_object_name = "natal_set"
    
    def get_queryset(self):
        """Filter to sets the user can view."""
        from django.db.models import Q
        
        user = self.request.user
        return NatalSet.objects.filter(
            Q(owner=user) |
            Q(permission=NatalSet.Permission.PUBLIC) |
            (Q(permission=NatalSet.Permission.NAMED_GROUP) & Q(shared_with=user))
        ).select_related('owner', 'place')
    
    def get_object(self, queryset=None):
        """Get the object and verify permission."""
        obj = super().get_object(queryset)
        if not obj.can_view(self.request.user):
            from django.core.exceptions import PermissionDenied
            raise PermissionDenied("You don't have permission to view this natal set.")
        return obj


class NatalSetUpdateView(LoginRequiredMixin, UpdateView):
    """
    Update view for natal sets.
    
    Only the owner can edit a natal set.
    """
    model = NatalSet
    template_name = "natal/natal_set_form.html"
    
    def get_form_class(self):
        """Return the regular form (not create form)."""
        return NatalSetForm
    
    def get_form_kwargs(self):
        """Pass the current user to the form."""
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs
    
    def get_queryset(self):
        """Only allow editing of sets owned by the user."""
        user = self.request.user
        return NatalSet.objects.filter(owner=user)
    
    def get_object(self, queryset=None):
        """Get the object and verify the user is the owner."""
        obj = super().get_object(queryset)
        if not obj.can_edit(self.request.user):
            from django.core.exceptions import PermissionDenied
            raise PermissionDenied("You don't have permission to edit this natal set.")
        return obj
    
    def get_success_url(self):
        """Redirect to the detail view after editing."""
        return reverse_lazy("natal:natal_set_detail", kwargs={"pk": self.object.pk})
    
    def get_context_data(self, **kwargs):
        """Add page title to context."""
        context = super().get_context_data(**kwargs)
        context['page_title'] = f'Edit {self.object.name}'
        return context


class NatalSetDeleteView(LoginRequiredMixin, DeleteView):
    """
    Delete view for natal sets.
    
    Only the owner can delete a natal set.
    """
    model = NatalSet
    template_name = "natal/natal_set_confirm_delete.html"
    success_url = reverse_lazy("natal:natal_set_list")
    context_object_name = "natal_set"
    
    def get_queryset(self):
        """Only allow deletion of sets owned by the user."""
        user = self.request.user
        return NatalSet.objects.filter(owner=user)
    
    def get_object(self, queryset=None):
        """Get the object and verify the user is the owner."""
        obj = super().get_object(queryset)
        if not obj.can_edit(self.request.user):
            from django.core.exceptions import PermissionDenied
            raise PermissionDenied("You don't have permission to delete this natal set.")
        return obj


class ChartView(LoginRequiredMixin, DetailView):
    """
    Chart generation view supporting both natal set charts and arbitrary parameter charts.
    
    URL patterns:
    - /natal/<pk>/chart/ - Chart for a specific natal set
    - /natal/chart/?lat=...&lon=...&time=... - Chart with arbitrary parameters
    
    The view:
    - Requires login (LoginRequiredMixin)
    - Checks permissions via can_view() for natal set charts
    - Calls the Astro Clock API via clients.generate_chart()
    - Handles errors gracefully by adding error to context
    """
    model = NatalSet
    template_name = "natal/chart_view.html"
    context_object_name = "natal_set"
    
    def get_queryset(self):
        """Filter to sets the user can view."""
        from django.db.models import Q
        
        user = self.request.user
        return NatalSet.objects.filter(
            Q(owner=user) |
            Q(permission=NatalSet.Permission.PUBLIC) |
            (Q(permission=NatalSet.Permission.NAMED_GROUP) & Q(shared_with=user))
        ).select_related('owner', 'place')
    
    def get_object(self, queryset=None):
        """Get the natal set and verify permission."""
        # Only get object for pk-based URLs, not parameter-based charts
        if self.kwargs.get('pk'):
            obj = super().get_object(queryset)
            if not obj.can_view(self.request.user):
                from django.core.exceptions import PermissionDenied
                raise PermissionDenied("You don't have permission to view this natal set.")
            return obj
        return None
    
    def get(self, request, *args, **kwargs):
        """Handle GET request for chart generation."""
        context = {}
        
        # Check if this is a natal set chart or parameter-based chart
        natal_set = self.get_object()
        
        if natal_set:
            # Natal set chart: /natal/<pk>/chart/
            context['natal_set'] = natal_set
            chart_params = {
                'latitude': float(natal_set.place.latitude),
                'longitude': float(natal_set.place.longitude),
                'datetime': natal_set.birth_datetime,
                'name': natal_set.name,
            }
        else:
            # Parameter-based chart: /natal/chart/?lat=...&lon=...&time=...
            try:
                lat = request.GET.get('lat') or request.GET.get('latitude')
                lon = request.GET.get('lon') or request.GET.get('longitude')
                time_str = request.GET.get('time') or request.GET.get('datetime')
                chart_name = request.GET.get('name', 'Custom Chart')
                
                if not all([lat, lon, time_str]):
                    context['error'] = "Missing required parameters: lat, lon, and time are required"
                    return self.render_to_response(context)
                
                from django.utils.dateparse import parse_datetime
                chart_datetime = parse_datetime(time_str)
                if chart_datetime is None:
                    context['error'] = "Invalid datetime format. Use ISO format (e.g., 1990-06-15T12:00)"
                    return self.render_to_response(context)
                
                chart_params = {
                    'latitude': float(lat),
                    'longitude': float(lon),
                    'datetime': chart_datetime,
                    'name': chart_name,
                }
            except (ValueError, TypeError) as e:
                context['error'] = f"Invalid parameter values: {str(e)}"
                return self.render_to_response(context)
        
        # Generate the chart
        try:
            from natal.clients import ChartRequest, generate_chart
            chart_request = ChartRequest(
                latitude=chart_params['latitude'],
                longitude=chart_params['longitude'],
                datetime=chart_params['datetime'],
                name=chart_params.get('name'),
            )
            chart_data = generate_chart(chart_request)
            context['chart'] = chart_data
        except Exception as e:
            # Catch API errors and add to context for graceful error handling
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Chart generation failed: {str(e)}")
            context['error'] = f"Chart generation failed: {str(e)}"
        
        return self.render_to_response(context)
