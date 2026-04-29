from django.urls import path
from . import views
from . import wizard

app_name = 'core'

urlpatterns = [
    path('', views.home, name='home'),
    path('test/htmx/partial/', views.htmx_partial, name='htmx_partial'),
    path('chart-of-now/', views.chart_of_now, name='chart_of_now'),
    # Onboarding Wizard
    path('wizard/step1/', wizard.wizard_step1, name='wizard_step1'),
    path('wizard/step1/submit/', wizard.wizard_step1_submit, name='wizard_step1_submit'),
    path('wizard/step2/', wizard.wizard_step2, name='wizard_step2'),
    path('wizard/step2/submit/', wizard.wizard_step2_submit, name='wizard_step2_submit'),
    path('wizard/skip/', wizard.wizard_skip, name='wizard_skip'),
]
