"""
URL configuration for e2i_api project.
"""

from django.contrib import admin
from django.urls import path, include

# Import views from ingestion app
from e2i_api.apps.ingestion.views import (
    upload_view,
    presign_view,
    complete_view,
    upload_status_view,
)

# Import views from reporting app
from e2i_api.apps.reporting.views import (
    ping,
    datasets,
    dataset_schema,
    dataset_sample,
    query_run,
    query_explain,
    query_limits,
    reports_detokenize,
    reports_status_or_delete,
    reports_download,
)

urlpatterns = [
    # Django Admin
    path("admin/", admin.site.urls),

    # Ingestion Endpoints
    path("ingest/upload", upload_view, name="upload"),
    path("ingest/presign", presign_view, name="presign"),
    path("ingest/complete", complete_view, name="complete"),
    path("ingest/uploads/<uuid:upload_id>/status", upload_status_view, name="upload-status"),

    # Reporting Endpoints
    path("api/reports/ping", ping, name="reporting-ping"),
    path("api/reports/datasets", datasets, name="datasets"),
    path("api/reports/datasets/<str:dataset>/schema", dataset_schema, name="dataset-schema"),
    path("api/reports/datasets/<str:dataset>/sample", dataset_sample, name="dataset-sample"),
    path("api/reports/query/run", query_run, name="query-run"),
    path("api/reports/query/explain", query_explain, name="query-explain"),
    path("api/reports/query/limits", query_limits, name="query-limits"),
    path("api/reports/detokenize", reports_detokenize, name="reports-detokenize"),
    path("api/reports/<uuid:rid>/status", reports_status_or_delete, name="reports-status"),
    path("api/reports/<uuid:rid>/delete", reports_status_or_delete, name="reports-delete"),
    path("api/reports/<uuid:rid>/download", reports_download, name="reports-download"),
]