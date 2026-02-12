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
from apps.api.admin_views import system_status

urlpatterns = [
    # Admin system status dashboard (must be before admin.site.urls)
    path(settings.ADMIN_URL + 'system-status/', system_status, name='admin-system-status'),

    # Django Admin (configurable URL via ADMIN_URL setting for security)
    path(settings.ADMIN_URL, admin.site.urls),

    # API v1
    path('api/', include('apps.api.urls')),

    # API Documentation
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),

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

# Customize admin site
admin.site.site_header = 'Junkbin.io Administration'
admin.site.site_title = 'Junkbin.io Admin'
admin.site.index_title = 'Dashboard'
