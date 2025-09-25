# e2i_api/middleware.py - Custom middleware for Railway health checks

from django.http import HttpResponse

class HealthCheckMiddleware:
    """
    Middleware to handle Railway health checks before any redirects.
    This ensures health checks return 200 OK immediately without going through
    Django's security middleware that redirects HTTP to HTTPS.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Handle health check requests immediately
        if request.path == '/health/':
            return HttpResponse("OK", status=200, content_type="text/plain")
        
        # For all other requests, continue with normal processing
        return self.get_response(request)
