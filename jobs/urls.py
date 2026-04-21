from django.urls import path

from .views import JobDeleteView, JobDetailView, JobDownloadView, JobListView

app_name = 'jobs'

urlpatterns = [
    path('', JobListView.as_view(), name='job_list'),
    path('<uuid:job_id>/', JobDetailView.as_view(), name='job_detail'),
    path('<uuid:job_id>/download/', JobDownloadView.as_view(), name='job_download'),
    path('<uuid:job_id>/delete/', JobDeleteView.as_view(), name='job_delete'),
]
