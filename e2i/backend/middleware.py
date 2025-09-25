from django.http import HttpResponse
import logging

logger = logging.getLogger(__name__)

class HealthCheckMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        logger.info(f"Request received: {request.method} {request.path}")
        
        if request.path == '/health/':
            return HttpResponse("OK", status=200)
            
        response = self.get_response(request)
        logger.info(f"Response status: {response.status_code}")
        return response
