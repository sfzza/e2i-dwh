# Minimal URLs for testing
from django.contrib import admin
from django.urls import path
from django.http import JsonResponse

def root_view(request):
    return JsonResponse({"message": "E2I API", "status": "running"})

def health_view(request):
    return JsonResponse({"status": "ok"})

urlpatterns = [
    path("", root_view, name="root"),
    path("health/", health_view, name="health"),
    path("admin/", admin.site.urls),
]
