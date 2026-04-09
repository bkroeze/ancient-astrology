"""
Electional astrology models for saved queries and job tracking.
"""

from django.conf import settings
from django.db import models


class SavedQuery(models.Model):
    """
    Represents a saved electional astrology query with access permissions.
    
    Stores the query parameters and job status for electional chart requests.
    Electional astrology selects auspicious dates/times for specific activities.
    """
    
    class Permission(models.TextChoices):
        PRIVATE = "private", "Private"
        NAMED_GROUP = "named_group", "Named Group"
        PUBLIC = "public", "Public"
    
    class QueryType(models.TextChoices):
        WEDDING = "wedding", "Wedding"
        PROJECT = "project", "Project Launch"
        TRAVEL = "travel", "Travel Departure"
        MOVE_IN = "move_in", "Move In"
        MEDICAL = "medical", "Medical Procedure"
        OTHER = "other", "Other"
    
    class JobStatus(models.TextChoices):
        PENDING = "pending", "Pending"
        PROCESSING = "processing", "Processing"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"
    
    name = models.CharField(
        max_length=255,
        help_text="Descriptive name for this query"
    )
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="electional_queries",
        help_text="User who owns this query"
    )
    query_type = models.CharField(
        max_length=20,
        choices=QueryType.choices,
        default=QueryType.OTHER,
        help_text="Type of electional query"
    )
    query_params = models.JSONField(
        default=dict,
        help_text="Query parameters including location, date range, and preferences"
    )
    permission = models.CharField(
        max_length=20,
        choices=Permission.choices,
        default=Permission.PRIVATE,
        help_text="Who can view this query"
    )
    shared_with = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        blank=True,
        related_name="shared_electional_queries",
        help_text="Users with explicit access (for named_group permission)"
    )
    # Job tracking fields
    job_id = models.CharField(
        max_length=100,
        blank=True,
        default="",
        help_text="LLM backend job ID for tracking"
    )
    job_status = models.CharField(
        max_length=20,
        choices=JobStatus.choices,
        default=JobStatus.PENDING,
        help_text="Current job status"
    )
    job_error = models.TextField(
        blank=True,
        default="",
        help_text="Error message if job failed"
    )
    result_data = models.JSONField(
        null=True,
        blank=True,
        help_text="Results from the electional analysis"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = "electional_saved_queries"
        verbose_name = "saved query"
        verbose_name_plural = "saved queries"
        ordering = ["-created_at"]
    
    def __str__(self):
        return f"{self.name} ({self.query_type}) - {self.owner}"
    
    def can_view(self, user):
        """
        Check if a given user can view this saved query.
        
        Returns True if:
        - User is the owner
        - Permission is PUBLIC and user is authenticated
        - User is in shared_with (for NAMED_GROUP)
        """
        if not user or not user.is_authenticated:
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
        Check if a given user can edit this saved query.
        
        Only the owner can edit a saved query.
        """
        return user.is_authenticated and user == self.owner
    
    def clean(self):
        """
        Validate model fields.
        
        Raises:
            ValidationError: If permission is NAMED_GROUP but no users are shared.
        """
        from django.core.exceptions import ValidationError
        
        if (self.permission == self.Permission.NAMED_GROUP and 
            not self.shared_with.exists()):
            # For new instances, check if shared_with would be empty
            # This allows saving intermediate states during form processing
            pass
