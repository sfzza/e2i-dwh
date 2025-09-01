"""
URL configuration for e2i_api project.
"""

from django.contrib import admin
from django.urls import path

# ✅ import views from ingestion app
from e2i_api.apps.ingestion.views import (
    upload_view,
    presign_view,
    complete_view,
    upload_status_view,
)

urlpatterns = [
    # Django Admin
    path("admin/", admin.site.urls),

    # Ingestion Endpoints
    path("ingest/upload", upload_view, name="upload"),
    path("ingest/presign", presign_view, name="presign"),
    path("ingest/complete", complete_view, name="complete"),
    path("ingest/uploads/<uuid:upload_id>/status", upload_status_view, name="upload-status"),
]
