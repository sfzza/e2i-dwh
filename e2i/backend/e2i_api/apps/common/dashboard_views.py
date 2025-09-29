# e2i_api/apps/common/dashboard_views.py - Dashboard metrics API endpoints

import json
import logging
from django.http import JsonResponse, HttpRequest
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Count, Q
from django.utils import timezone
from datetime import datetime, timedelta

from .models import AuditLog, User
from .auth import user_access_required, _json_error, get_current_user

# Import ingestion models for file processing metrics
try:
    from e2i_api.apps.ingestion.models import Upload, ValidationReport
except ImportError:
    Upload = None
    ValidationReport = None

logger = logging.getLogger(__name__)


@user_access_required
def dashboard_metrics_view(request: HttpRequest):
    """
    GET /dashboard/metrics/ - Get dashboard metrics (Authenticated users)
    """
    if request.method != 'GET':
        return _json_error("METHOD_NOT_ALLOWED", "Only GET allowed", 405)

    try:
        current_user = get_current_user(request)
        if not current_user:
            return _json_error("AUTHENTICATION_REQUIRED", "Authentication required", 401)

        # Get date ranges
        now = timezone.now()
        this_month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        last_month_start = (this_month_start - timedelta(days=1)).replace(day=1)
        last_month_end = this_month_start - timedelta(seconds=1)
        this_week_start = now - timedelta(days=now.weekday())
        this_week_start = this_week_start.replace(hour=0, minute=0, second=0, microsecond=0)

        # Initialize metrics
        metrics = {
            'files_processed_month': 0,
            'files_processed_last_month': 0,
            'files_processed_change': 0,
            'pipelines_running': 0,
            'system_alerts': 0,
            'reports_generated': 0,
            'reports_generated_week': 0,
            'total_users': 0,
            'active_users_today': 0,
            'recent_uploads': [],
            'system_status': 'operational'
        }

        # Files Processed (Month) - from Upload model
        if Upload:
            # Current month uploads
            current_month_uploads = Upload.objects.filter(
                created_at__gte=this_month_start
            )
            
            # Filter by user if not admin
            if current_user.role != 'admin':
                current_month_uploads = current_month_uploads.filter(user_id=current_user.id)
            
            metrics['files_processed_month'] = current_month_uploads.count()

            # Last month uploads for comparison
            last_month_uploads = Upload.objects.filter(
                created_at__gte=last_month_start,
                created_at__lte=last_month_end
            )
            
            if current_user.role != 'admin':
                last_month_uploads = last_month_uploads.filter(user_id=current_user.id)
            
            metrics['files_processed_last_month'] = last_month_uploads.count()

            # Calculate percentage change
            if metrics['files_processed_last_month'] > 0:
                change = ((metrics['files_processed_month'] - metrics['files_processed_last_month']) / 
                         metrics['files_processed_last_month']) * 100
                metrics['files_processed_change'] = round(change, 1)

            # Pipelines Running - count uploads in processing states
            processing_states = ['pending', 'uploaded', 'mapped', 'transformed']
            running_pipelines = Upload.objects.filter(status__in=processing_states)
            
            if current_user.role != 'admin':
                running_pipelines = running_pipelines.filter(user_id=current_user.id)
            
            metrics['pipelines_running'] = running_pipelines.count()

            # Recent uploads for dashboard
            recent_uploads_query = Upload.objects.select_related('validation').order_by('-created_at')
            
            if current_user.role != 'admin':
                recent_uploads_query = recent_uploads_query.filter(user_id=current_user.id)
            
            # Apply slice after filtering
            recent_uploads = recent_uploads_query[:5]
            
            metrics['recent_uploads'] = [
                {
                    'id': str(upload.id),
                    'file_name': upload.file_name,
                    'status': upload.status,
                    'created_at': upload.created_at.isoformat(),
                    'record_count': upload.validation.total_rows if upload.validation else None
                }
                for upload in recent_uploads
            ]

        # System Alerts - count failed uploads and system errors
        if Upload:
            failed_uploads = Upload.objects.filter(status='failed')
            if current_user.role != 'admin':
                failed_uploads = failed_uploads.filter(user_id=current_user.id)
            metrics['system_alerts'] = failed_uploads.count()

        # Reports Generated - count completed uploads
        if Upload:
            completed_uploads = Upload.objects.filter(status='completed')
            if current_user.role != 'admin':
                completed_uploads = completed_uploads.filter(user_id=current_user.id)
            metrics['reports_generated'] = completed_uploads.count()

            # Reports generated this week
            week_reports = completed_uploads.filter(created_at__gte=this_week_start)
            metrics['reports_generated_week'] = week_reports.count()

        # User metrics (admin only)
        if current_user.role == 'admin':
            metrics['total_users'] = User.objects.filter(is_active=True).count()
            
            # Active users today (users with audit logs today)
            today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            active_users = AuditLog.objects.filter(
                timestamp__gte=today_start
            ).values('username').distinct().count()
            metrics['active_users_today'] = active_users

        # System status
        if metrics['system_alerts'] > 0:
            metrics['system_status'] = 'warning'
        elif metrics['pipelines_running'] > 5:
            metrics['system_status'] = 'busy'
        else:
            metrics['system_status'] = 'operational'

        return JsonResponse({
            'success': True,
            'metrics': metrics,
            'user_role': current_user.role,
            'generated_at': now.isoformat()
        })

    except Exception as e:
        logger.error(f"Error fetching dashboard metrics: {e}")
        return _json_error("INTERNAL_SERVER_ERROR", f"Failed to fetch dashboard metrics: {e}", 500)


@user_access_required
def dashboard_activity_view(request: HttpRequest):
    """
    GET /dashboard/activity/ - Get recent activity for dashboard (Authenticated users)
    """
    if request.method != 'GET':
        return _json_error("METHOD_NOT_ALLOWED", "Only GET allowed", 405)

    try:
        current_user = get_current_user(request)
        if not current_user:
            return _json_error("AUTHENTICATION_REQUIRED", "Authentication required", 401)

        # Get recent audit logs
        recent_activity_query = AuditLog.objects.all().order_by('-timestamp')
        
        # Filter by user if not admin
        if current_user.role != 'admin':
            recent_activity_query = recent_activity_query.filter(
                Q(user=current_user) | Q(username=current_user.username)
            )
        
        # Apply slice after filtering
        recent_activity = recent_activity_query[:10]

        activity_data = []
        for log in recent_activity:
            activity_data.append({
                'id': str(log.id),
                'username': log.username or 'System',
                'action': log.action,
                'resource': log.resource,
                'status': log.status,
                'timestamp': log.timestamp.isoformat(),
                'ip_address': log.ip_address
            })

        return JsonResponse({
            'success': True,
            'activity': activity_data,
            'total_count': len(activity_data)
        })

    except Exception as e:
        logger.error(f"Error fetching dashboard activity: {e}")
        return _json_error("INTERNAL_SERVER_ERROR", f"Failed to fetch dashboard activity: {e}", 500)


@user_access_required
def user_dashboard_summary_view(request: HttpRequest):
    """
    GET /dashboard/user-summary/ - Get user-specific dashboard summary (Authenticated users)
    """
    if request.method != 'GET':
        return _json_error("METHOD_NOT_ALLOWED", "Only GET allowed", 405)

    try:
        current_user = get_current_user(request)
        if not current_user:
            return _json_error("AUTHENTICATION_REQUIRED", "Authentication required", 401)

        # Get date ranges
        now = timezone.now()
        this_month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        this_week_start = now - timedelta(days=now.weekday())
        this_week_start = this_week_start.replace(hour=0, minute=0, second=0, microsecond=0)
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

        # Initialize user summary
        user_summary = {
            'user_info': {
                'username': current_user.username,
                'email': current_user.email,
                'role': current_user.role,
                'is_active': current_user.is_active,
                'last_login': current_user.last_login.isoformat() if current_user.last_login else None,
                'date_joined': current_user.created_at.isoformat()
            },
            'today_stats': {
                'uploads_today': 0,
                'successful_today': 0,
                'failed_today': 0
            },
            'week_stats': {
                'uploads_this_week': 0,
                'successful_this_week': 0,
                'failed_this_week': 0
            },
            'month_stats': {
                'uploads_this_month': 0,
                'successful_this_month': 0,
                'failed_this_month': 0
            },
            'recent_activity_count': 0,
            'system_status': 'operational'
        }

        # Get user-specific upload statistics
        if Upload:
            # Today's uploads
            today_uploads = Upload.objects.filter(
                user_id=current_user.id,
                created_at__gte=today_start
            )
            user_summary['today_stats']['uploads_today'] = today_uploads.count()
            user_summary['today_stats']['successful_today'] = today_uploads.filter(status='completed').count()
            user_summary['today_stats']['failed_today'] = today_uploads.filter(status='failed').count()

            # This week's uploads
            week_uploads = Upload.objects.filter(
                user_id=current_user.id,
                created_at__gte=this_week_start
            )
            user_summary['week_stats']['uploads_this_week'] = week_uploads.count()
            user_summary['week_stats']['successful_this_week'] = week_uploads.filter(status='completed').count()
            user_summary['week_stats']['failed_this_week'] = week_uploads.filter(status='failed').count()

            # This month's uploads
            month_uploads = Upload.objects.filter(
                user_id=current_user.id,
                created_at__gte=this_month_start
            )
            user_summary['month_stats']['uploads_this_month'] = month_uploads.count()
            user_summary['month_stats']['successful_this_month'] = month_uploads.filter(status='completed').count()
            user_summary['month_stats']['failed_this_month'] = month_uploads.filter(status='failed').count()

        # Recent activity count (last 7 days)
        week_ago = now - timedelta(days=7)
        recent_activity = AuditLog.objects.filter(
            Q(user=current_user) | Q(username=current_user.username),
            timestamp__gte=week_ago
        )
        user_summary['recent_activity_count'] = recent_activity.count()

        # System status based on user's recent failures
        if user_summary['today_stats']['failed_today'] > 0:
            user_summary['system_status'] = 'warning'
        elif user_summary['week_stats']['failed_this_week'] > 2:
            user_summary['system_status'] = 'attention'
        else:
            user_summary['system_status'] = 'operational'

        return JsonResponse({
            'success': True,
            'user_summary': user_summary,
            'generated_at': now.isoformat()
        })

    except Exception as e:
        logger.error(f"Error fetching user dashboard summary: {e}")
        return _json_error("INTERNAL_SERVER_ERROR", f"Failed to fetch user dashboard summary: {e}", 500)


@user_access_required
def user_upload_history_view(request: HttpRequest):
    """
    GET /dashboard/user-uploads/ - Get user's upload history for dashboard (Authenticated users)
    """
    if request.method != 'GET':
        return _json_error("METHOD_NOT_ALLOWED", "Only GET allowed", 405)

    try:
        current_user = get_current_user(request)
        if not current_user:
            return _json_error("AUTHENTICATION_REQUIRED", "Authentication required", 401)

        # Get query parameters
        limit = int(request.GET.get('limit', 10))
        status_filter = request.GET.get('status', None)
        
        # Build query
        uploads_query = Upload.objects.filter(user_id=current_user.id)
        
        if status_filter:
            uploads_query = uploads_query.filter(status=status_filter)
        
        # Get recent uploads
        recent_uploads = uploads_query.select_related('validation').order_by('-created_at')[:limit]
        
        uploads_data = []
        for upload in recent_uploads:
            uploads_data.append({
                'id': str(upload.id),
                'file_name': upload.file_name,
                'status': upload.status,
                'created_at': upload.created_at.isoformat(),
                'updated_at': upload.updated_at.isoformat() if upload.updated_at else None,
                'record_count': upload.validation.total_rows if upload.validation else None,
                'file_size': upload.file_size,
                'data_type': upload.data_type,
                'template_used': upload.template.name if upload.template else None
            })

        return JsonResponse({
            'success': True,
            'uploads': uploads_data,
            'total_count': len(uploads_data),
            'user_id': str(current_user.id)
        })

    except Exception as e:
        logger.error(f"Error fetching user upload history: {e}")
        return _json_error("INTERNAL_SERVER_ERROR", f"Failed to fetch user upload history: {e}", 500)


@user_access_required
def user_activity_timeline_view(request: HttpRequest):
    """
    GET /dashboard/user-activity/ - Get user's activity timeline for dashboard (Authenticated users)
    """
    if request.method != 'GET':
        return _json_error("METHOD_NOT_ALLOWED", "Only GET allowed", 405)

    try:
        current_user = get_current_user(request)
        if not current_user:
            return _json_error("AUTHENTICATION_REQUIRED", "Authentication required", 401)

        # Get query parameters
        limit = int(request.GET.get('limit', 20))
        days_back = int(request.GET.get('days', 7))
        
        # Calculate date range
        end_date = timezone.now()
        start_date = end_date - timedelta(days=days_back)
        
        # Get user's activity
        user_activity = AuditLog.objects.filter(
            Q(user=current_user) | Q(username=current_user.username),
            timestamp__gte=start_date,
            timestamp__lte=end_date
        ).order_by('-timestamp')[:limit]
        
        activity_data = []
        for log in user_activity:
            activity_data.append({
                'id': str(log.id),
                'action': log.action,
                'resource': log.resource,
                'status': log.status,
                'timestamp': log.timestamp.isoformat(),
                'ip_address': log.ip_address,
                'user_agent': log.user_agent,
                'details': log.details
            })

        return JsonResponse({
            'success': True,
            'activity': activity_data,
            'total_count': len(activity_data),
            'date_range': {
                'start': start_date.isoformat(),
                'end': end_date.isoformat()
            }
        })

    except Exception as e:
        logger.error(f"Error fetching user activity timeline: {e}")
        return _json_error("INTERNAL_SERVER_ERROR", f"Failed to fetch user activity timeline: {e}", 500)


