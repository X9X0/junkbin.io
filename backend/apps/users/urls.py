"""
User URL configuration for Junkbin.io
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    UserViewSet,
    UserRegistrationView,
    CurrentUserView,
    PasswordChangeView,
    PreferencesView,
)

router = DefaultRouter()
router.register(r'users', UserViewSet, basename='user')

urlpatterns = [
    path('', include(router.urls)),
    path('auth/register/', UserRegistrationView.as_view(), name='register'),
    path('auth/me/', CurrentUserView.as_view(), name='current-user'),
    path('auth/password/change/', PasswordChangeView.as_view(), name='password-change'),
    path('auth/preferences/', PreferencesView.as_view(), name='preferences'),
]
