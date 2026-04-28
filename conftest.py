import os

import django
from django.conf import settings

# Configure Django settings for pytest-django before any test collection.
# This mirrors the setup in manage.py and wsgi.py.
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "ancient_astrology.settings")


def pytest_configure(config):
    """Ensure Django is set up for pytest-django."""
    settings.INSTALLED_APPS  # force lazy settings evaluation
