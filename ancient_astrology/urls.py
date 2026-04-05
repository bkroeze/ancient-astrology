"""
URL configuration for ancient_astrology project.
"""
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('core.urls')),
    path('natal/', include('natal.urls', namespace='natal')),
    path('accounts/', include('allauth.urls')),
]
