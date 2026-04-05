"""
API URL configuration for natal app.

This module defines API v1 endpoints for the natal app.
"""
from django.urls import path

from .views import ChartExportAPIView


urlpatterns = [
    path('charts/<int:pk>/', ChartExportAPIView.as_view(), name='chart_export_api'),
]
