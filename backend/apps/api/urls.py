"""
API URL configuration for Junkbin.io

All API endpoints are organized under /api/
"""
from django.urls import path, include
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
    TokenVerifyView,
)

from .views import APIRootView, SearchView, HealthCheckView, StatsView

urlpatterns = [
    # API Root
    path('', APIRootView.as_view(), name='api-root'),

    # Health Check & Stats
    path('health/', HealthCheckView.as_view(), name='health-check'),
    path('stats/', StatsView.as_view(), name='stats'),

    # JWT Authentication
    path('auth/token/', TokenObtainPairView.as_view(), name='token-obtain-pair'),
    path('auth/token/refresh/', TokenRefreshView.as_view(), name='token-refresh'),
    path('auth/token/verify/', TokenVerifyView.as_view(), name='token-verify'),

    # App endpoints
    path('', include('apps.users.urls')),
    path('', include('apps.products.urls')),
    path('', include('apps.components.urls')),
    path('', include('apps.submissions.urls')),
    path('', include('apps.reports.urls')),

    # Search endpoint
    path('search/', SearchView.as_view(), name='search'),
]
