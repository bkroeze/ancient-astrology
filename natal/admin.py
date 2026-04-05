from django.contrib import admin

from .models import NatalSet, Place


@admin.register(Place)
class PlaceAdmin(admin.ModelAdmin):
    """Admin configuration for Place model."""
    
    list_display = ["name", "latitude", "longitude", "timezone", "created_by", "created_at"]
    list_filter = ["timezone", "created_at"]
    search_fields = ["name", "created_by__email"]
    readonly_fields = ["created_at", "updated_at"]
    raw_id_fields = ["created_by"]
    
    fieldsets = [
        (
            "Location Details",
            {
                "fields": ["name", "latitude", "longitude", "timezone"],
            }
        ),
        (
            "Metadata",
            {
                "fields": ["created_by", "created_at", "updated_at"],
                "classes": ["collapse"],
            }
        ),
    ]


@admin.register(NatalSet)
class NatalSetAdmin(admin.ModelAdmin):
    """Admin configuration for NatalSet model."""
    
    list_display = ["name", "owner", "birth_datetime", "place", "permission", "created_at"]
    list_filter = ["permission", "created_at", "birth_datetime"]
    search_fields = ["name", "owner__email", "place__name"]
    readonly_fields = ["created_at", "updated_at"]
    raw_id_fields = ["owner", "place"]
    filter_horizontal = ["shared_with"]
    
    fieldsets = [
        (
            "Basic Information",
            {
                "fields": ["name", "owner", "birth_datetime"],
            }
        ),
        (
            "Location",
            {
                "fields": ["place"],
            }
        ),
        (
            "Notes",
            {
                "fields": ["notes"],
                "classes": ["collapse"],
            }
        ),
        (
            "Permissions",
            {
                "fields": ["permission", "shared_with"],
            }
        ),
        (
            "Metadata",
            {
                "fields": ["created_at", "updated_at"],
                "classes": ["collapse"],
            }
        ),
    ]
