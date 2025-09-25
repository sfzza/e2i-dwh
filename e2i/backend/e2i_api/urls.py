# e2i_api/urls.py - Updated to include authentication endpoints

from django.contrib import admin
from django.urls import path
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.utils import timezone

# Simple root view for Railway
def root_view(request):
    return JsonResponse({
        "message": "E2I Data Warehouse API",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "health": "/health/",
            "admin": "/admin/",
            "api": "/api/",
            "auth": "/auth/",
            "dashboard": "/dashboard/",
            "templates": "/templates/",
            "ingestion": "/ingest/",
            "reports": "/api/reports/"
        }
    })

# Health check view
def health_view(request):
    return JsonResponse({"status": "ok"})

# Authentication views
from e2i_api.apps.common.auth import (
    login_view,
    logout_view,
    generate_api_key_view,
    user_profile_view,
)

# User management views
from e2i_api.apps.common.user_management_views import (
    user_list_view,
    user_create_view,
    user_delete_view,
    user_toggle_status_view,
    user_update_view,
)

# Audit logs views
from e2i_api.apps.common.audit_views import (
    audit_logs_list_view,
    audit_logs_create_view,
    audit_logs_stats_view,
)

# Dashboard views
from e2i_api.apps.common.dashboard_views import (
    dashboard_metrics_view,
    dashboard_activity_view,
)

# Existing ingestion views
from e2i_api.apps.ingestion.views import (
    upload_view,
    presign_view,
    complete_view,
    upload_status_view,
    upload_history_view,
)

# Template management views
from e2i_api.apps.ingestion.template_views import (
    template_list_view,
    template_create_from_upload_view,
    template_detail_view,
    template_edit_view,
    template_activate_view,
    template_deactivate_view,
    admin_delete_template_column_view,
    admin_delete_template_view,
    admin_template_usage_view,
    upload_preview_view,
    upload_set_mappings_view,
    user_select_template_view,
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
    # Root and Health endpoints
    path("", root_view, name="root"),
    path("health/", health_view, name="health"),
    
    # Django Admin
    path("admin/", admin.site.urls),

    # =================== AUTHENTICATION ENDPOINTS ===================
    
    path("auth/login", login_view, name="auth-login"),
    path("auth/logout", logout_view, name="auth-logout"),
    path("auth/generate-api-key", generate_api_key_view, name="auth-generate-api-key"),
    path("auth/profile", user_profile_view, name="auth-profile"),

    # =================== USER MANAGEMENT ENDPOINTS ===================
    
    path("users/", user_list_view, name="user-list"),
    path("users/create", user_create_view, name="user-create"),
    path("users/<uuid:user_id>/", user_update_view, name="user-update"),
    path("users/<uuid:user_id>/delete", user_delete_view, name="user-delete"),
    path("users/<uuid:user_id>/toggle-status", user_toggle_status_view, name="user-toggle-status"),

    # =================== AUDIT LOGS ENDPOINTS ===================
    
    path("audit-logs/", audit_logs_list_view, name="audit-logs-list"),
    path("audit-logs/create", audit_logs_create_view, name="audit-logs-create"),
    path("audit-logs/stats/", audit_logs_stats_view, name="audit-logs-stats"),

    # =================== DASHBOARD ENDPOINTS ===================
    
    path("dashboard/metrics/", dashboard_metrics_view, name="dashboard-metrics"),
    path("dashboard/activity/", dashboard_activity_view, name="dashboard-activity"),

    # =================== INGESTION ENDPOINTS ===================
    
    # File Upload (authentication required)
    path("ingest/upload", upload_view, name="upload"),
    path("ingest/presign", presign_view, name="presign"),
    path("ingest/complete", complete_view, name="complete"),
    path("ingest/uploads/", upload_history_view, name="upload-history"),
    path("ingest/uploads/<uuid:upload_id>/status", upload_status_view, name="upload-status"),
    
    # =================== TEMPLATE MANAGEMENT ===================
    
    # Template CRUD (Admin only except for list which is accessible to all authenticated users)
    path("templates/", template_list_view, name="template-list"),
    path("templates/create", template_create_from_upload_view, name="template-create"),
    path("templates/<uuid:template_id>/details", template_detail_view, name="template-detail"),
    path("templates/<uuid:template_id>", template_edit_view, name="template-edit"),
    path("templates/<uuid:template_id>/activate", template_activate_view, name="template-activate"),
     path('templates/<uuid:template_id>/deactivate', template_deactivate_view, name='template-deactivate'),
    
    # Admin-only endpoints
    path("templates/<uuid:template_id>/usage", admin_template_usage_view, name="template-usage"),
    path("templates/<uuid:template_id>/delete", admin_delete_template_view, name="template-delete"),
    path("templates/<uuid:template_id>/columns/<uuid:mapping_id>/delete", admin_delete_template_column_view, name="template-column-delete"),
    
    # =================== COLUMN MAPPING ===================
    
    # Upload preview and mapping (for authenticated users)
    path("ingest/uploads/<uuid:upload_id>/preview", upload_preview_view, name="upload-preview"),
    path("ingest/uploads/<uuid:upload_id>/select-template", user_select_template_view, name="upload-select-template"),
    path("ingest/uploads/<uuid:upload_id>/mappings", upload_set_mappings_view, name="upload-mappings"),
    
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