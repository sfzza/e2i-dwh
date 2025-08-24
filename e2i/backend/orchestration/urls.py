from django.urls import path
from .views import RunPipelineView

urlpatterns = [
    path('run/', RunPipelineView.as_view(), name='run-pipeline'),
]