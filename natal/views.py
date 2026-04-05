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
