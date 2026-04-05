from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    path('', views.home, name='home'),
    path('test/htmx/partial/', views.htmx_partial, name='htmx_partial'),
    path('chart-of-now/', views.chart_of_now, name='chart_of_now'),
]
