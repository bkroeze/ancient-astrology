"""
URL configuration for ancient_astrology project.
"""
from django.contrib import admin
from django.urls import path, include

from natal.views import ChartExportAPIView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('core.urls')),
    path('natal/', include('natal.urls', namespace='natal')),
    # API v1 endpoints
    path('api/v1/charts/<int:pk>/', ChartExportAPIView.as_view(), name='chart_export_api'),
    path('accounts/', include('allauth.urls')),
]
