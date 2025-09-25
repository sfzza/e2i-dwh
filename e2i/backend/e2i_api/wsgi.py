"""
WSGI config for e2i_api project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.2/howto/deployment/wsgi/
"""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "e2i_api.settings")

# Original Django application
django_application = get_wsgi_application()

# Wrapper to debug WSGI requests
def application(environ, start_response):
    print(f"WSGI Request: {environ.get('REQUEST_METHOD')} {environ.get('PATH_INFO')}")
    
    # Force root to work for debugging
    if environ.get('PATH_INFO') == '/':
        status = '200 OK'
        response_headers = [('Content-Type', 'application/json')]
        start_response(status, response_headers)
        return [b'{"message": "Direct WSGI response for root URL"}']
    
    # Pass everything else to Django
    return django_application(environ, start_response)
