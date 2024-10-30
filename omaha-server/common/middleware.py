
import json
import logging
from django.conf import settings
from django.utils import timezone
from .models import RequestLog

logger = logging.getLogger(__name__)

class RequestLoggingMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        # Define excluded path prefixes
        self.excluded_prefixes = [
            '/static/',
            '/admin/',
            # Add other prefixes if needed
        ]
        # Optionally, retrieve STATIC_URL from settings
        self.static_url = getattr(settings, 'STATIC_URL', '/static/')

    def __call__(self, request):
        # Check if the request path starts with any excluded prefix
        if self.is_excluded(request.path):
            return self.get_response(request)

        # Code to execute for each request before the view is called
        request._start_time = timezone.now()

        response = self.get_response(request)

        # Code to execute for each request after the view is called
        try:
            # Get authenticated user
            user = request.user if request.user.is_authenticated else None

            # Get client IP address
            ip_address = self.get_client_ip(request)

            # Extract headers
            headers = {k: v for k, v in request.META.items() if k.startswith('HTTP_')}

            # Extract request body for specific methods
            body = ''
            if request.method in ['POST', 'PUT', 'PATCH']:
                try:
                    body = request.body.decode('utf-8')
                except UnicodeDecodeError:
                    body = 'Binary data'

            # Extract query parameters
            query_params = request.META.get('QUERY_STRING', '')

            # Create RequestLog entry
            RequestLog.objects.create(
                path=request.path,
                method=request.method,
                query_params=query_params,
                body=body,
                headers=json.dumps(headers),
                status_code=response.status_code,
                user=user,
                ip_address=ip_address
            )
        except Exception as e:
            logger.error(f"Error in RequestLoggingMiddleware: {e}")
            # Optionally, you can re-raise the exception to propagate it
            # raise

        return response

    def is_excluded(self, path):
        # Check if the path starts with any of the excluded prefixes
        for prefix in self.excluded_prefixes:
            if path.startswith(prefix):
                return True
        return False

    def get_client_ip(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            # In case of multiple IPs, take the first one
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
