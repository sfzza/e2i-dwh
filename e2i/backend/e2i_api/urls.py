# e2i_api/urls.py - Updated to include template management

from django.contrib import admin
from django.urls import path
from django.views.decorators.csrf import csrf_exempt

# Existing ingestion views
from e2i_api.apps.ingestion.views import (
    upload_view,
    presign_view,
    complete_view,
    upload_status_view,
)

# New template management views
from e2i_api.apps.ingestion.template_views import (
    template_list_view,
    template_create_from_upload_view,
    template_edit_view,
    template_activate_view,
    # New imports for deletion and usage views
    admin_delete_template_column_view,
    admin_delete_template_view,
    admin_template_usage_view,
    upload_preview_view,
    upload_set_mappings_view,
)

# Existing reporting views
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

    # =================== INGESTION ENDPOINTS ===================
    
    # File Upload (existing) - These handle POST requests so they need to be exempted.
    path("ingest/upload", csrf_exempt(upload_view), name="upload"),
    path("ingest/presign", csrf_exempt(presign_view), name="presign"),
    path("ingest/complete", csrf_exempt(complete_view), name="complete"),
    path("ingest/uploads/<uuid:upload_id>/status", upload_status_view, name="upload-status"),
    
    # =================== TEMPLATE MANAGEMENT ===================
    
    # Template CRUD (Admin only) - These use POST, PUT, and DELETE methods.
    path("templates/", template_list_view, name="template-list"),
    path("templates/create", csrf_exempt(template_create_from_upload_view), name="template-create"),
    path("templates/<uuid:template_id>", csrf_exempt(template_edit_view), name="template-edit"),
    path("templates/<uuid:template_id>/activate", csrf_exempt(template_activate_view), name="template-activate"),
    
    # New deletion and usage endpoints - These use GET and DELETE methods.
    path("templates/<uuid:template_id>/usage", admin_template_usage_view, name="template-usage"),
    path("templates/<uuid:template_id>/delete", csrf_exempt(admin_delete_template_view), name="template-delete"),
    path("templates/<uuid:template_id>/columns/<uuid:mapping_id>/delete", csrf_exempt(admin_delete_template_column_view), name="template-column-delete"),
    
    # =================== COLUMN MAPPING ===================
    
    # Upload preview and mapping (for users) - These use GET and POST methods.
    path("ingest/uploads/<uuid:upload_id>/preview", upload_preview_view, name="upload-preview"),
    path("ingest/uploads/<uuid:upload_id>/mappings", csrf_exempt(upload_set_mappings_view), name="upload-mappings"),
    
    # =================== REPORTING ENDPOINTS ===================
    
    path("api/reports/ping", ping, name="reporting-ping"),
    path("api/reports/datasets", datasets, name="datasets"),
    path("api/reports/datasets/<str:dataset>/schema", dataset_schema, name="dataset-schema"),
    path("api/reports/datasets/<str:dataset>/sample", dataset_sample, name="dataset-sample"),
    path("api/reports/query/run", csrf_exempt(query_run), name="query-run"),
    path("api/reports/query/explain", csrf_exempt(query_explain), name="query-explain"),
    path("api/reports/query/limits", query_limits, name="query-limits"),
    path("api/reports/detokenize", csrf_exempt(reports_detokenize), name="reports-detokenize"),
    path("api/reports/<uuid:rid>/status", reports_status_or_delete, name="reports-status"),
    path("api/reports/<uuid:rid>/delete", csrf_exempt(reports_status_or_delete), name="reports-delete"),
    path("api/reports/<uuid:rid>/download", reports_download, name="reports-download"),
]
