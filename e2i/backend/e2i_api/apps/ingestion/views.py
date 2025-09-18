# e2i_api/apps/ingestion/views.py - Updated with authentication

from django.shortcuts import render
from django.http import JsonResponse, HttpRequest, HttpResponseNotAllowed
from django.views.decorators.csrf import csrf_exempt
from django.db import transaction
from django.utils.text import get_valid_filename

import csv
import datetime as dt
import hmac
import hashlib
import io
import json
import os
import typing as t
import uuid
import httpx

from .models import Upload, ValidationReport

# Import authentication decorators
from e2i_api.apps.common.auth import (
    require_auth, 
    admin_required, 
    user_access_required,
    get_current_user,
    get_current_user_id
)

try:
    from minio import Minio
except Exception:  # pragma: no cover
    Minio = None  # type: ignore

try:
    from charset_normalizer import from_bytes as cn_from_bytes
except Exception:  # pragma: no cover
    cn_from_bytes = None  # type: ignore

# ---------------------------------------------------------------- Utilities ---
def _env_bool(key: str, default: bool = False) -> bool:
    v = os.getenv(key)
    if v is None:
        return default
    return v.lower() in ("1", "true", "yes", "on")


def _env_int(key: str, default: int) -> int:
    try:
        return int(os.getenv(key, str(default)))
    except Exception:
        return default


def _env_float(key: str, default: float) -> float:
    try:
        return float(os.getenv(key, str(default)))
    except Exception:
        return default


def _required_headers() -> t.List[str]:
    return []


def _json_error(code: str, message: str, status: int = 400, details: t.Optional[dict] = None):
    payload = {"code": code, "message": message}
    if details:
        payload["details"] = details
    return JsonResponse(payload, status=status)

def _size_limit_mb() -> float:
    return _env_float("INGEST_MAX_SIZE_MB", 100.0)

# ---------------------------------------------------------------- MinIO utils
_MINIO_CLIENT: t.Optional["Minio"] = None  # cached


def _get_minio_client() -> "Minio":
    if Minio is None:
        raise RuntimeError("Dependency 'minio' is not installed")
    global _MINIO_CLIENT
    if _MINIO_CLIENT:
        return _MINIO_CLIENT
    endpoint = os.getenv("MINIO_ENDPOINT", "localhost:9000")
    access_key = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
    secret_key = os.getenv("MINIO_SECRET_KEY", "minioadmin")
    use_ssl = _env_bool("MINIO_USE_SSL", False)
    client = Minio(endpoint, access_key=access_key, secret_key=secret_key, secure=use_ssl)
    bucket = os.getenv("MINIO_BUCKET", "landing")
    try:
        if not client.bucket_exists(bucket):
            client.make_bucket(bucket)
    except Exception:
        pass
    _MINIO_CLIENT = client
    return client


def _bucket_name() -> str:
    return os.getenv("MINIO_BUCKET", "landing")


def _build_object_key(user_id: uuid.UUID, filename: str) -> str:
    today = dt.date.today()
    safe = get_valid_filename(filename or "file.csv")
    return f"{today.year}/{today.month:02d}/{today.day:02d}/{uuid.uuid4()}_{safe}"


# UPDATED: Use the new authentication system
def _current_user_id(req: HttpRequest) -> uuid.UUID:
    """Get current user ID - updated to use new auth system"""
    return get_current_user_id(req) or uuid.UUID(int=0)


def _detect_encoding(bucket: str, key: str, byte_limit: int = 65536) -> str:
    client = _get_minio_client()
    with client.get_object(bucket, key, offset=0, length=byte_limit) as resp:
        chunk = resp.read()
    if cn_from_bytes is None:
        return "utf-8"
    best = cn_from_bytes(chunk).best()
    enc = (best.encoding or "utf-8").lower()
    return enc


def _validate_csv(bucket: str, key: str) -> dict:
    client = _get_minio_client()
    max_rows = _env_int("INGEST_MAX_ROWS", 1_000_000)
    warn_pct = _env_float("INGEST_EMPTY_WARN_PCT", 1.0)
    fail_pct = _env_float("INGEST_EMPTY_FAIL_PCT", 5.0)
    required = _required_headers()
    encoding = _detect_encoding(bucket, key)
    warnings, errors = [], []
    total_rows, empty_rows = 0, 0
    missing, extra = [], []
    if encoding not in ("utf-8", "ascii"):
        errors.append(f"Unsupported encoding: {encoding}. Only UTF-8/ASCII allowed.")
    with client.get_object(bucket, key) as resp:
        data = resp.read()
    text_stream = io.TextIOWrapper(io.BytesIO(data), encoding=encoding, errors="replace", newline="")
    reader = csv.reader(text_stream)
    try:
        header = next(reader, [])
    except Exception:
        header = []
    missing = [h for h in required if h not in header]
    extra = [h for h in header if h not in required]
    if missing:
        errors.append(f"Missing required headers: {missing}")
    if extra:
        warnings.append(f"Extra headers: {extra}")
    header_len = len(header)
    for row in reader:
        total_rows += 1
        if not any((c or "").strip() for c in row):
            empty_rows += 1
        if header_len and len(row) != header_len:
            errors.append("Row has mismatched column count.")
            break
        if total_rows > max_rows:
            errors.append(f"Row limit exceeded: > {max_rows}")
            break
    if total_rows > 0:
        pct = (empty_rows / total_rows) * 100.0
        if pct > fail_pct:
            errors.append(f"Too many empty rows ({pct:.2f}%).")
        elif pct > warn_pct:
            warnings.append(f"Empty rows warning ({pct:.2f}%).")
    return {
        "encoding": encoding,
        "required_headers_missing": missing,
        "extra_headers": extra,
        "total_rows": total_rows,
        "empty_rows": empty_rows,
        "warnings": warnings,
        "errors": errors,
    }


# NEW: A simplified notify function using httpx
ORCH_URL = os.getenv("ORCHESTRATOR_URL", "http://e2i_orchestrator:8002")

def _notify_orchestrator(upload_id: uuid.UUID, minio_key: str, validation_summary: dict = None, template_id: t.Optional[uuid.UUID] = None) -> t.Optional[dict]:
    with httpx.Client() as client:
        try:
            payload = {
                "pipelineKey": "etl_pipeline",
                "params": {
                    "uploadId": str(upload_id),
                    "minioKey": minio_key,
                    "validation": validation_summary,
                },
                "idempotencyKey": f"upload:{upload_id}"
            }
            if template_id:
                payload["params"]["templateId"] = str(template_id)
            
            response = client.post(
                f"{ORCH_URL}/pipelines/run",  # Add /v1 prefix
                json=payload
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Orchestrator error: {e}")  # Add logging
            return None

# ------------------------------------------------------------------- Views ---
@csrf_exempt
@user_access_required  # Both admin and user can upload
def upload_view(request: HttpRequest):
    """
    Handle direct multipart uploads to Django -> MinIO.
    Requires authentication (admin or user).
    """
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    if Minio is None:
        return _json_error("DEPENDENCY_MISSING", "minio library is required", 500)

    file = request.FILES.get("file")
    if not file:
        return _json_error("BAD_REQUEST", "Missing multipart field 'file'")
    size_mb = (getattr(file, "size", 0) or 0) / (1024 * 1024)
    if size_mb > _size_limit_mb():
        return _json_error("BAD_REQUEST", f"File too large (> {_size_limit_mb()} MB)")

    user_id = _current_user_id(request)
    client = _get_minio_client()
    bucket = _bucket_name()
    key = _build_object_key(user_id, file.name)

    try:
        length = getattr(file, "size", None)
        if length is None:
            data = file.read()
            length = len(data)
            stream = io.BytesIO(data)
        else:
            stream = file.file
        client.put_object(bucket, key, stream, length=length, content_type="text/csv")
    except Exception as ex:
        return _json_error("UPLOAD_FAILED", f"Failed to store object: {ex}", 500)

    with transaction.atomic():
        upload = Upload.objects.create(
            user_id=user_id,
            file_name=file.name,
            minio_key=key,
            bytes=getattr(file, "size", 0),
            status="uploaded"
        )
        summary = _validate_csv(bucket, key)
        ValidationReport.objects.create(
            upload=upload,
            required_headers_missing=summary["required_headers_missing"],
            extra_headers=summary["extra_headers"],
            total_rows=summary["total_rows"],
            empty_rows=summary["empty_rows"],
            encoding=summary["encoding"],
            warnings=summary["warnings"],
            errors=summary["errors"],
            stats={},
        )
        final_status = "validated" if not summary["errors"] else "failed"
        upload.status = final_status
        upload.error = "; ".join(summary["errors"]) if summary["errors"] else None
        upload.save(update_fields=["status", "error", "updated_at"])

    resp = {
        "uploadId": str(upload.id),
        "fileName": upload.file_name,
        "minioKey": upload.minio_key,
    }
    
    return JsonResponse(resp)


@csrf_exempt
@user_access_required  # Both admin and user can use presigned uploads
def presign_view(request: HttpRequest):
    """
    Generate a presigned URL for direct-to-MinIO upload.
    Requires authentication (admin or user).
    """
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    if Minio is None:
        return _json_error("DEPENDENCY_MISSING", "minio library is required", 500)

    try:
        data = json.loads(request.body or b"{}")
    except Exception:
        data = {}
    file_name = data.get("fileName")
    content_length = int(data.get("contentLength") or 0)
    if not file_name:
        return _json_error("BAD_REQUEST", "fileName required")
    if (content_length / (1024 * 1024)) > _size_limit_mb():
        return _json_error("BAD_REQUEST", "contentLength exceeds limit")

    client = _get_minio_client()
    bucket = _bucket_name()
    user_id = _current_user_id(request)
    key = _build_object_key(user_id, file_name)

    try:
        url = client.presigned_put_object(bucket, key, expires=900)
    except Exception as ex:
        return _json_error("PRESIGN_FAILED", f"Failed to presign: {ex}", 500)

    upload = Upload.objects.create(
        user_id=user_id, file_name=file_name, minio_key=key, status="pending"
    )
    expires_at = (dt.datetime.utcnow() + dt.timedelta(seconds=900)).isoformat() + "Z"

    return JsonResponse({"uploadId": str(upload.id), "url": url, "fields": {}, "minioKey": key, "expiresAt": expires_at})


@csrf_exempt
@user_access_required  # Both admin and user can complete uploads
def complete_view(request: HttpRequest):
    """
    Mark a presigned upload as complete and run validation.
    Requires authentication (admin or user).
    """
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    if Minio is None:
        return _json_error("DEPENDENCY_MISSING", "minio library is required", 500)

    try:
        data = json.loads(request.body or b"{}")
    except Exception:
        data = {}
    upload_id = data.get("uploadId")
    minio_key = data.get("minioKey")
    if not (upload_id and minio_key):
        return _json_error("BAD_REQUEST", "uploadId and minioKey required")

    try:
        upload = Upload.objects.get(id=upload_id, minio_key=minio_key)
    except Upload.DoesNotExist:
        return _json_error("NOT_FOUND", "Upload not found", 404)

    # Check if user owns this upload or is admin
    current_user = get_current_user(request)
    if str(upload.user_id) != str(current_user.id) and current_user.role != 'admin':
        return _json_error("FORBIDDEN", "Access denied", 403)

    client = _get_minio_client()
    bucket = _bucket_name()
    try:
        stat = client.stat_object(bucket, minio_key)
    except Exception as ex:
        return _json_error("BAD_REQUEST", f"Object not found in MinIO: {ex}")

    with transaction.atomic():
        upload.bytes = getattr(stat, "size", 0)
        upload.status = "uploaded"
        upload.save(update_fields=["bytes", "status", "updated_at"])

        summary = _validate_csv(bucket, minio_key)
        ValidationReport.objects.update_or_create(
            upload=upload,
            defaults=dict(
                required_headers_missing=summary["required_headers_missing"],
                extra_headers=summary["extra_headers"],
                total_rows=summary["total_rows"],
                empty_rows=summary["empty_rows"],
                encoding=summary["encoding"],
                warnings=summary["warnings"],
                errors=summary["errors"],
                stats={},
            ),
        )
        final_status = "validated" if not summary["errors"] else "failed"
        upload.status = final_status
        upload.error = "; ".join(summary["errors"]) if summary["errors"] else None
        upload.save(update_fields=["status", "error", "updated_at"])

    return JsonResponse({"ok": True})


def _serialize_upload(upload: Upload) -> dict:
    data = {
        "uploadId": str(upload.id),
        "fileName": upload.file_name,
        "minioKey": upload.minio_key,
        "status": upload.status,
        "bytes": upload.bytes,
        "validation": None,
    }
    vr = getattr(upload, "validation", None)
    if vr:
        data["validation"] = {
            "requiredHeadersMissing": vr.required_headers_missing,
            "extraHeaders": vr.extra_headers,
            "totalRows": vr.total_rows or 0,
            "emptyRows": vr.empty_rows or 0,
            "encoding": vr.encoding or "utf-8",
            "warnings": vr.warnings,
            "errors": vr.errors,
        }
    return data


@user_access_required  # Both admin and user can check status
def upload_status_view(request: HttpRequest, upload_id: str):
    """
    Return the status (and validation report if present) for a given upload.
    Requires authentication (admin or user).
    """
    if request.method != "GET":
        return HttpResponseNotAllowed(["GET"])
    try:
        upload = Upload.objects.select_related("validation").get(id=upload_id)
    except Upload.DoesNotExist:
        return _json_error("NOT_FOUND", "Upload not found", 404)
    
    # Check if user owns this upload or is admin
    current_user = get_current_user(request)
    if str(upload.user_id) != str(current_user.id) and current_user.role != 'admin':
        return _json_error("FORBIDDEN", "Access denied", 403)
        
    return JsonResponse(_serialize_upload(upload))