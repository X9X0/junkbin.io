"""
API URL configuration for Junkbin.io

All API endpoints are organized under /api/
"""
from django.conf import settings
from django.urls import path, include
from django.views.decorators.csrf import ensure_csrf_cookie
from django.utils.decorators import method_decorator
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
    TokenVerifyView,
)
from rest_framework_simplejwt.tokens import RefreshToken

from apps.users.models import UserActivity
from .views import APIRootView, SearchView, HealthCheckView, StatsView, AnalyticsView


@method_decorator(ensure_csrf_cookie, name='dispatch')
class GetCSRFTokenView(APIView):
    """Endpoint to get CSRF cookie for SPA."""
    permission_classes = []

    def get(self, request):
        return Response({'detail': 'CSRF cookie set'})


def set_token_cookies(response, access_token, refresh_token=None):
    """Set HttpOnly cookies for JWT tokens."""
    jwt_settings = settings.SIMPLE_JWT

    response.set_cookie(
        key=jwt_settings.get('AUTH_COOKIE', 'access_token'),
        value=access_token,
        httponly=jwt_settings.get('AUTH_COOKIE_HTTP_ONLY', True),
        secure=jwt_settings.get('AUTH_COOKIE_SECURE', True),
        samesite=jwt_settings.get('AUTH_COOKIE_SAMESITE', 'Lax'),
        path=jwt_settings.get('AUTH_COOKIE_PATH', '/'),
        max_age=int(jwt_settings['ACCESS_TOKEN_LIFETIME'].total_seconds()),
    )

    if refresh_token:
        response.set_cookie(
            key=jwt_settings.get('AUTH_COOKIE_REFRESH', 'refresh_token'),
            value=refresh_token,
            httponly=jwt_settings.get('AUTH_COOKIE_HTTP_ONLY', True),
            secure=jwt_settings.get('AUTH_COOKIE_SECURE', True),
            samesite=jwt_settings.get('AUTH_COOKIE_SAMESITE', 'Lax'),
            path=jwt_settings.get('AUTH_COOKIE_PATH', '/'),
            max_age=int(jwt_settings['REFRESH_TOKEN_LIFETIME'].total_seconds()),
        )

    return response


def clear_token_cookies(response):
    """Clear JWT token cookies."""
    jwt_settings = settings.SIMPLE_JWT

    response.delete_cookie(
        key=jwt_settings.get('AUTH_COOKIE', 'access_token'),
        path=jwt_settings.get('AUTH_COOKIE_PATH', '/'),
        samesite=jwt_settings.get('AUTH_COOKIE_SAMESITE', 'Lax'),
    )
    response.delete_cookie(
        key=jwt_settings.get('AUTH_COOKIE_REFRESH', 'refresh_token'),
        path=jwt_settings.get('AUTH_COOKIE_PATH', '/'),
        samesite=jwt_settings.get('AUTH_COOKIE_SAMESITE', 'Lax'),
    )

    return response


class CookieTokenObtainPairView(TokenObtainPairView):
    """Token obtain view that sets HttpOnly cookies."""
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'auth'

    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        if response.status_code == 200:
            serializer = self.get_serializer(data=request.data)
            try:
                serializer.is_valid()
                user = serializer.user
                x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
                ip = x_forwarded_for.split(',')[0].strip() if x_forwarded_for else request.META.get('REMOTE_ADDR')
                UserActivity.objects.create(
                    user=user,
                    activity_type=UserActivity.ActivityType.LOGIN,
                    ip_address=ip,
                    user_agent=request.META.get('HTTP_USER_AGENT', '')[:500],
                )
            except Exception:
                pass
        return response

    def finalize_response(self, request, response, *args, **kwargs):
        if response.status_code == 200 and 'access' in response.data:
            response = set_token_cookies(
                response,
                response.data['access'],
                response.data.get('refresh')
            )
            # Remove tokens from response body for cookie-based flow
            # Keep them for backwards compatibility with localStorage clients
        return super().finalize_response(request, response, *args, **kwargs)


class CookieTokenRefreshView(TokenRefreshView):
    """Token refresh view that reads from and sets HttpOnly cookies."""
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'auth'

    def post(self, request, *args, **kwargs):
        # Try to get refresh token from cookie if not in body
        if 'refresh' not in request.data:
            refresh_token = request.COOKIES.get(
                settings.SIMPLE_JWT.get('AUTH_COOKIE_REFRESH', 'refresh_token')
            )
            if refresh_token:
                request._full_data = {'refresh': refresh_token}

        return super().post(request, *args, **kwargs)

    def finalize_response(self, request, response, *args, **kwargs):
        if response.status_code == 200 and 'access' in response.data:
            response = set_token_cookies(
                response,
                response.data['access'],
                response.data.get('refresh')
            )
        return super().finalize_response(request, response, *args, **kwargs)


class LogoutView(APIView):
    """Logout view that clears token cookies."""

    def post(self, request):
        response = Response({'message': 'Logged out successfully'})
        response = clear_token_cookies(response)

        # Try to blacklist the refresh token if provided
        refresh_token = request.COOKIES.get(
            settings.SIMPLE_JWT.get('AUTH_COOKIE_REFRESH', 'refresh_token')
        ) or request.data.get('refresh')

        if refresh_token:
            try:
                token = RefreshToken(refresh_token)
                token.blacklist()
            except Exception:
                pass  # Token may already be blacklisted or invalid

        return response


urlpatterns = [
    # API Root
    path('', APIRootView.as_view(), name='api-root'),

    # Health Check & Stats
    path('health/', HealthCheckView.as_view(), name='health-check'),
    path('stats/', StatsView.as_view(), name='stats'),
    path('analytics/', AnalyticsView.as_view(), name='analytics'),

    # CSRF token endpoint for SPA
    path('auth/csrf/', GetCSRFTokenView.as_view(), name='csrf-token'),

    # JWT Authentication (rate limited, cookie-based)
    path('auth/token/', CookieTokenObtainPairView.as_view(), name='token-obtain-pair'),
    path('auth/token/refresh/', CookieTokenRefreshView.as_view(), name='token-refresh'),
    path('auth/token/verify/', TokenVerifyView.as_view(), name='token-verify'),
    path('auth/logout/', LogoutView.as_view(), name='logout'),

    # App endpoints
    path('', include('apps.users.urls')),
    path('', include('apps.products.urls')),
    path('', include('apps.components.urls')),
    path('', include('apps.submissions.urls')),
    path('', include('apps.reports.urls')),
    path('', include('apps.messaging.urls')),
    path('', include('apps.junkbin.urls')),
    path('', include('apps.recipes.urls')),
    path('newsletter/', include('apps.newsletter.urls')),

    # Search endpoint
    path('search/', SearchView.as_view(), name='search'),
]
