import uuid
from django.db import models


class Upload(models.Model):
    STATUS = (
        ("pending", "Pending"),
        ("uploaded", "Uploaded"),
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
