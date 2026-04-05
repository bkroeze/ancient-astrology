"""
URL configuration for ancient_astrology project.
"""
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('core.urls')),
    path('natal/', include('natal.urls', namespace='natal')),
    # API v1 endpoints
    path('api/v1/', include('natal.api_urls')),
    path('accounts/', include('allauth.urls')),
]
