# e2i_api/apps/common/audit_views.py - Audit logs API endpoints

import json
import logging
from django.http import JsonResponse, HttpRequest
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Q
from django.utils import timezone
from datetime import datetime, timedelta

from .models import AuditLog
from .auth import admin_required, _json_error, get_current_user

logger = logging.getLogger(__name__)


@admin_required
def audit_logs_list_view(request: HttpRequest):
    """
    GET /audit-logs/ - List audit logs (Admin only)
    Query parameters:
    - page: Page number (default: 1)
    - limit: Items per page (default: 50)
    - date_from: Start date (ISO format)
    - date_to: End date (ISO format)
    - action: Filter by action
    - user: Filter by username
    - status: Filter by status
    """
    if request.method != 'GET':
        return _json_error("METHOD_NOT_ALLOWED", "Only GET allowed", 405)

    try:
        # Get query parameters
        page = int(request.GET.get('page', 1))
        limit = min(int(request.GET.get('limit', 50)), 100)  # Max 100 per page
        date_from = request.GET.get('date_from')
        date_to = request.GET.get('date_to')
        action_filter = request.GET.get('action')
        user_filter = request.GET.get('user')
        status_filter = request.GET.get('status')

        # Build query
        query = AuditLog.objects.all()

        # Apply filters
        if date_from:
            try:
                date_from_dt = datetime.fromisoformat(date_from.replace('Z', '+00:00'))
                query = query.filter(timestamp__gte=date_from_dt)
            except ValueError:
                return _json_error("BAD_REQUEST", "Invalid date_from format. Use ISO format.", 400)

        if date_to:
            try:
                date_to_dt = datetime.fromisoformat(date_to.replace('Z', '+00:00'))
                query = query.filter(timestamp__lte=date_to_dt)
            except ValueError:
                return _json_error("BAD_REQUEST", "Invalid date_to format. Use ISO format.", 400)

        if action_filter:
            query = query.filter(action=action_filter)

        if user_filter:
            query = query.filter(Q(username__icontains=user_filter) | Q(user__username__icontains=user_filter))

        if status_filter:
            query = query.filter(status=status_filter)

        # Order by timestamp (newest first)
        query = query.order_by('-timestamp')

        # Apply pagination
        offset = (page - 1) * limit
        logs = query[offset:offset + limit]

        # Serialize logs
        logs_data = []
        for log in logs:
            logs_data.append({
                'id': str(log.id),
                'username': log.username or 'System',
                'action': log.action,
                'resource': log.resource,
                'resource_id': log.resource_id,
                'details': log.details,
                'status': log.status,
                'ip_address': log.ip_address,
                'user_agent': log.user_agent,
                'timestamp': log.timestamp.isoformat(),
                'created_at': log.created_at.isoformat()
            })

        # Get total count for pagination
        total_count = query.count()

        return JsonResponse({
            'success': True,
            'logs': logs_data,
            'pagination': {
                'page': page,
                'limit': limit,
                'total': total_count,
                'pages': (total_count + limit - 1) // limit
            }
        })

    except Exception as e:
        logger.error(f"Error fetching audit logs: {e}")
        return _json_error("INTERNAL_SERVER_ERROR", f"Failed to fetch audit logs: {e}", 500)


@csrf_exempt
@admin_required
def audit_logs_create_view(request: HttpRequest):
    """
    POST /audit-logs/ - Create audit log entry (Admin only)
    Body: {
        "username": "user123",
        "action": "login",
        "resource": "dashboard",
        "resource_id": "uuid",
        "details": {"key": "value"},
        "status": "success",
        "ip_address": "192.168.1.1",
        "user_agent": "Mozilla/5.0..."
    }
    """
    if request.method != 'POST':
        return _json_error("METHOD_NOT_ALLOWED", "Only POST allowed", 405)

    try:
        data = json.loads(request.body)
        
        # Validate required fields
        if not data.get('action'):
            return _json_error("BAD_REQUEST", "Action is required")

        # Create audit log entry
        log = AuditLog.log_action(
            username=data.get('username'),
            action=data.get('action'),
            resource=data.get('resource'),
            resource_id=data.get('resource_id'),
            details=data.get('details', {}),
            status=data.get('status', 'success'),
            ip_address=data.get('ip_address'),
            user_agent=data.get('user_agent')
        )

        return JsonResponse({
            'success': True,
            'message': 'Audit log created successfully',
            'log_id': str(log.id)
        }, status=201)

    except json.JSONDecodeError:
        return _json_error("BAD_REQUEST", "Invalid JSON body")
    except Exception as e:
        logger.error(f"Error creating audit log: {e}")
        return _json_error("INTERNAL_SERVER_ERROR", f"Failed to create audit log: {e}", 500)


@admin_required
def audit_logs_stats_view(request: HttpRequest):
    """
    GET /audit-logs/stats/ - Get audit logs statistics (Admin only)
    """
    if request.method != 'GET':
        return _json_error("METHOD_NOT_ALLOWED", "Only GET allowed", 405)

    try:
        # Get date range (default to last 30 days)
        days = int(request.GET.get('days', 30))
        start_date = timezone.now() - timedelta(days=days)

        # Get statistics
        total_logs = AuditLog.objects.filter(timestamp__gte=start_date).count()
        
        # Action breakdown
        action_stats = {}
        for action, _ in AuditLog.ACTION_CHOICES:
            count = AuditLog.objects.filter(
                timestamp__gte=start_date,
                action=action
            ).count()
            if count > 0:
                action_stats[action] = count

        # Status breakdown
        status_stats = {}
        for status, _ in AuditLog.STATUS_CHOICES:
            count = AuditLog.objects.filter(
                timestamp__gte=start_date,
                status=status
            ).count()
            if count > 0:
                status_stats[status] = count

        # Top users
        from django.db.models import Count
        top_users = AuditLog.objects.filter(
            timestamp__gte=start_date
        ).values('username').annotate(
            count=Count('id')
        ).order_by('-count')[:10]

        return JsonResponse({
            'success': True,
            'stats': {
                'total_logs': total_logs,
                'date_range': {
                    'start': start_date.isoformat(),
                    'end': timezone.now().isoformat(),
                    'days': days
                },
                'action_breakdown': action_stats,
                'status_breakdown': status_stats,
                'top_users': list(top_users)
            }
        })

    except Exception as e:
        logger.error(f"Error fetching audit logs stats: {e}")
        return _json_error("INTERNAL_SERVER_ERROR", f"Failed to fetch audit logs stats: {e}", 500)


