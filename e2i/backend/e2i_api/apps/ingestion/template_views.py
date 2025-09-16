import csv
import io
import json
import logging
import uuid
import pandas as pd
from django.db import transaction
from django.db.models import Count
from django.http import JsonResponse, HttpResponseNotAllowed
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import csrf_exempt

from .models import (
    ColumnMapping,
    DataTemplate,
    TemplateColumn,
    Upload,
    UploadExtension,
)
from .views import (
    _current_user_id,
    _get_minio_client,
    _bucket_name,
    _json_error,
    _notify_orchestrator,
)

logger = logging.getLogger(__name__)

# ===================================================================
# ADMIN: Template Management
# ===================================================================

@csrf_exempt
def template_list_view(request):
    """List all active templates for selection."""
    if request.method != "GET":
        return HttpResponseNotAllowed(["GET"])

    templates = DataTemplate.objects.filter(status="active").prefetch_related("columns")
    result = [
        {
            "id": str(template.id),
            "name": template.name,
            "description": template.description,
            "version": template.version,
            "target_table": template.target_table,
            "column_count": template.columns.count(),
            "columns": [
                {
                    "name": col.name,
                    "display_name": col.display_name,
                    "data_type": col.data_type,
                    "is_required": col.is_required,
                }
                for col in template.columns.all()
            ],
            "created_at": template.created_at.isoformat(),
        }
        for template in templates
    ]
    return JsonResponse({"templates": result})


@csrf_exempt
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
    target_table = data.get('target_table') # Ensure this is provided by the admin UI

    if not all([upload_id, template_name, target_table]):
        return _json_error("BAD_REQUEST", "upload_id, name, and target_table are required")

    upload = get_object_or_404(Upload, id=upload_id)
    user_id = _current_user_id(request)

    try:
        client = _get_minio_client()
        bucket = _bucket_name()
        with client.get_object(bucket, upload.minio_key) as response:
            content = response.read().decode("utf-8-sig") # Use utf-8-sig to handle BOM
        df = pd.read_csv(io.StringIO(content))
    except Exception as e:
        return _json_error("PROCESSING_ERROR", f"Failed to read file from storage: {e}", 500)

    with transaction.atomic():
        template = DataTemplate.objects.create(
            name=template_name,
            description=data.get("description", ""),
            created_by=user_id,
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
    
    return JsonResponse({"id": str(template.id), "status": template.status}, status=201)


@csrf_exempt
def template_edit_view(request, template_id):
    """Admin: Get, update, or delete a template definition."""
    template = get_object_or_404(DataTemplate.objects.prefetch_related('columns'), id=template_id)

    if request.method == "GET":
        return JsonResponse({
            'id': str(template.id), 'name': template.name, 'description': template.description,
            'status': template.status, 'target_table': template.target_table,
            'columns': [{'id': str(c.id), 'name': c.name, 'display_name': c.display_name,
                         'data_type': c.data_type, 'is_required': c.is_required, 'order': c.order}
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
                    TemplateColumn.objects.create(template=template, **col_data)
        return JsonResponse({"success": True, "message": "Template updated."})
    elif request.method == "DELETE":
        template.delete()
        return JsonResponse({"success": True, "message": "Template deleted."})
    
    return HttpResponseNotAllowed(["GET", "PUT", "DELETE"])


@csrf_exempt
def template_activate_view(request, template_id):
    """Admin: Activate a template to make it available for users."""
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    template = get_object_or_404(DataTemplate, id=template_id)
    template.status = "active"
    template.save()
    return JsonResponse({"success": True, "status": template.status})


# ===================================================================
# USER: Mapping Workflow
# ===================================================================

@csrf_exempt
def upload_preview_view(request, upload_id):
    """User: Get a preview of an uploaded file for the mapping UI."""
    if request.method != "GET":
        return HttpResponseNotAllowed(["GET"])
    upload = get_object_or_404(Upload, id=upload_id)
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
def user_select_template_view(request, upload_id):
    """
    CORRECTED: User selects a template for their upload. DOES NOT trigger the pipeline.
    """
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
def upload_set_mappings_view(request, upload_id):
    """
    CORRECTED: User sets column mappings for an upload AND triggers the Airflow pipeline.
    """
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])

    try:
        data = json.loads(request.body or b"{}")
        mappings = data.get("mappings", [])
    except json.JSONDecodeError:
        return _json_error("BAD_REQUEST", "Invalid JSON body")

    try:
        # Eagerly load related objects to ensure a template has been selected
        upload = Upload.objects.select_related("template_info__selected_template").get(id=upload_id)
        template = upload.template_info.selected_template
        if not template:
            raise ValueError("No template selected for this upload.")
    except (Upload.DoesNotExist, UploadExtension.DoesNotExist, ValueError) as e:
        return _json_error("BAD_REQUEST", f"Upload not found or template not selected: {e}", 400)

    with transaction.atomic():
        # Clear previous mappings for this upload
        ColumnMapping.objects.filter(upload=upload).delete()
        
        # Create new mapping records
        for mapping_data in mappings:
            source_col = mapping_data.get("source")
            target_col_id = mapping_data.get("target_column_id")
            if not source_col or not target_col_id:
                continue

            try:
                target_column = TemplateColumn.objects.get(id=target_col_id, template=template)
                ColumnMapping.objects.create(
                    upload=upload,
                    template=template,
                    source_column=source_col,
                    target_column=target_column,
                    transform_function=mapping_data.get("transform_function"),
                    transform_params=mapping_data.get("transform_params", {}),
                )
            except TemplateColumn.DoesNotExist:
                return _json_error("BAD_REQUEST", f"Invalid target column ID: {target_col_id}", 400)
        
        # Update status to indicate readiness for processing
        upload.status = "mapped"
        upload.save()
        
        upload.template_info.mapping_completed = True
        upload.template_info.save()

    # --- TRIGGER THE AIRFLOW PIPELINE ---
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


@csrf_exempt
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