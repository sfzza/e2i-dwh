from django.http import HttpResponse, JsonResponse
import logging
import traceback

logger = logging.getLogger(__name__)

class HealthCheckMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Log EVERY request
        print(f"Request received: {request.method} {request.path}")
        logger.info(f"Request received: {request.method} {request.path}")
        
        if request.path == '/health/':
            return HttpResponse("OK", status=200)
        
        try:
            response = self.get_response(request)
            print(f"Response status: {response.status_code}")
            return response
        except Exception as e:
            print(f"ERROR handling {request.path}: {str(e)}")
            logger.error(f"ERROR handling {request.path}: {traceback.format_exc()}")
            return JsonResponse({"error": str(e)}, status=500)
