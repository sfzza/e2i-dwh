from django.db import models
from django.utils import timezone
import uuid

# Create your models here.
class AuditLog(models.Model):
    EVENT_TYPES = (
        ("QUERY", "Query Run"),
        ("EXPORT", "Data Export"),
    )

    event_type = models.CharField(max_length=10, choices=EVENT_TYPES)
    username = models.CharField(max_length=255, blank=True, null=True)
    roles = models.JSONField(default=list)
    dataset = models.CharField(max_length=255)
    columns = models.JSONField(default=list)
    filters = models.JSONField(default=list)
    order_by = models.JSONField(default=list)
    limit = models.IntegerField(null=True, blank=True)
    offset = models.IntegerField(null=True, blank=True)
    row_count = models.IntegerField(null=True, blank=True)
    duration_ms = models.IntegerField(null=True, blank=True)
    ip = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True, null=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "audit_log"
        ordering = ["-timestamp"]


class ExportJob(models.Model):
    STATUS_CHOICES = (
        ("RUNNING", "Running"),
        ("DONE", "Done"),
        ("FAILED", "Failed"),
        ("PENDING", "Pending"),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_by = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="PENDING")
    error = models.TextField(blank=True, null=True)
    roles = models.JSONField(default=list)
    dataset = models.CharField(max_length=255)
    columns = models.JSONField(default=list)
    filters = models.JSONField(default=list)
    order_by = models.JSONField(default=list)
    file_path = models.CharField(max_length=255, blank=True, null=True)
    row_count = models.IntegerField(null=True, blank=True)
    file_format = models.CharField(max_length=10, default="CSV")
    signed_token = models.TextField(blank=True, null=True)
    signed_expires_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "export_job"
        ordering = ["-created_at"]