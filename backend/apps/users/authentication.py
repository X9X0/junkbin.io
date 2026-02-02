"""
Custom JWT authentication using HttpOnly cookies.

This provides better security against XSS attacks by storing tokens
in HttpOnly cookies instead of localStorage.
"""
from django.conf import settings
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken, AuthenticationFailed


class CookieJWTAuthentication(JWTAuthentication):
    """
    JWT Authentication that reads tokens from HttpOnly cookies.

    Falls back to Authorization header for backwards compatibility
    and API testing tools.
    """

    def authenticate(self, request):
        # First, try to get token from cookie
        raw_token = request.COOKIES.get(
            settings.SIMPLE_JWT.get('AUTH_COOKIE', 'access_token')
        )

        if raw_token is None:
            # Fall back to header-based authentication
            return super().authenticate(request)

        # Validate the token from cookie
        validated_token = self.get_validated_token(raw_token)

        return self.get_user(validated_token), validated_token
