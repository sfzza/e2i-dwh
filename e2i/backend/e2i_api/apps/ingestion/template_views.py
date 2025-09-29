# e2i_api/apps/ingestion/template_views.py

import csv
import io
import json
import logging
import pandas as pd
from django.db import transaction
from django.db.models import Count
from django.http import JsonResponse, HttpResponseNotAllowed
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import csrf_exempt

# Consolidated and cleaned imports
from e2i_api.apps.common.auth import (
    admin_required,
    user_access_required,
    get_current_user,
)
from .models import (
    ColumnMapping,
    DataTemplate,
    TemplateColumn,
    Upload,
    UploadExtension,
)
from .views import (
    _get_minio_client,
    _bucket_name,
    _json_error,
    _notify_orchestrator,
)

logger = logging.getLogger(__name__)

# ===================================================================
# Template Management
# ===================================================================

@user_access_required
def template_list_view(request):
    """List all templates for the current user."""
    if request.method != "GET":
        return HttpResponseNotAllowed(["GET"])

    current_user = get_current_user(request)
    
    # If user is admin, show all templates they created
    # If user is regular user, show all active templates (created by anyone)
    if current_user.role == 'admin':
        templates = DataTemplate.objects.filter(created_by=current_user.id).prefetch_related("columns")
    else:
        # Regular users can see all active templates
        templates = DataTemplate.objects.filter(status='active').prefetch_related("columns")

    result = [
        {
            "id": str(template.id),
            "name": template.name,
            "description": template.description,
            "version": template.version,
            "status": template.status,
            "target_table": template.target_table,
            "column_count": template.columns.count(),
            "columns": [
                {
                    "name": col.name,
                    "display_name": col.display_name,
                    "data_type": col.data_type,
                    "processing_type": col.processing_type,
                    "is_required": col.is_required,
                    "merged_from_columns": col.merged_from_columns,
                }
                for col in template.columns.all()
            ],
            "created_at": template.created_at.isoformat(),
        }
        for template in templates
    ]
    return JsonResponse({"templates": result})


# In e2i_api/apps/ingestion/template_views.py

@csrf_exempt
@admin_required
def template_create_from_upload_view(request):
    """Admin: Create a new template from an existing file upload."""
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    try:
        data = json.loads(request.body or b"{}")
    except json.JSONDecodeError:
        return _json_error("BAD_REQUEST", "Invalid JSON body")

    upload_id = data.get('upload_id')
    template_name = data.get('name', '').strip()
    target_table = data.get('target_table')

    if not all([upload_id, template_name, target_table]):
        return _json_error("BAD_REQUEST", "upload_id, name, and target_table are required")

    upload = get_object_or_404(Upload, id=upload_id)
    
    # ### FIX: REMOVED the incorrect 'user_id' line ###
    # ### Get the full user object instead ###
    current_user = get_current_user(request)

    try:
        client = _get_minio_client()
        bucket = _bucket_name()
        with client.get_object(bucket, upload.minio_key) as response:
            content = response.read().decode("utf-8-sig")
        df = pd.read_csv(io.StringIO(content))
    except Exception as e:
        return _json_error("PROCESSING_ERROR", f"Failed to read file from storage: {e}", 500)

    with transaction.atomic():
        template = DataTemplate.objects.create(
            name=template_name,
            description=data.get("description", ""),
            # ### FIX: Use the correct 'current_user.id' here ###
            created_by=current_user.id,
            created_from_upload=upload,
            target_table=target_table,
            status="draft",
        )
        for idx, header in enumerate(df.columns):
            clean_header = header.strip()
            if not clean_header:
                continue
            
            col_name = clean_header.lower().replace(" ", "_").replace(".", "_")
            dtype = str(df[header].dtype)

            if "int" in dtype: data_type = "integer"
            elif "float" in dtype: data_type = "float"
            elif "datetime" in dtype: data_type = "datetime"
            elif "bool" in dtype: data_type = "boolean"
            else: data_type = "string"
            
            TemplateColumn.objects.create(
                template=template, name=col_name, display_name=clean_header,
                data_type=data_type, order=idx
            )
    
    # Log template creation activity
    from e2i_api.apps.common.models import AuditLog
    if current_user:
        AuditLog.log_action(
            user=current_user,
            username=current_user.username,
            action='template_create',
            resource=f'template: {template_name}',
            resource_id=str(template.id),
            status='success',
            ip_address=request.META.get('REMOTE_ADDR'),
            user_agent=request.META.get('HTTP_USER_AGENT', '')[:1000],
            details={
                'target_table': target_table,
                'columns_count': len(df.columns),
                'created_from_upload': str(upload_id)
            }
        )
    
    return JsonResponse({"id": str(template.id), "status": template.status}, status=201)

@user_access_required
def template_detail_view(request, template_id):
    """Get template details for users (read-only access)."""
    if request.method != "GET":
        return HttpResponseNotAllowed(["GET"])
    
    template = get_object_or_404(DataTemplate.objects.prefetch_related('columns'), id=template_id)
    
    return JsonResponse({
        'id': str(template.id), 'name': template.name, 'description': template.description,
        'status': template.status, 'target_table': template.target_table,
        'columns': [{'id': str(c.id), 'name': c.name, 'display_name': c.display_name,
                     'data_type': c.data_type, 'processing_type': c.processing_type,
                     'is_required': c.is_required, 'merged_from_columns': c.merged_from_columns,
                     'order': c.order}
                    for c in template.columns.all()]
    })

@csrf_exempt
@admin_required
def template_edit_view(request, template_id):
    """Admin: Get, update, or delete a template definition."""
    template = get_object_or_404(DataTemplate.objects.prefetch_related('columns'), id=template_id)

    if request.method == "GET":
        return JsonResponse({
            'id': str(template.id), 'name': template.name, 'description': template.description,
            'status': template.status, 'target_table': template.target_table,
            'columns': [{'id': str(c.id), 'name': c.name, 'display_name': c.display_name,
                         'data_type': c.data_type, 'processing_type': c.processing_type,
                         'is_required': c.is_required, 'merged_from_columns': c.merged_from_columns,
                         'order': c.order}
                        for c in template.columns.all()]
        })
    elif request.method == "PUT":
        try:
            data = json.loads(request.body or b"{}")
        except json.JSONDecodeError:
            return _json_error("BAD_REQUEST", "Invalid JSON body")
        
        with transaction.atomic():
            template.name = data.get('name', template.name)
            template.description = data.get('description', template.description)
            template.target_table = data.get('target_table', template.target_table)
            template.save()

            if 'columns' in data:
                template.columns.all().delete()
                for col_data in data['columns']:
                    # Log the column data being created for debugging
                    logger.info(f"Creating column with data: {col_data}")
                    TemplateColumn.objects.create(template=template, **col_data)
        return JsonResponse({"success": True, "message": "Template updated."})
    elif request.method == "DELETE":
        template.delete()
        return JsonResponse({"success": True, "message": "Template deleted."})
    
    return HttpResponseNotAllowed(["GET", "PUT", "DELETE"])


@csrf_exempt
@admin_required
def template_activate_view(request, template_id):
    """Admin: Activate a template to make it available for users."""
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    template = get_object_or_404(DataTemplate, id=template_id)
    template.status = "active"
    template.save()
    return JsonResponse({"success": True, "status": template.status})


@csrf_exempt
@admin_required
def template_deactivate_view(request, template_id):
    """Admin: Deactivate a template, changing its status back to draft."""
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    template = get_object_or_404(DataTemplate, id=template_id)
    template.status = "draft"
    template.save()
    return JsonResponse({"success": True, "status": template.status})


# ===================================================================
# USER: Mapping Workflow
# ===================================================================

@user_access_required
def upload_preview_view(request, upload_id):
    """User: Get a preview of an uploaded file for the mapping UI."""
    if request.method != "GET":
        return HttpResponseNotAllowed(["GET"])
    
    upload = get_object_or_404(Upload, id=upload_id)
    
    current_user = get_current_user(request)
    if str(upload.user_id) != str(current_user.id) and current_user.role != 'admin':
        return _json_error("FORBIDDEN", "Access denied", 403)
    
    try:
        client = _get_minio_client()
        bucket = _bucket_name()
        with client.get_object(bucket, upload.minio_key) as response:
            content = response.read().decode("utf-8-sig")
        
        rows = list(csv.reader(io.StringIO(content)))
        if not rows:
            return _json_error("PROCESSING_ERROR", "Uploaded file is empty.", 400)
        
        headers = rows[0]
        sample_data = rows[1:6]
        
        UploadExtension.objects.update_or_create(
            upload=upload,
            defaults={'source_headers': headers, 'sample_data': sample_data}
        )
        return JsonResponse({
            'upload_id': str(upload.id), 'file_name': upload.file_name,
            'headers': headers, 'sample_data': sample_data,
            'row_count': len(rows) - 1
        })
    except Exception as e:
        return _json_error("PROCESSING_ERROR", f"Failed to preview file: {e}", 500)


@csrf_exempt
@user_access_required
def user_select_template_view(request, upload_id):
    """User selects a template for their upload. DOES NOT trigger the pipeline."""
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])

    try:
        data = json.loads(request.body or b"{}")
        template_id = data.get("template_id")
    except (json.JSONDecodeError, AttributeError):
        return _json_error("BAD_REQUEST", "Invalid JSON body or missing template_id")

    if not template_id:
        return _json_error("BAD_REQUEST", "template_id is required")

    upload = get_object_or_404(Upload, id=upload_id)
    
    current_user = get_current_user(request)
    if str(upload.user_id) != str(current_user.id) and current_user.role != 'admin':
        return _json_error("FORBIDDEN", "Access denied", 403)
    
    template = get_object_or_404(DataTemplate, id=template_id, status="active")

    UploadExtension.objects.update_or_create(
        upload=upload,
        defaults={"selected_template": template}
    )

    return JsonResponse({
        "success": True,
        "upload_id": str(upload.id),
        "template_id": str(template.id),
        "message": f'Template "{template.name}" has been selected for this upload.',
    })


@csrf_exempt
@user_access_required
def upload_set_mappings_view(request, upload_id):
    """User sets column mappings for an upload AND triggers the Airflow pipeline."""
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])

    try:
        data = json.loads(request.body or b"{}")
        mappings = data.get("mappings", [])
    except json.JSONDecodeError:
        return _json_error("BAD_REQUEST", "Invalid JSON body")

    try:
        upload = Upload.objects.select_related("template_info__selected_template").get(id=upload_id)
        template = upload.template_info.selected_template
        if not template:
            raise ValueError("No template selected for this upload.")
    except (Upload.DoesNotExist, UploadExtension.DoesNotExist, ValueError) as e:
        return _json_error("BAD_REQUEST", f"Upload not found or template not selected: {e}", 400)

    current_user = get_current_user(request)
    if str(upload.user_id) != str(current_user.id) and current_user.role != 'admin':
        return _json_error("FORBIDDEN", "Access denied", 403)

    with transaction.atomic():
        # Clear existing mappings for this upload
        ColumnMapping.objects.filter(upload=upload).delete()
        
        for mapping_data in mappings:
            source_col = mapping_data.get("source")
            merged_sources = mapping_data.get("merged_sources", [])
            target_col_id = mapping_data.get("target_column_id")
            
            if not target_col_id:
                continue

            try:
                target_column = TemplateColumn.objects.get(id=target_col_id, template=template)
                
                # Handle regular column mapping (single source)
                if source_col:
                    ColumnMapping.objects.update_or_create(
                        upload=upload,
                        source_column=source_col,
                        defaults={
                            'template': template,
                            'target_column': target_column,
                            'transform_function': mapping_data.get("transform_function"),
                            'transform_params': mapping_data.get("transform_params", {}),
                        }
                    )
                
                # Handle merged column mapping (multiple sources)
                elif merged_sources:
                    # Filter out empty/null sources
                    valid_sources = [source for source in merged_sources if source]
                    if valid_sources:
                        # Create a single mapping record for merged columns
                        # Use the first valid source as the primary source_column
                        primary_source = valid_sources[0]
                        ColumnMapping.objects.update_or_create(
                            upload=upload,
                            source_column=primary_source,
                            defaults={
                                'template': template,
                                'target_column': target_column,
                                'transform_function': mapping_data.get("transform_function"),
                                'transform_params': {
                                    **mapping_data.get("transform_params", {}),
                                    'is_merged': True,
                                    'merged_sources': valid_sources,
                                    'primary_source': primary_source
                                },
                            }
                        )
                
            except TemplateColumn.DoesNotExist:
                return _json_error("BAD_REQUEST", f"Invalid target column ID: {target_col_id}", 400)
        
        upload.status = "mapped"
        upload.save()
        
        upload.template_info.mapping_completed = True
        upload.template_info.save()

    logger.info(f"Mappings saved for upload {upload.id}. Triggering Airflow pipeline.")
    orchestrator_resp = _notify_orchestrator(
        upload_id=upload.id,
        minio_key=upload.minio_key
    )

    response_data = {
        "success": True,
        "upload_id": str(upload.id),
        "message": "Mappings saved and processing has started.",
    }
    if orchestrator_resp and "runId" in orchestrator_resp:
        response_data["runId"] = orchestrator_resp["runId"]

    return JsonResponse(response_data)


# ===================================================================
# ADMIN: Deletion and Usage Checks
# ===================================================================

@csrf_exempt
@admin_required
def admin_delete_template_column_view(request, template_id, column_id):
    """Admin: Delete a specific column from a template."""
    if request.method != "DELETE":
        return HttpResponseNotAllowed(["DELETE"])
    
    template = get_object_or_404(DataTemplate, id=template_id)
    column = get_object_or_404(TemplateColumn, id=column_id, template=template)
    
    if template.uploads.filter(upload__status__in=['mapped', 'transformed']).exists():
        return _json_error("TEMPLATE_IN_USE", "Cannot delete column: template is in use by active uploads.", 400)
        
    column_name = column.name
    column.delete()
    return JsonResponse({"success": True, "message": f"Column '{column_name}' deleted."})


@csrf_exempt
@admin_required
def admin_delete_template_view(request, template_id):
    """Admin: Delete an entire template."""
    if request.method != "DELETE":
        return HttpResponseNotAllowed(["DELETE"])
    
    template = get_object_or_404(DataTemplate, id=template_id)
    
    if template.uploads.filter(upload__status__in=['mapped', 'transformed']).exists() and not request.GET.get('force'):
        return _json_error("TEMPLATE_IN_USE", "Template is in use by active uploads. Use ?force=true to override.", 400)

    template_name = template.name
    template.delete()
    return JsonResponse({"success": True, "message": f"Template '{template_name}' deleted."})


@admin_required
def admin_template_usage_view(request, template_id):
    """Admin: Check a template's usage statistics."""
    if request.method != "GET":
        return HttpResponseNotAllowed(["GET"])
        
    template = get_object_or_404(DataTemplate, id=template_id)
    usage_stats = template.uploads.values('upload__status').annotate(count=Count('upload__status'))
    
    status_counts = {stat['upload__status']: stat['count'] for stat in usage_stats}
    total_uploads = sum(status_counts.values())
    active_uploads = sum(count for status, count in status_counts.items() if status in ['mapped', 'transformed'])

    return JsonResponse({
        'template_id': str(template.id),
        'template_name': template.name,
        'total_uploads': total_uploads,
        'active_uploads': active_uploads,
        'status_breakdown': status_counts
    })