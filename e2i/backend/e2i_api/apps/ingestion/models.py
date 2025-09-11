import uuid
from django.db import models
from django.contrib.auth.models import User


class Upload(models.Model):
    STATUS = (
        ("pending", "Pending"),
        ("uploaded", "Uploaded"),
        ("mapped", "Mapped"), 
        ("validated", "Validated"),
        ("failed", "Failed"),
        ("canceled", "Canceled"),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Who uploaded
    user_id = models.UUIDField()

    # File/meta
    file_name = models.TextField()
    minio_key = models.TextField(unique=True)
    bytes = models.BigIntegerField(default=0)
    content_type = models.CharField(max_length=128, null=True, blank=True)
    checksum_sha256 = models.CharField(max_length=64, null=True, blank=True)

    # Optional dataset tag for key scheme landing/{dataset}/YYYY/MM/DD/...
    dataset = models.CharField(max_length=64, null=True, blank=True)

    # Lifecycle
    status = models.CharField(max_length=16, choices=STATUS, default="pending")
    error = models.TextField(null=True, blank=True)
    validated_at = models.DateTimeField(null=True, blank=True)

    # Orchestrator bookkeeping
    orchestrator_triggered_at = models.DateTimeField(null=True, blank=True)
    pipeline_run_id = models.CharField(max_length=128, null=True, blank=True)

    # Timestamps
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

    @property
    def is_valid(self) -> bool:
        return self.status == "validated" and getattr(self, "validation", None) is not None


class ValidationReport(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    upload = models.OneToOneField(
        Upload, on_delete=models.CASCADE, related_name="validation"
    )

    # Header checks
    required_headers_missing = models.JSONField(default=list, blank=True)
    extra_headers = models.JSONField(default=list, blank=True)

    # Stats
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

    def __str__(self) -> str:
        return f"ValidationReport for {self.upload.file_name} ({self.total_rows or 0} rows)"


# START OF NEW MODELS FOR TEMPLATE FUNCTIONALITY

class DataTemplate(models.Model):
    """Templates created by admins for data structure definition"""

    STATUS_CHOICES = (
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('archived', 'Archived'),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)

    # Admin who created this template
    created_by = models.UUIDField()  # Admin user ID
    created_from_upload = models.ForeignKey(
        'Upload',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_templates'
    )

    # Template metadata
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default='draft')
    version = models.IntegerField(default=1)

    # Target table in ClickHouse
    target_table = models.CharField(max_length=64, default='applicants')

    # Timestamps
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
    """Column definitions within a template"""

    DATA_TYPES = (
        ('string', 'String'),
        ('integer', 'Integer'),
        ('float', 'Float'),
        ('datetime', 'DateTime'),
        ('date', 'Date'),
        ('boolean', 'Boolean'),
    )

    PROCESSING_TYPES = (
        ('none', 'No Processing'),
        ('tokenize', 'Tokenize (PII)'),
        ('hash', 'Hash'),
        ('encrypt', 'Encrypt'),
        ('normalize', 'Normalize'),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    template = models.ForeignKey(
        DataTemplate,
        on_delete=models.CASCADE,
        related_name='columns'
    )

    # Column definition
    name = models.CharField(max_length=128)  # Target column name
    display_name = models.CharField(max_length=128)  # Human readable name
    data_type = models.CharField(max_length=16, choices=DATA_TYPES, default='string')

    # Validation rules
    is_required = models.BooleanField(default=False)
    max_length = models.IntegerField(null=True, blank=True)
    min_value = models.FloatField(null=True, blank=True)
    max_value = models.FloatField(null=True, blank=True)
    regex_pattern = models.CharField(max_length=512, blank=True, null=True)

    # Processing configuration
    processing_type = models.CharField(max_length=16, choices=PROCESSING_TYPES, default='none')
    processing_config = models.JSONField(default=dict, blank=True)  # Additional config

    # Display order
    order = models.IntegerField(default=0)

    # Merge configuration (for admin template editing)
    merged_from_columns = models.JSONField(default=list, blank=True)  # Source column names that were merged

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
    """Maps source file columns to template columns for each upload"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    upload = models.ForeignKey(
        'Upload',
        on_delete=models.CASCADE,
        related_name='column_mappings'
    )
    template = models.ForeignKey(
        DataTemplate,
        on_delete=models.CASCADE,
        related_name='upload_mappings'
    )

    # Mapping definition
    source_column = models.CharField(max_length=128)  # Column name in uploaded file
    target_column = models.ForeignKey(
        TemplateColumn,
        on_delete=models.CASCADE,
        related_name='source_mappings'
    )

    # Transformation rules for this specific mapping
    transform_function = models.CharField(max_length=64, blank=True, null=True)  # e.g., 'upper', 'trim', 'format_date'
    transform_params = models.JSONField(default=dict, blank=True)

    # Validation results for this mapping
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
    """Extension to the existing Upload model for template functionality"""

    upload = models.OneToOneField(
        'Upload',
        on_delete=models.CASCADE,
        related_name='template_info'
    )

    # Template selection
    selected_template = models.ForeignKey(
        DataTemplate,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='uploads'
    )

    # Mapping status
    mapping_completed = models.BooleanField(default=False)
    mapping_validated = models.BooleanField(default=False)

    # Preview data for mapping interface
    source_headers = models.JSONField(default=list, blank=True)  # Headers from uploaded file
    sample_data = models.JSONField(default=list, blank=True)     # First few rows for preview

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'upload_template_info'
