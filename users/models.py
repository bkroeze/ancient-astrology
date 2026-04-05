from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """
    Custom User model extending AbstractUser.
    
    This model is defined before any migrations are created to ensure
    we can use a custom user model from the start.
    """
    
    email = models.EmailField(unique=True)
    default_place = models.ForeignKey(
        "natal.Place",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="default_for_users",
        help_text="Default birth place for this user"
    )
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']
    
    class Meta:
        db_table = 'users'
        verbose_name = 'user'
        verbose_name_plural = 'users'
    
    def __str__(self):
        return self.email
