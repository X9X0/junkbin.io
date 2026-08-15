"""
URL configuration for Junkbin.io

The `urlpatterns` list routes URLs to views.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)
from rest_framework.permissions import IsAdminUser
from apps.api.admin_views import system_status, system_status_json
from apps.components.admin_views import bulk_edit_components, bulk_edit_components_action
from apps.users.admin_views import user_contributions, user_contributions_action

urlpatterns = [
    # Prometheus metrics
    path('', include('django_prometheus.urls')),

    # Admin system status dashboard (must be before admin.site.urls)
    path(settings.ADMIN_URL + 'system-status/', system_status, name='admin-system-status'),
    path(settings.ADMIN_URL + 'system-status/json/', system_status_json, name='admin-system-status-json'),

    # Admin user contribution review (must be before admin.site.urls)
    path(settings.ADMIN_URL + 'user-contributions/<uuid:user_id>/', user_contributions, name='admin-user-contributions'),
    path(settings.ADMIN_URL + 'user-contributions/<uuid:user_id>/actions/', user_contributions_action, name='admin-user-contributions-action'),

    # Admin component bulk edit (must be before admin.site.urls)
    path(settings.ADMIN_URL + 'component-bulk-edit/', bulk_edit_components, name='admin-component-bulk-edit'),
    path(settings.ADMIN_URL + 'component-bulk-edit/apply/', bulk_edit_components_action, name='admin-component-bulk-edit-action'),

    # Django Admin (configurable URL via ADMIN_URL setting for security)
    path(settings.ADMIN_URL, admin.site.urls),

    # API v1
    path('api/', include('apps.api.urls')),

    # API Documentation (staff only)
    path('api/schema/', SpectacularAPIView.as_view(permission_classes=[IsAdminUser]), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema', permission_classes=[IsAdminUser]), name='swagger-ui'),
    path('api/redoc/', SpectacularRedocView.as_view(url_name='schema', permission_classes=[IsAdminUser]), name='redoc'),

    # Django Allauth (for OAuth callbacks)
    path('accounts/', include('allauth.urls')),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

    # Debug toolbar
    import debug_toolbar
    urlpatterns = [
        path('__debug__/', include(debug_toolbar.urls)),
    ] + urlpatterns
