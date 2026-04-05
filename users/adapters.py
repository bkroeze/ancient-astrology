from allauth.account.adapter import DefaultAccountAdapter
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.conf import settings


class AccountAdapter(DefaultAccountAdapter):
    """
    Custom account adapter for Ancient Astrology.
    
    Handles user signup, authentication, and account management.
    """
    
    def is_open_for_signup(self, request, email=None):
        """
        Allow signup by default.
        Override this to add domain-based restrictions if needed.
        """
        return True
    
    def clean_email(self, email):
        """
        Normalize email addresses by lowercasing the domain part.
        """
        email = super().clean_email(email)
        if email:
            email = email.lower()
        return email


class SocialAccountAdapter(DefaultSocialAccountAdapter):
    """
    Custom social account adapter for Ancient Astrology.
    
    Handles OAuth authentication (e.g., Google sign-in).
    """
    
    def is_open_for_signup(self, request, sociallogin):
        """
        Allow social account signup by default.
        """
        return True
