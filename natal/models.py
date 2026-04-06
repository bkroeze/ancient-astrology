from django.conf import settings
from django.db import models


class Place(models.Model):
    """
    Represents a geographic location used for natal chart calculations.
    
    Stores coordinates and timezone information needed for accurate
    astrological calculations including sidereal time computation.
    """
    
    name = models.CharField(max_length=255, help_text="Display name for the location")
    latitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        help_text="Latitude in decimal degrees (-90 to 90)"
    )
    longitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        help_text="Longitude in decimal degrees (-180 to 180)"
    )
    timezone = models.CharField(
        max_length=50,
        help_text="IANA timezone identifier (e.g., 'America/New_York')"
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="places",
        help_text="User who created this place"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = "natal_places"
        verbose_name = "place"
        verbose_name_plural = "places"
        ordering = ["name"]
        # Ensure location uniqueness per user
        constraints = [
            models.UniqueConstraint(
                fields=["name", "created_by"],
                name="unique_place_name_per_user"
            )
        ]
    
    def __str__(self):
        return self.name


class NatalSet(models.Model):
    """
    Represents a natal chart set with birth information and access permissions.
    
    Contains the birth datetime, location, and permission settings that
    determine who can view this natal chart data.
    """
    
    class Permission(models.TextChoices):
        PRIVATE = "private", "Private"
        NAMED_GROUP = "named_group", "Named Group"
        PUBLIC = "public", "Public"
    
    name = models.CharField(
        max_length=255,
        help_text="Descriptive name for this natal set"
    )
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="natal_sets",
        help_text="User who owns this natal set"
    )
    birth_datetime = models.DateTimeField(
        help_text="Birth date and time"
    )
    # Inline location fields (place FK preserved for data migration in T02)
    location_name = models.CharField(
        max_length=255,
        blank=True,
        default="",
        help_text="Birth location name"
    )
    latitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True,
        help_text="Latitude in decimal degrees (-90 to 90)"
    )
    longitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True,
        help_text="Longitude in decimal degrees (-180 to 180)"
    )
    timezone = models.CharField(
        max_length=50,
        blank=True,
        default="",
        help_text="IANA timezone identifier (e.g., 'America/New_York')"
    )
    place = models.ForeignKey(
        Place,
        on_delete=models.CASCADE,
        related_name="natal_sets",
        help_text="Birth location",
        null=True,
        blank=True
    )
    notes = models.TextField(
        blank=True,
        default="",
        help_text="Optional notes about this natal chart"
    )
    permission = models.CharField(
        max_length=20,
        choices=Permission.choices,
        default=Permission.PRIVATE,
        help_text="Who can view this natal set"
    )
    shared_with = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        blank=True,
        related_name="shared_natal_sets",
        help_text="Users with explicit access (for named_group permission)"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = "natal_sets"
        verbose_name = "natal set"
        verbose_name_plural = "natal sets"
        ordering = ["-created_at"]
    
    def __str__(self):
        return f"{self.name} ({self.owner})"
    
    def can_view(self, user):
        """
        Check if a given user can view this natal set.
        
        Returns True if:
        - User is the owner
        - Permission is PUBLIC and user is authenticated
        - User is in shared_with (for NAMED_GROUP)
        """
        if not user.is_authenticated:
            return False
        
        if user == self.owner:
            return True
        
        if self.permission == self.Permission.PUBLIC:
            return True
        
        if self.permission == self.Permission.NAMED_GROUP:
            return self.shared_with.filter(pk=user.pk).exists()
        
        return False
    
    def can_edit(self, user):
        """
        Check if a given user can edit this natal set.
        
        Only the owner can edit a natal set.
        """
        return user.is_authenticated and user == self.owner
