"""
URL patterns for electional app.
"""
from django.urls import path

from . import views

app_name = "electional"

# Web views
urlpatterns = [
    path("", views.SavedQueryListView.as_view(), name="saved_query_list"),
    path("create/", views.SavedQueryCreateView.as_view(), name="saved_query_create"),
    path("<int:pk>/", views.SavedQueryDetailView.as_view(), name="saved_query_detail"),
    path("<int:pk>/edit/", views.SavedQueryUpdateView.as_view(), name="saved_query_edit"),
    path("<int:pk>/delete/", views.SavedQueryDeleteView.as_view(), name="saved_query_delete"),
    path("<int:pk>/submit/", views.SavedQuerySubmitView.as_view(), name="saved_query_submit"),
    path("<int:pk>/job-status/", views.SavedQueryJobStatusView.as_view(), name="saved_query_job_status"),
]
