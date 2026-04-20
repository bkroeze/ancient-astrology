"""
URL configuration for ancient_astrology project.
"""
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('core.urls')),
    path('natal/', include('natal.urls', namespace='natal')),
    path('api/v1/', include('natal.api_urls')),
    path('accounts/', include('allauth.urls')),
    path('electional/', include('electional.urls', namespace='electional')),
    path('jobs/', include('jobs.urls', namespace='jobs')),
]
