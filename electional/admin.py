"""
Admin configuration for electional app.
"""

from django.contrib import admin
from .models import SavedQuery


@admin.register(SavedQuery)
class SavedQueryAdmin(admin.ModelAdmin):
    """Admin interface for SavedQuery model."""
    
    list_display = [
        "name",
        "owner",
        "query_type",
        "permission",
        "job_status",
        "created_at",
    ]
    list_filter = [
        "query_type",
        "permission",
        "job_status",
        "created_at",
    ]
    search_fields = [
        "name",
        "owner__username",
        "owner__email",
    ]
    readonly_fields = [
        "job_id",
        "created_at",
        "updated_at",
    ]
    raw_id_fields = [
        "owner",
    ]
    
    fieldsets = (
        ("Basic Info", {
            "fields": (
                "name",
                "owner",
                "query_type",
                "permission",
            )
        }),
        ("Query Parameters", {
            "fields": (
                "query_params",
            )
        }),
        ("Job Tracking", {
            "fields": (
                "job_id",
                "job_status",
                "job_error",
                "result_data",
            )
        }),
        ("Access Control", {
            "fields": (
                "shared_with",
            )
        }),
        ("Timestamps", {
            "fields": (
                "created_at",
                "updated_at",
            ),
            "classes": ("collapse",)
        }),
    )
