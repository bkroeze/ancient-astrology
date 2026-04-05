"""
URL patterns for natal app.
"""
from django.urls import path

from . import views

app_name = "natal"

urlpatterns = [
    path("", views.NatalSetListView.as_view(), name="natal_set_list"),
    path("create/", views.NatalSetCreateView.as_view(), name="natal_set_create"),
    path("chart/", views.ChartView.as_view(), name="chart_view"),
    path("<int:pk>/", views.NatalSetDetailView.as_view(), name="natal_set_detail"),
    path("<int:pk>/edit/", views.NatalSetUpdateView.as_view(), name="natal_set_edit"),
    path("<int:pk>/delete/", views.NatalSetDeleteView.as_view(), name="natal_set_delete"),
    path("<int:pk>/chart/", views.ChartView.as_view(), name="natal_set_chart"),
]
