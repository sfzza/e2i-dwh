from django.contrib import admin
from .models import Upload, ValidationReport


@admin.register(Upload)
class UploadAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "file_name",
        "status",
        "bytes",
        "created_at",
    )
    search_fields = ("file_name", "minio_key")
    list_filter = ("status", "created_at")
    ordering = ("-created_at",)
    readonly_fields = ("created_at", "updated_at")  # prevents accidental edits
    date_hierarchy = "created_at"


@admin.register(ValidationReport)
class ValidationReportAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "upload",
        "total_rows",
        "empty_rows",
        "encoding",
        "created_at",
    )
    search_fields = ("upload__file_name",)
    list_filter = ("encoding", "created_at")
    ordering = ("-created_at",)
    readonly_fields = ("created_at",)
    date_hierarchy = "created_at"
