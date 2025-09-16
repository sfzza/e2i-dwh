import uuid
from django.db import models
from django.contrib.auth.models import User


class Upload(models.Model):
    # ADDED more detailed statuses for better tracking
    STATUS = (
        ("pending", "Pending"),
        ("uploaded", "Uploaded"),
        ("mapped", "Mapped"),
        ("transformed", "Transformed"),
        ("completed", "Completed"),
        ("failed", "Failed"),
        ("canceled", "Canceled"),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user_id = models.UUIDField()
    file_name = models.TextField()
    minio_key = models.TextField(unique=True)
    bytes = models.BigIntegerField(default=0)
    content_type = models.CharField(max_length=128, null=True, blank=True)
    checksum_sha256 = models.CharField(max_length=64, null=True, blank=True)
    dataset = models.CharField(max_length=64, null=True, blank=True)
    status = models.CharField(max_length=16, choices=STATUS, default="pending")
    error = models.TextField(null=True, blank=True)
    validated_at = models.DateTimeField(null=True, blank=True)
    orchestrator_triggered_at = models.DateTimeField(null=True, blank=True)
    pipeline_run_id = models.CharField(max_length=128, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "uploads"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user_id"], name="idx_uploads_user"),
            models.Index(fields=["status"], name="idx_uploads_status"),
            models.Index(fields=["dataset"], name="idx_uploads_dataset"),
            models.Index(fields=["created_at"], name="idx_uploads_created"),
        ]

    def __str__(self) -> str:
        return f"{self.file_name} [{self.status}]"

class ValidationReport(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    upload = models.OneToOneField(Upload, on_delete=models.CASCADE, related_name="validation")
    required_headers_missing = models.JSONField(default=list, blank=True)
    extra_headers = models.JSONField(default=list, blank=True)
    total_rows = models.BigIntegerField(null=True, blank=True)
    empty_rows = models.BigIntegerField(null=True, blank=True)
    encoding = models.CharField(max_length=32, null=True, blank=True)
    warnings = models.JSONField(default=list, blank=True)
    errors = models.JSONField(default=list, blank=True)
    stats = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "validation_reports"
        ordering = ["-created_at"]

class DataTemplate(models.Model):
    STATUS_CHOICES = (
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('archived', 'Archived'),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    created_by = models.UUIDField()
    created_from_upload = models.ForeignKey(
        'Upload',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_templates'
    )
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default='draft')
    version = models.IntegerField(default=1)

    # --- THIS IS THE KEY IMPROVEMENT ---
    target_table = models.CharField(max_length=128, blank=False, null=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'data_templates'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['created_by'], name='idx_templates_creator'),
            models.Index(fields=['status'], name='idx_templates_status'),
            models.Index(fields=['target_table'], name='idx_templates_table'),
        ]

    def __str__(self):
        return f"{self.name} (v{self.version})"

class TemplateColumn(models.Model):
    DATA_TYPES = (
        ('string', 'String'), ('integer', 'Integer'), ('float', 'Float'),
        ('datetime', 'DateTime'), ('date', 'Date'), ('boolean', 'Boolean'),
    )
    PROCESSING_TYPES = (
        ('none', 'No Processing'), ('tokenize', 'Tokenize (PII)'), ('hash', 'Hash'),
        ('encrypt', 'Encrypt'), ('normalize', 'Normalize'),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    template = models.ForeignKey(DataTemplate, on_delete=models.CASCADE, related_name='columns')
    name = models.CharField(max_length=128)
    display_name = models.CharField(max_length=128)
    data_type = models.CharField(max_length=16, choices=DATA_TYPES, default='string')
    is_required = models.BooleanField(default=False)
    max_length = models.IntegerField(null=True, blank=True)
    min_value = models.FloatField(null=True, blank=True)
    max_value = models.FloatField(null=True, blank=True)
    regex_pattern = models.CharField(max_length=512, blank=True, null=True)
    processing_type = models.CharField(max_length=16, choices=PROCESSING_TYPES, default='none')
    processing_config = models.JSONField(default=dict, blank=True)
    order = models.IntegerField(default=0)
    merged_from_columns = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'template_columns'
        ordering = ['order', 'name']
        unique_together = [['template', 'name']]
        indexes = [
            models.Index(fields=['template', 'order'], name='idx_template_cols_order'),
        ]

    def __str__(self):
        return f"{self.template.name}.{self.name}"

class ColumnMapping(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    upload = models.ForeignKey(Upload, on_delete=models.CASCADE, related_name='column_mappings')
    template = models.ForeignKey(DataTemplate, on_delete=models.CASCADE, related_name='upload_mappings')
    source_column = models.CharField(max_length=128)
    target_column = models.ForeignKey(TemplateColumn, on_delete=models.CASCADE, related_name='source_mappings')
    transform_function = models.CharField(max_length=64, blank=True, null=True)
    transform_params = models.JSONField(default=dict, blank=True)
    is_valid = models.BooleanField(default=True)
    validation_errors = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'column_mappings'
        unique_together = [['upload', 'source_column'], ['upload', 'target_column']]
        indexes = [
            models.Index(fields=['upload'], name='idx_mappings_upload'),
            models.Index(fields=['template'], name='idx_mappings_template'),
        ]

    def __str__(self):
        return f"{self.upload.file_name}: {self.source_column} -> {self.target_column.name}"

class UploadExtension(models.Model):
    upload = models.OneToOneField(Upload, on_delete=models.CASCADE, related_name='template_info')
    selected_template = models.ForeignKey(
        DataTemplate, on_delete=models.SET_NULL, null=True, blank=True, related_name='uploads'
    )
    mapping_completed = models.BooleanField(default=False)
    mapping_validated = models.BooleanField(default=False)
    source_headers = models.JSONField(default=list, blank=True)
    sample_data = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'upload_template_info'