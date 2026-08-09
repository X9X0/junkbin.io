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
    UsernameChangeView,
    AccountDeleteView,
    PreferencesView,
    EmailVerificationView,
    ResendVerificationView,
    PasswordResetRequestView,
    PasswordResetConfirmView,
    GoogleAuthView,
    GitHubAuthView,
)

router = DefaultRouter()
router.register(r'users', UserViewSet, basename='user')

urlpatterns = [
    path('', include(router.urls)),
    path('auth/register/', UserRegistrationView.as_view(), name='register'),
    path('auth/verify-email/', EmailVerificationView.as_view(), name='verify-email'),
    path('auth/resend-verification/', ResendVerificationView.as_view(), name='resend-verification'),
    path('auth/me/', CurrentUserView.as_view(), name='current-user'),
    path('auth/password/change/', PasswordChangeView.as_view(), name='password-change'),
    path('auth/username/change/', UsernameChangeView.as_view(), name='username-change'),
    path('auth/account/delete/', AccountDeleteView.as_view(), name='account-delete'),
    path('auth/password/reset/', PasswordResetRequestView.as_view(), name='password-reset-request'),
    path('auth/password/reset/confirm/', PasswordResetConfirmView.as_view(), name='password-reset-confirm'),
    path('auth/preferences/', PreferencesView.as_view(), name='preferences'),
    path('auth/google/', GoogleAuthView.as_view(), name='google-auth'),
    path('auth/github/', GitHubAuthView.as_view(), name='github-auth'),
]
