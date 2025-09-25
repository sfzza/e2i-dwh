# e2i/backend/e2i_api/urls.py
from django.contrib import admin
from django.urls import path, include, re_path
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt

@csrf_exempt
def root_view(request):
    """Root endpoint that returns API information"""
    import logging
    logger = logging.getLogger(__name__)
    logger.info("Root view called")
    
    return JsonResponse({
        "message": "E2I Data Warehouse API",
        "status": "running",
        "version": "1.0.0",
        "endpoints": {
            "admin": "/admin/",
            "health": "/health/",
            "api": "/api/"
        }
    })

@csrf_exempt  
def health_check(request):
    """Health check endpoint for Railway"""
    import logging
    logger = logging.getLogger(__name__)
    logger.info("Health view called")
    return HttpResponse("OK", status=200)

def catch_all(request, path=''):
    """Catch all undefined routes"""
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"Catch-all called for path: {request.path}")
    
    return JsonResponse({
        "error": "Not found",
        "path": request.path,
        "available_endpoints": ["/health/", "/admin/"]
    }, status=404)

urlpatterns = [
    path('', root_view, name='root'),  # This handles the root URL
    path('health/', health_check, name='health_check'),
    path('admin/', admin.site.urls),
    
    # Catch everything else
    re_path(r'^.*$', catch_all),  # Catch all undefined routes
]