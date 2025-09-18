# e2i_api/apps/common/middleware.py

import time
import hashlib
import logging
from collections import defaultdict
from datetime import datetime, timedelta
from django.http import JsonResponse
from django.core.cache import cache
from django.conf import settings
from django.utils import timezone
from django.contrib.auth import get_user_model

logger = logging.getLogger(__name__)
User = get_user_model()


class RateLimitMiddleware:
    """
    Rate limiting middleware that tracks requests per user/IP.
    Supports different limits for different user roles.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        
        # Default rate limits (requests per hour)
        self.rate_limits = {
            'admin': getattr(settings, 'RATE_LIMIT_ADMIN_PER_HOUR', 2000),
            'user': getattr(settings, 'RATE_LIMIT_USER_PER_HOUR', 1000),
            'anonymous': getattr(settings, 'RATE_LIMIT_ANONYMOUS_PER_HOUR', 100),
        }
        
        # Stricter limits for auth endpoints
        self.auth_rate_limits = {
            'login': 10,      # 10 login attempts per hour
            'api_key': 5,     # 5 API key generations per hour
        }

    def __call__(self, request):
        # Check rate limits before processing request
        if not self.is_rate_limited(request):
            response = self.get_response(request)
            
            # Add rate limit headers to response
            self.add_rate_limit_headers(request, response)
            return response
        else:
            return JsonResponse({
                'code': 'RATE_LIMIT_EXCEEDED',
                'message': 'Rate limit exceeded. Please try again later.',
                'retry_after': 3600  # 1 hour
            }, status=429)

    def is_rate_limited(self, request):
        """Check if the request should be rate limited."""
        
        # Get identifier for rate limiting
        identifier = self.get_rate_limit_identifier(request)
        user_role = getattr(request, 'user_role', None) or 'anonymous'
        
        # Special handling for auth endpoints
        if self.is_auth_endpoint(request):
            return self.check_auth_rate_limit(request, identifier)
        
        # General rate limiting
        limit = self.rate_limits.get(user_role, self.rate_limits['anonymous'])
        return self.check_rate_limit(identifier, limit)

    def get_rate_limit_identifier(self, request):
        """Get unique identifier for rate limiting."""
        
        # Use user ID if authenticated
        if hasattr(request, 'user') and request.user and hasattr(request.user, 'id'):
            return f"user:{request.user.id}"
        
        # Fall back to IP address
        ip = self.get_client_ip(request)
        return f"ip:{ip}"

    def get_client_ip(self, request):
        """Extract client IP address from request."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR', 'unknown')
        return ip

    def is_auth_endpoint(self, request):
        """Check if this is an authentication endpoint."""
        auth_paths = [
            '/auth/login',
            '/auth/generate-api-key',
            '/auth/logout'
        ]
        return any(request.path.startswith(path) for path in auth_paths)

    def check_auth_rate_limit(self, request, identifier):
        """Apply stricter rate limits to auth endpoints."""
        
        if '/auth/login' in request.path:
            limit = self.auth_rate_limits['login']
            cache_key = f"auth_login:{identifier}"
        elif '/auth/generate-api-key' in request.path:
            limit = self.auth_rate_limits['api_key']
            cache_key = f"auth_api_key:{identifier}"
        else:
            return False  # No special limit for other auth endpoints
        
        return self.check_rate_limit(cache_key, limit)

    def check_rate_limit(self, identifier, limit):
        """Check if identifier has exceeded the rate limit."""
        
        cache_key = f"rate_limit:{identifier}"
        current_time = int(time.time())
        window_start = current_time - 3600  # 1 hour window
        
        # Get current request count
        requests = cache.get(cache_key, [])
        
        # Filter out old requests (outside the window)
        requests = [req_time for req_time in requests if req_time > window_start]
        
        # Check if limit exceeded
        if len(requests) >= limit:
            logger.warning(f"Rate limit exceeded for {identifier}: {len(requests)}/{limit} requests")
            return True
        
        # Add current request and update cache
        requests.append(current_time)
        cache.set(cache_key, requests, 3600)  # Cache for 1 hour
        
        return False

    def add_rate_limit_headers(self, request, response):
        """Add rate limit information to response headers."""
        
        identifier = self.get_rate_limit_identifier(request)
        user_role = getattr(request, 'user_role', None) or 'anonymous'
        limit = self.rate_limits.get(user_role, self.rate_limits['anonymous'])
        
        cache_key = f"rate_limit:{identifier}"
        current_time = int(time.time())
        window_start = current_time - 3600
        
        requests = cache.get(cache_key, [])
        requests = [req_time for req_time in requests if req_time > window_start]
        
        remaining = max(0, limit - len(requests))
        reset_time = window_start + 3600
        
        response['X-RateLimit-Limit'] = str(limit)
        response['X-RateLimit-Remaining'] = str(remaining)
        response['X-RateLimit-Reset'] = str(reset_time)


class SecurityHeadersMiddleware:
    """
    Middleware to add security headers to all responses.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        
        # Add security headers
        response['X-Content-Type-Options'] = 'nosniff'
        response['X-Frame-Options'] = 'DENY'
        response['X-XSS-Protection'] = '1; mode=block'
        response['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        
        # Add CSP header for admin pages
        if request.path.startswith('/admin/'):
            response['Content-Security-Policy'] = (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline'; "
                "style-src 'self' 'unsafe-inline'; "
                "img-src 'self' data:; "
                "font-src 'self'"
            )
        
        return response


class FailedLoginTrackingMiddleware:
    """
    Middleware to track and temporarily block IPs with too many failed login attempts.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        self.max_attempts = getattr(settings, 'MAX_LOGIN_ATTEMPTS', 5)
        self.lockout_duration = getattr(settings, 'LOGIN_LOCKOUT_DURATION', 900)  # 15 minutes

    def __call__(self, request):
        # Check if IP is locked out for login attempts
        if self.is_login_attempt(request) and self.is_ip_locked_out(request):
            return JsonResponse({
                'code': 'IP_LOCKED_OUT',
                'message': 'Too many failed login attempts. Please try again later.',
                'retry_after': self.lockout_duration
            }, status=429)
        
        response = self.get_response(request)
        
        # Track failed login attempts
        if self.is_login_attempt(request) and response.status_code == 401:
            self.record_failed_login(request)
        
        # Clear failed attempts on successful login
        if self.is_login_attempt(request) and response.status_code == 200:
            self.clear_failed_attempts(request)
        
        return response

    def is_login_attempt(self, request):
        """Check if this is a login attempt."""
        return request.path == '/auth/login' and request.method == 'POST'

    def is_ip_locked_out(self, request):
        """Check if IP is currently locked out."""
        ip = self.get_client_ip(request)
        cache_key = f"failed_logins:{ip}"
        
        failed_attempts = cache.get(cache_key, [])
        current_time = time.time()
        
        # Remove old attempts
        failed_attempts = [
            attempt_time for attempt_time in failed_attempts 
            if current_time - attempt_time < self.lockout_duration
        ]
        
        return len(failed_attempts) >= self.max_attempts

    def record_failed_login(self, request):
        """Record a failed login attempt."""
        ip = self.get_client_ip(request)
        cache_key = f"failed_logins:{ip}"
        
        failed_attempts = cache.get(cache_key, [])
        failed_attempts.append(time.time())
        
        cache.set(cache_key, failed_attempts, self.lockout_duration)
        
        logger.warning(f"Failed login attempt from IP {ip}. Total attempts: {len(failed_attempts)}")

    def clear_failed_attempts(self, request):
        """Clear failed login attempts for IP on successful login."""
        ip = self.get_client_ip(request)
        cache_key = f"failed_logins:{ip}"
        cache.delete(cache_key)

    def get_client_ip(self, request):
        """Extract client IP address."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR', 'unknown')
        return ip


class RequestLoggingMiddleware:
    """
    Middleware to log all API requests for auditing purposes.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        self.logger = logging.getLogger('e2i_api.requests')

    def __call__(self, request):
        start_time = time.time()
        
        # Log request
        self.log_request(request)
        
        response = self.get_response(request)
        
        # Log response
        duration = time.time() - start_time
        self.log_response(request, response, duration)
        
        return response

    def log_request(self, request):
        """Log incoming request details."""
        user_info = "anonymous"
        if hasattr(request, 'user') and request.user and hasattr(request.user, 'id'):
            user_info = f"{request.user.username} ({request.user.role})"
        
        self.logger.info(
            f"REQUEST {request.method} {request.path} - User: {user_info} - IP: {self.get_client_ip(request)}"
        )

    def log_response(self, request, response, duration):
        """Log response details."""
        user_info = "anonymous"
        if hasattr(request, 'user') and request.user and hasattr(request.user, 'id'):
            user_info = f"{request.user.username}"
        
        self.logger.info(
            f"RESPONSE {response.status_code} {request.path} - "
            f"User: {user_info} - Duration: {duration:.3f}s"
        )
        
        # Log errors with more detail
        if response.status_code >= 400:
            self.logger.warning(
                f"ERROR {response.status_code} {request.path} - "
                f"User: {user_info} - IP: {self.get_client_ip(request)}"
            )

    def get_client_ip(self, request):
        """Extract client IP address."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR', 'unknown')
        return ip


class APIKeyValidationMiddleware:
    """
    Enhanced middleware for API key validation with additional security checks.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        self.suspicious_threshold = 10  # Number of invalid attempts before flagging

    def __call__(self, request):
        # Track invalid API key attempts
        api_key = request.headers.get('X-API-Key')
        if api_key and not self.is_valid_api_key(api_key):
            self.track_invalid_attempt(request, api_key)
        
        return self.get_response(request)

    def is_valid_api_key(self, api_key):
        """Check if API key exists and is valid."""
        try:
            User.objects.get(api_key=api_key, is_active=True)
            return True
        except User.DoesNotExist:
            return False

    def track_invalid_attempt(self, request, api_key):
        """Track invalid API key attempts for security monitoring."""
        ip = self.get_client_ip(request)
        
        # Hash the API key for logging (don't store full key)
        api_key_hash = hashlib.sha256(api_key.encode()).hexdigest()[:16]
        
        logger.warning(
            f"Invalid API key attempt from IP {ip}: {api_key_hash}... "
            f"Path: {request.path}"
        )
        
        # Track attempts per IP
        cache_key = f"invalid_api_attempts:{ip}"
        attempts = cache.get(cache_key, 0) + 1
        cache.set(cache_key, attempts, 3600)  # Track for 1 hour
        
        if attempts >= self.suspicious_threshold:
            logger.error(
                f"SECURITY ALERT: IP {ip} has made {attempts} invalid API key attempts"
            )

    def get_client_ip(self, request):
        """Extract client IP address."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR', 'unknown')
        return ip