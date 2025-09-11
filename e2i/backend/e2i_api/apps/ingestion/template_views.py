import csv
import io
import json
import pandas as pd
from django.http import JsonResponse, HttpResponseNotAllowed
from django.views.decorators.csrf import csrf_exempt
from django.db import transaction
from django.db.models import Count
from django.shortcuts import get_object_or_404

from .models import DataTemplate, TemplateColumn, Upload, ColumnMapping, UploadExtension
from .views import _current_user_id, _json_error, _get_minio_client, _bucket_name


# =================== TEMPLATE MANAGEMENT ===================

@csrf_exempt
def template_list_view(request):
    """List all templates (for template selection during upload)"""
    if request.method != "GET":
        return HttpResponseNotAllowed(["GET"])

    templates = DataTemplate.objects.filter(status='active').prefetch_related('columns')

    result = []
    for template in templates:
        result.append({
            'id': str(template.id),
            'name': template.name,
            'description': template.description,
            'version': template.version,
            'target_table': template.target_table,
            'column_count': template.columns.count(),
            'columns': [
                {
                    'name': col.name,
                    'display_name': col.display_name,
                    'data_type': col.data_type,
                    'is_required': col.is_required,
                    'processing_type': col.processing_type,
                }
                for col in template.columns.all()
            ],
            'created_at': template.created_at.isoformat(),
        })

    return JsonResponse({'templates': result})


@csrf_exempt
def template_create_from_upload_view(request):
    """Admin creates a template from an uploaded file"""
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])

    try:
        data = json.loads(request.body or b"{}")
    except json.JSONDecodeError:
        return _json_error("BAD_REQUEST", "Invalid JSON body")

    upload_id = data.get('upload_id')
    template_name = data.get('name', '').strip()
    description = data.get('description', '')
    target_table = data.get('target_table', 'applicants')

    if not upload_id or not template_name:
        return _json_error("BAD_REQUEST", "upload_id and name are required")

    try:
        upload = Upload.objects.get(id=upload_id)
    except Upload.DoesNotExist:
        return _json_error("NOT_FOUND", "Upload not found", 404)

    # Extract columns from the uploaded file
    try:
        client = _get_minio_client()
        bucket = _bucket_name()

        # Get object from MinIO and read content
        with client.get_object(bucket, upload.minio_key) as response:
            content = response.read().decode('utf-8')

        # Read the file content into a Pandas DataFrame for easy processing
        df = pd.read_csv(io.StringIO(content))

    except Exception as e:
        return _json_error("PROCESSING_ERROR", f"Failed to process file: {str(e)}", 500)

    user_id = _current_user_id(request)

    # Create template with transaction
    with transaction.atomic():
        template = DataTemplate.objects.create(
            name=template_name,
            description=description,
            created_by=user_id,
            created_from_upload=upload,
            target_table=target_table,
            status='draft'  # Start as draft for editing
        )

        # Create columns based on file headers
        for idx, header in enumerate(df.columns):
            if not header.strip():
                continue

            # Infer data type from pandas
            col_name = header.strip().lower().replace(' ', '_').replace('.', '_')
            dtype = str(df[header].dtype)

            if 'int' in dtype:
                data_type = 'integer'
            elif 'float' in dtype:
                data_type = 'float'
            elif 'datetime' in dtype:
                data_type = 'datetime'
            elif 'bool' in dtype:
                data_type = 'boolean'
            else:
                data_type = 'string'

            # Determine if this looks like PII that should be tokenized
            processing_type = 'none'
            if any(keyword in col_name.lower() for keyword in ['name', 'email', 'phone', 'ssn', 'id']):
                processing_type = 'tokenize'

            TemplateColumn.objects.create(
                template=template,
                name=col_name,
                display_name=header.strip(),
                data_type=data_type,
                processing_type=processing_type,
                order=idx,
                is_required=False  # Admin can edit this later
            )

    return JsonResponse({
        'id': str(template.id),
        'name': template.name,
        'status': template.status,
        'columns': [
            {
                'id': str(col.id),
                'name': col.name,
                'display_name': col.display_name,
                'data_type': col.data_type,
                'processing_type': col.processing_type,
                'is_required': col.is_required,
                'order': col.order,
            }
            for col in template.columns.all()
        ]
    }, status=201)


@csrf_exempt
def template_edit_view(request, template_id):
    """Admin edits template columns (merge, edit, delete)"""
    if request.method not in ["GET", "PUT", "DELETE"]:
        return HttpResponseNotAllowed(["GET", "PUT", "DELETE"])

    template = get_object_or_404(DataTemplate, id=template_id)

    if request.method == "GET":
        # Return template for editing
        return JsonResponse({
            'id': str(template.id),
            'name': template.name,
            'description': template.description,
            'status': template.status,
            'target_table': template.target_table,
            'columns': [
                {
                    'id': str(col.id),
                    'name': col.name,
                    'display_name': col.display_name,
                    'data_type': col.data_type,
                    'processing_type': col.processing_type,
                    'is_required': col.is_required,
                    'order': col.order,
                    'merged_from_columns': col.merged_from_columns,
                    'max_length': col.max_length,
                    'regex_pattern': col.regex_pattern,
                }
                for col in template.columns.all().order_by('order')
            ]
        })

    elif request.method == "PUT":
        # Update template and columns
        try:
            data = json.loads(request.body or b"{}")
        except json.JSONDecodeError:
            return _json_error("BAD_REQUEST", "Invalid JSON body")

        with transaction.atomic():
            # Update template metadata
            if 'name' in data:
                template.name = data['name']
            if 'description' in data:
                template.description = data['description']
            if 'target_table' in data:
                template.target_table = data['target_table']
            template.save()

            # Update columns
            if 'columns' in data:
                # Delete existing columns and recreate (simpler than complex updates)
                template.columns.all().delete()

                for col_data in data['columns']:
                    TemplateColumn.objects.create(
                        template=template,
                        name=col_data.get('name', ''),
                        display_name=col_data.get('display_name', ''),
                        data_type=col_data.get('data_type', 'string'),
                        processing_type=col_data.get('processing_type', 'none'),
                        is_required=col_data.get('is_required', False),
                        order=col_data.get('order', 0),
                        merged_from_columns=col_data.get('merged_from_columns', []),
                        max_length=col_data.get('max_length'),
                        regex_pattern=col_data.get('regex_pattern'),
                    )

        return JsonResponse({'success': True, 'message': 'Template updated successfully'})

    elif request.method == "DELETE":
        # Delete template
        template.delete()
        return JsonResponse({'success': True, 'message': 'Template deleted successfully'})


@csrf_exempt
def template_activate_view(request, template_id):
    """Admin activates a template (makes it available for use)"""
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])

    template = get_object_or_404(DataTemplate, id=template_id)
    template.status = 'active'
    template.save()

    return JsonResponse({'success': True, 'status': template.status})


# =================== COLUMN MAPPING DURING UPLOAD ===================

@csrf_exempt
def upload_preview_view(request, upload_id):
    """Get file preview for column mapping interface"""
    if request.method != "GET":
        return HttpResponseNotAllowed(["GET"])

    try:
        upload = Upload.objects.get(id=upload_id)
    except Upload.DoesNotExist:
        return _json_error("NOT_FOUND", "Upload not found", 404)

    try:
        client = _get_minio_client()
        bucket = _bucket_name()

        with client.get_object(bucket, upload.minio_key) as response:
            content = response.read().decode('utf-8')

        # Read the entire CSV content into a list of lists
        csv_reader = csv.reader(io.StringIO(content))
        rows = list(csv_reader)

        if not rows:
            return _json_error("PROCESSING_ERROR", "Uploaded file is empty or invalid", 400)

        headers = rows[0]
        sample_rows = rows[1:6]  # Get headers and first 5 rows

        # Store preview data for mapping interface
        upload_ext, created = UploadExtension.objects.get_or_create(
            upload=upload,
            defaults={
                'source_headers': headers,
                'sample_data': sample_rows,
            }
        )
        if not created:
            upload_ext.source_headers = headers
            upload_ext.sample_data = sample_rows
            upload_ext.save()

        return JsonResponse({
            'upload_id': str(upload.id),
            'file_name': upload.file_name,
            'headers': headers,
            'sample_data': sample_rows,
            'row_count': len(rows) - 1 if len(rows) > 0 else 0
        })

    except Exception as e:
        return _json_error("PROCESSING_ERROR", f"Failed to preview file: {str(e)}", 500)


@csrf_exempt
def upload_set_mappings_view(request, upload_id):
    """Set column mappings for an upload"""
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])

    try:
        data = json.loads(request.body or b"{}")
    except json.JSONDecodeError:
        return _json_error("BAD_REQUEST", "Invalid JSON body")

    template_id = data.get('template_id')
    mappings = data.get('mappings', [])  # [{'source': 'Name', 'target_column_id': 'uuid'}, ...]

    if not template_id or not mappings:
        return _json_error("BAD_REQUEST", "template_id and mappings are required")

    try:
        upload = Upload.objects.get(id=upload_id)
        template = DataTemplate.objects.get(id=template_id)
    except (Upload.DoesNotExist, DataTemplate.DoesNotExist) as e:
        return _json_error("NOT_FOUND", f"Upload or template not found: {str(e)}", 404)

    with transaction.atomic():
        # Clear existing mappings
        ColumnMapping.objects.filter(upload=upload).delete()

        # Create new mappings
        for mapping in mappings:
            source_col = mapping.get('source')
            target_col_id = mapping.get('target_column_id')

            if not source_col or not target_col_id:
                continue

            try:
                target_column = TemplateColumn.objects.get(id=target_col_id, template=template)

                ColumnMapping.objects.create(
                    upload=upload,
                    template=template,
                    source_column=source_col,
                    target_column=target_column,
                    transform_function=mapping.get('transform_function'),
                    transform_params=mapping.get('transform_params', {}),
                )
            except TemplateColumn.DoesNotExist:
                return _json_error("BAD_REQUEST", f"Invalid target column: {target_col_id}")

        # Update upload extension
        upload_ext, created = UploadExtension.objects.get_or_create(upload=upload)
        upload_ext.selected_template = template
        upload_ext.mapping_completed = True
        upload_ext.save()

        # Update upload status to ready for processing
        upload.status = 'mapped'
        upload.save()

    return JsonResponse({
        'success': True,
        'upload_id': str(upload.id),
        'template_id': str(template.id),
        'mappings_count': len(mappings)
    })

# =================== ADMIN DELETION FUNCTIONS ===================

@csrf_exempt
def admin_delete_template_column_view(request, template_id, column_id):
    """Admin deletes a specific column from a template"""
    if request.method != "DELETE":
        return HttpResponseNotAllowed(["DELETE"])

    template = get_object_or_404(DataTemplate, id=template_id)
    column_to_delete = get_object_or_404(TemplateColumn, id=column_id, template=template)

    # Check if template is being used by any active uploads
    # A template is considered in use if it is referenced by an UploadExtension
    # and the corresponding Upload status is not 'completed' or 'failed'
    active_uploads_count = UploadExtension.objects.filter(
        selected_template=template,
        upload__status__in=['upload_received', 'mapped', 'processing']
    ).count()

    if active_uploads_count > 0:
        return _json_error(
            "TEMPLATE_IN_USE",
            f"Cannot delete column - template is being used by {active_uploads_count} active uploads",
            400
        )

    column_name = column_to_delete.name
    column_to_delete.delete()

    return JsonResponse({
        'success': True,
        'message': f"Column '{column_name}' deleted from template '{template.name}'",
        'deleted_column': column_name
    })


@csrf_exempt
def admin_delete_template_view(request, template_id):
    """Admin deletes an entire template"""
    if request.method != "DELETE":
        return HttpResponseNotAllowed(["DELETE"])

    template = get_object_or_404(DataTemplate, id=template_id)

    # Check usage
    total_uploads = UploadExtension.objects.filter(selected_template=template).count()
    active_uploads = UploadExtension.objects.filter(
        selected_template=template,
        upload__status__in=['upload_received', 'mapped', 'processing']
    ).count()

    force_delete = request.GET.get('force', 'false').lower() == 'true'

    if active_uploads > 0 and not force_delete:
        return _json_error(
            "TEMPLATE_IN_USE",
            f"Cannot delete template - {active_uploads} uploads are processing. Use ?force=true to force deletion.",
            400
        )

    if total_uploads > 0 and not force_delete:
        return JsonResponse({
            'success': False,
            'message': f"Template has {total_uploads} upload records. Use ?force=true to delete anyway.",
            'total_uploads': total_uploads,
            'active_uploads': active_uploads
        }, status=400)

    template_name = template.name

    with transaction.atomic():
        if force_delete and active_uploads > 0:
            # Mark active uploads as failed
            Upload.objects.filter(
                uploadextension__selected_template=template,
                status__in=['upload_received', 'mapped', 'processing']
            ).update(status='failed', error='Template was deleted')

        template.delete()  # Cascades to columns and mappings

    return JsonResponse({
        'success': True,
        'message': f"Template '{template_name}' deleted successfully",
        'uploads_affected': total_uploads,
        'force_deleted': force_delete
    })


@csrf_exempt
def admin_template_usage_view(request, template_id):
    """Check template usage before deletion"""
    if request.method != "GET":
        return HttpResponseNotAllowed(["GET"])

    template = get_object_or_404(DataTemplate, id=template_id)

    # Use a raw SQL query or a more complex ORM query to get counts
    # The `UploadExtension` model is the link
    upload_stats = UploadExtension.objects.filter(selected_template=template).values(
        'upload__status'
    ).annotate(count=Count('upload__status'))

    status_counts = {stat['upload__status']: stat['count'] for stat in upload_stats}
    total_uploads = sum(status_counts.values())
    active_statuses = ['upload_received', 'mapped', 'processing']
    active_uploads = sum(
        count for status, count in status_counts.items()
        if status in active_statuses
    )

    return JsonResponse({
        'template_id': str(template.id),
        'template_name': template.name,
        'usage_summary': {
            'total_uploads': total_uploads,
            'active_uploads': active_uploads,
            'status_breakdown': status_counts,
            'can_delete_safely': active_uploads == 0
        },
        'deletion_options': {
            'safe_delete': active_uploads == 0,
            'force_delete_available': True,
            'force_delete_warning': f"Will affect {total_uploads} upload records" if total_uploads > 0 else None
        }
    })
