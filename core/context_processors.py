"""
Context processors for exposing application settings to templates.
"""
from django.conf import settings


def feature_flags(request):
    """
    Expose feature flag settings to all templates.
    
    Adds a `feature_flags` dictionary to the template context,
    allowing templates to conditionally render UI based on flags.
    
    Flags are defined in settings.py as ELECTIONAL_ENABLED, etc.
    """
    return {
        'feature_flags': {
            'ELECTIONAL_ENABLED': getattr(settings, 'ELECTIONAL_ENABLED', False),
        }
    }
