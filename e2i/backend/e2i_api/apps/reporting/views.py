# views.py
from __future__ import annotations

import os
import csv
import json
from time import perf_counter
from datetime import timedelta
from pathlib import Path

from django.conf import settings
from django.core import signing
from django.utils import timezone
from django.http import (
    JsonResponse,
    HttpResponse,
    HttpResponseBadRequest,
    HttpResponseNotFound,
)
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from .models import AuditLog, ExportJob

# --- NEW: real query imports ---
from clickhouse_driver import Client as CHClient
from .query_builder import build_select, QueryBuildError


# ---------- helpers ----------
def _username(request):
    if hasattr(request, "user") and getattr(request.user, "is_authenticated", False):
        return request.user.username
    return None


def _roles_from_headers(request):
    raw = request.headers.get("X-Roles") or request.META.get("HTTP_X_ROLES") or ""
    return [r.strip() for r in raw.split(",") if r.strip()]


def _make_download_token(job_id: str) -> str:
    return signing.dumps({"job_id": str(job_id)}, salt="export-download", compress=True)


def _verify_download_token(token: str, max_age_seconds: int) -> str | None:
    data = signing.loads(token, salt="export-download", max_age=max_age_seconds)
    return data.get("job_id")


def log_query_audit(
    request, *, dataset, columns, filters, order_by, limit, offset, row_count, duration_ms
):
    AuditLog.objects.create(
        event_type="QUERY",
        username=_username(request),
        roles=_roles_from_headers(request),
        dataset=dataset,
        columns=columns or [],
        filters=filters or [],
        order_by=order_by or [],
        limit=limit,
        offset=offset,
        row_count=row_count,
        duration_ms=duration_ms,
        ip=request.META.get("REMOTE_ADDR"),
        user_agent=request.META.get("HTTP_USER_AGENT"),
    )


def log_export_audit(request, *, job: ExportJob):
    AuditLog.objects.create(
        event_type="EXPORT",
        username=job.created_by,
        roles=job.roles,
        dataset=job.dataset,
        columns=job.columns or [],
        filters=job.filters or [],
        order_by=job.order_by or [],
        row_count=job.row_count,
        ip=request.META.get("REMOTE_ADDR"),
        user_agent=request.META.get("HTTP_USER_AGENT"),
    )


# ---------- health ----------
@require_http_methods(["GET"])
def ping(request):
    return HttpResponse("reporting ok")


# ---------- metadata ----------
@require_http_methods(["GET"])
def datasets(request):
    return JsonResponse(["transactions", "customers"], safe=False)


@require_http_methods(["GET"])
def dataset_schema(request, dataset: str):
    columns = [
        {"name": "id", "type": "UInt64", "pii": False},
        {"name": "email", "type": "String", "pii": True},
        {"name": "created_at", "type": "DateTime", "pii": False},
    ]
    return JsonResponse({"dataset": dataset, "columns": columns})


@require_http_methods(["GET"])
def dataset_sample(request, dataset: str):
    columns = ["id", "email", "created_at"]
    rows = [
        [1, "token:email:abc123", "2024-01-01 00:00:00"],
        [2, "token:email:def456", "2024-01-02 00:00:00"],
    ]
    return JsonResponse({"dataset": dataset, "columns": columns, "rows": rows})


# ---------- query (REAL role-aware ClickHouse) ----------
@csrf_exempt
@require_http_methods(["POST"])
def query_run(request):
    t0 = perf_counter()
    try:
        payload = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return HttpResponseBadRequest("Invalid JSON body")

    dataset = payload.get("dataset")
    columns = payload.get("columns") or []
    filters = payload.get("filters") or []
    order_by = payload.get("order_by") or []
    limit = payload.get("limit")
    offset = payload.get("offset") or 0
    roles = [
        r.strip()
        for r in (request.headers.get("X-Roles") or request.META.get("HTTP_X_ROLES") or "").split(",")
        if r.strip()
    ]

    try:
        # Enforces dataset+allowlist and returns safe SQL + params
        sql, params, selected_cols = build_select(
            dataset, columns, filters, order_by, limit, offset, roles
        )

        ch = CHClient(
            host=settings.CLICKHOUSE["HOST"],
            port=settings.CLICKHOUSE["PORT"],
            user=settings.CLICKHOUSE["USER"],
            password=settings.CLICKHOUSE["PASSWORD"],
            database=settings.CLICKHOUSE["DATABASE"],
            settings={"max_execution_time": settings.CLICKHOUSE["QUERY_TIMEOUT"]},
        )
        rows = ch.execute(sql, params)
        result = {"columns": selected_cols, "rows": rows, "row_count": len(rows)}
    except QueryBuildError as e:
        return HttpResponseBadRequest(str(e))
    except Exception as e:
        return HttpResponseBadRequest(f"Query failed: {e}")

    duration_ms = int((perf_counter() - t0) * 1000)
    log_query_audit(
        request,
        dataset=dataset,
        columns=selected_cols,
        filters=filters,
        order_by=order_by,
        limit=limit,
        offset=offset,
        row_count=result["row_count"],
        duration_ms=duration_ms,
    )
    return JsonResponse(result)


@csrf_exempt
@require_http_methods(["POST"])
def query_explain(request):
    return JsonResponse({"plan": {"strategy": "INDEX_SCAN", "estimated_rows": 1234}})


@require_http_methods(["GET"])
def query_limits(request):
    roles_hdr = request.headers.get("X-Roles") or request.META.get("HTTP_X_ROLES") or ""
    roles = {r.strip().lower() for r in roles_hdr.split(",") if r.strip()}
    caps = {"max_rows": 2000, "max_columns": 50, "timeout_ms": 20000}
    if "admin" in roles or "analyst" in roles:
        caps = {"max_rows": 10000, "max_columns": 100, "timeout_ms": 30000}
    return JsonResponse(caps)


# ---------- reports (detokenized export) ----------
@csrf_exempt
@require_http_methods(["POST"])
def reports_detokenize(request):
    try:
        payload = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return HttpResponseBadRequest("Invalid JSON body")

    dataset = payload.get("dataset", "transactions")
    columns = payload.get("columns") or ["id", "email", "created_at"]
    filters = payload.get("filters") or []
    order_by = payload.get("order_by") or []
    file_fmt = (payload.get("format") or "CSV").upper()

    job = ExportJob.objects.create(
        created_by=_username(request),
        roles=_roles_from_headers(request),
        dataset=dataset,
        columns=columns,
        filters=filters,
        order_by=order_by,
        file_format=file_fmt,
        status="RUNNING",
    )

    export_dir = Path(settings.REPORTING["EXPORT_DIR"])
    export_dir.mkdir(parents=True, exist_ok=True)
    out_file = export_dir / f"{job.id}.csv"

    with open(out_file, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(columns)
        w.writerow([1, "john@example.com", "2024-01-01 00:00:00"])
        w.writerow([2, "mary@example.com", "2024-01-02 00:00:00"])
    row_count = 2

    job.file_path = str(out_file)
    job.row_count = row_count
    job.status = "DONE"

    token = _make_download_token(job.id)
    job.signed_token = token
    job.signed_expires_at = timezone.now() + timedelta(
        seconds=settings.REPORTING["EXPORT_TTL_SECONDS"]
    )
    job.save(
        update_fields=["file_path", "row_count", "status", "signed_token", "signed_expires_at"]
    )

    log_export_audit(request, job=job)
    return JsonResponse(
        {"id": str(job.id), "status": job.status, "rows": job.row_count, "token": token},
        status=201,
    )


@require_http_methods(["GET", "DELETE"])
def reports_status_or_delete(request, rid):
    job = get_object_or_404(ExportJob, id=rid)
    if request.method == "GET":
        return JsonResponse(
            {
                "id": str(job.id),
                "status": job.status,
                "rows": job.row_count,
                "dataset": job.dataset,
                "created_at": job.created_at.isoformat(),
            }
        )
    try:
        if job.file_path and os.path.exists(job.file_path):
            os.remove(job.file_path)
    except Exception:
        pass
    job.delete()
    return JsonResponse({"id": str(rid), "deleted": True})


@require_http_methods(["GET"])
def reports_download(request, rid):
    job = get_object_or_404(ExportJob, id=rid, status="DONE")

    token = request.GET.get("token")
    if not token:
        return HttpResponseBadRequest("Missing token")
    try:
        job_id_from_token = _verify_download_token(
            token, settings.REPORTING["EXPORT_TTL_SECONDS"]
        )
        if str(job.id) != str(job_id_from_token):
            return HttpResponseBadRequest("Token does not match job")
    except Exception:
        return HttpResponseBadRequest("Invalid or expired token")

    if not job.file_path or not os.path.exists(job.file_path):
        return HttpResponseNotFound("File not found")

    with open(job.file_path, "rb") as f:
        data = f.read()
    resp = HttpResponse(data, content_type="text/csv")
    resp["Content-Disposition"] = f'attachment; filename="{rid}.csv"'
    return resp
