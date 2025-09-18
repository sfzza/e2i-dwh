# e2i_api/apps/common/auth.py

import uuid
import logging
from functools import wraps
from django.http import JsonResponse
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser

logger = logging.getLogger(__name__)

User = get_user_model()


class AuthenticationMiddleware:
    """
    Custom authentication middleware that supports multiple auth methods:
    1. API Key in X-API-Key header
    2. Session Token in X-Session-Token header  
    3. User ID in X-User-Id header (for backwards compatibility)
    """
    
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Try to authenticate user
        user = self.authenticate_request(request)
        request.user = user if user else AnonymousUser()
        
        # Add user info to request for easy access
        if hasattr(request.user, 'id'):
            request.user_id = request.user.id
            request.user_role = getattr(request.user, 'role', None)
        else:
            request.user_id = None
            request.user_role = None

        response = self.get_response(request)
        return response

    def authenticate_request(self, request):
        """Try multiple authentication methods"""
        
        # Method 1: API Key authentication
        api_key = request.headers.get('X-API-Key') or request.headers.get('X-Api-Key')
        if api_key:
            try:
                user = User.objects.get(api_key=api_key, is_active=True)
                logger.info(f"Authenticated user {user.username} via API key")
                return user
            except User.DoesNotExist:
                logger.warning(f"Invalid API key attempted: {api_key[:8]}...")

        # Method 2: Session Token authentication
        session_token = request.headers.get('X-Session-Token')
        if session_token:
            try:
                from .models import UserSession
                session = UserSession.objects.select_related('user').get(
                    session_token=session_token,
                    is_active=True
                )
                if not session.is_expired():
                    session.refresh()  # Update last accessed time
                    logger.info(f"Authenticated user {session.user.username} via session token")
                    return session.user
                else:
                    # Deactivate expired session
                    session.is_active = False
                    session.save()
                    logger.info(f"Session token expired for user {session.user.username}")
            except UserSession.DoesNotExist:
                logger.warning(f"Invalid session token attempted")

        # Method 3: Direct User ID (backwards compatibility - less secure)
        user_id_header = request.headers.get('X-User-Id') or request.META.get('HTTP_X_USER_ID')
        if user_id_header:
            try:
                user_uuid = uuid.UUID(user_id_header)
                user = User.objects.get(id=user_uuid, is_active=True)
                logger.info(f"Authenticated user {user.username} via User-ID header")
                return user
            except (ValueError, User.DoesNotExist):
                logger.warning(f"Invalid User-ID header: {user_id_header}")

        return None


def _json_error(code: str, message: str, status: int = 400):
    """Helper function for JSON error responses"""
    return JsonResponse({"code": code, "message": message}, status=status)


def require_auth(required_role=None):
    """
    Decorator to require authentication and optionally a specific role.
    
    Usage:
    @require_auth()  # Any authenticated user
    @require_auth('admin')  # Only admin users
    @require_auth('user')  # Only regular users (excludes admin)
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapped_view(request, *args, **kwargs):
            # Check if user is authenticated
            if not hasattr(request, 'user') or not request.user or not hasattr(request.user, 'id'):
                return _json_error("AUTHENTICATION_REQUIRED", "Authentication required", 401)

            if not request.user.is_active:
                return _json_error("ACCOUNT_DISABLED", "User account is disabled", 403)

            # Check role if required
            if required_role:
                user_role = getattr(request.user, 'role', None)
                if not user_role:
                    return _json_error("INVALID_USER", "User has no role assigned", 403)

                if required_role == 'admin' and user_role != 'admin':
                    return _json_error("ADMIN_REQUIRED", "Administrator access required", 403)
                elif required_role == 'user' and user_role not in ['user', 'admin']:
                    # Allow admin to access user endpoints
                    return _json_error("USER_ACCESS_REQUIRED", "User access required", 403)

            return view_func(request, *args, **kwargs)
        return wrapped_view
    return decorator


def admin_required(view_func):
    """Decorator that requires admin role"""
    return require_auth('admin')(view_func)


def user_access_required(view_func):
    """Decorator that requires user role (admin can also access)"""
    return require_auth('user')(view_func)


def get_current_user(request):
    """Helper function to get the current authenticated user"""
    if hasattr(request, 'user') and request.user and hasattr(request.user, 'id'):
        return request.user
    return None


def get_current_user_id(request):
    """Helper function to get the current user's UUID"""
    user = get_current_user(request)
    return user.id if user else None


def is_admin(request):
    """Check if current user is admin"""
    user = get_current_user(request)
    return user and getattr(user, 'role', None) == 'admin'


def is_user(request):
    """Check if current user is a regular user"""
    user = get_current_user(request)
    return user and getattr(user, 'role', None) in ['user', 'admin']


# Authentication views for login/logout/token generation
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth import authenticate
import json


@csrf_exempt
def login_view(request):
    """
    Authenticate user and return session token
    POST /auth/login
    Body: {"username": "user", "password": "pass"}
    """
    if request.method != 'POST':
        return _json_error("METHOD_NOT_ALLOWED", "Only POST allowed", 405)

    try:
        data = json.loads(request.body)
        username = data.get('username')
        password = data.get('password')

        if not username or not password:
            return _json_error("BAD_REQUEST", "Username and password required")

        # Try to get user and check password
        try:
            user = User.objects.get(username=username, is_active=True)
            if user.check_password(password):
                # Create session token
                from .models import UserSession
                import secrets
                from datetime import timedelta

                session_token = secrets.token_hex(32)
                session = UserSession.objects.create(
                    user=user,
                    session_token=session_token,
                    expires_at=timezone.now() + timedelta(days=7),
                    ip_address=request.META.get('REMOTE_ADDR'),
                    user_agent=request.META.get('HTTP_USER_AGENT', '')[:1000]
                )

                return JsonResponse({
                    "success": True,
                    "user": {
                        "id": str(user.id),
                        "username": user.username,
                        "role": user.role,
                        "email": user.email
                    },
                    "session_token": session_token,
                    "api_key": user.api_key,
                    "expires_at": session.expires_at.isoformat()
                })
            else:
                return _json_error("INVALID_CREDENTIALS", "Invalid username or password", 401)
        except User.DoesNotExist:
            return _json_error("INVALID_CREDENTIALS", "Invalid username or password", 401)

    except json.JSONDecodeError:
        return _json_error("BAD_REQUEST", "Invalid JSON body")
    except Exception as e:
        logger.error(f"Login error: {e}")
        return _json_error("INTERNAL_ERROR", "Login failed", 500)


@csrf_exempt
@require_auth()
def logout_view(request):
    """
    Logout user (deactivate session token)
    POST /auth/logout
    """
    if request.method != 'POST':
        return _json_error("METHOD_NOT_ALLOWED", "Only POST allowed", 405)

    session_token = request.headers.get('X-Session-Token')
    if session_token:
        try:
            from .models import UserSession
            session = UserSession.objects.get(session_token=session_token)
            session.is_active = False
            session.save()
        except UserSession.DoesNotExist:
            pass

    return JsonResponse({"success": True, "message": "Logged out successfully"})


@csrf_exempt
@require_auth()
def generate_api_key_view(request):
    """
    Generate new API key for user
    POST /auth/generate-api-key
    """
    if request.method != 'POST':
        return _json_error("METHOD_NOT_ALLOWED", "Only POST allowed", 405)

    user = get_current_user(request)
    if not user:
        return _json_error("AUTHENTICATION_REQUIRED", "Authentication required", 401)

    api_key = user.generate_api_key()
    return JsonResponse({
        "success": True,
        "api_key": api_key,
        "message": "New API key generated successfully"
    })


@require_auth()
def user_profile_view(request):
    """
    Get current user profile
    GET /auth/profile
    """
    if request.method != 'GET':
        return _json_error("METHOD_NOT_ALLOWED", "Only GET allowed", 405)

    user = get_current_user(request)
    return JsonResponse({
        "user": {
            "id": str(user.id),
            "username": user.username,
            "email": user.email,
            "role": user.role,
            "created_at": user.created_at.isoformat(),
            "has_api_key": bool(user.api_key)
        }
    })