"""
Custom middleware for Junkbin.io API
"""
from django.conf import settings
from django.http import HttpResponseForbidden, JsonResponse
import re


def axes_lockout_response(request, credentials, *args, **kwargs):
    """
    Custom lockout response for django-axes.
    Returns a JSON response with helpful information for locked out users.
    """
    cooloff_time = getattr(settings, 'AXES_COOLOFF_TIME', 1)

    return JsonResponse(
        {
            'detail': f'Account temporarily locked due to too many failed login attempts. '
                      f'Please try again in {cooloff_time} hour(s) or contact support.',
            'error_code': 'account_locked',
            'cooloff_hours': cooloff_time,
        },
        status=403
    )


class AdminIPWhitelistMiddleware:
    """
    Middleware to restrict admin access to whitelisted IP addresses.

    Configure via ADMIN_ALLOWED_IPS setting (list of IP addresses or CIDR ranges).
    If ADMIN_ALLOWED_IPS is empty or not set, all IPs are allowed (for development).

    Example settings:
        ADMIN_ALLOWED_IPS = ['10.0.0.1', '192.168.1.0/24', '::1']
    """

    def __init__(self, get_response):
        self.get_response = get_response
        self.admin_url_pattern = re.compile(r'^/(' + settings.ADMIN_URL.rstrip('/') + r')/')

    def __call__(self, request):
        # Get admin URL from settings (default to 'admin')
        admin_url = getattr(settings, 'ADMIN_URL', 'admin/')

        # Check if this is an admin request
        if request.path.startswith(f'/{admin_url}') or request.path.startswith('/admin/'):
            allowed_ips = getattr(settings, 'ADMIN_ALLOWED_IPS', [])

            # If no whitelist configured, allow all (development mode)
            if allowed_ips:
                client_ip = self._get_client_ip(request)

                if not self._is_ip_allowed(client_ip, allowed_ips):
                    return HttpResponseForbidden(
                        'Access denied. Your IP address is not authorized to access the admin panel.'
                    )

        return self.get_response(request)

    def _get_client_ip(self, request):
        """Extract client IP from request, considering proxy headers."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            # Take the first IP in the chain (original client)
            return x_forwarded_for.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR', '')

    def _is_ip_allowed(self, client_ip, allowed_ips):
        """Check if client IP is in the allowed list."""
        import ipaddress

        if not client_ip:
            return False

        try:
            client = ipaddress.ip_address(client_ip)
        except ValueError:
            return False

        for allowed in allowed_ips:
            try:
                # Check if it's a network (CIDR notation)
                if '/' in allowed:
                    network = ipaddress.ip_network(allowed, strict=False)
                    if client in network:
                        return True
                else:
                    # Single IP address
                    if client == ipaddress.ip_address(allowed):
                        return True
            except ValueError:
                continue

        return False
