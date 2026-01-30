"""
Report URL configuration for Junkbin.io
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import ReportViewSet, UserReviewViewSet

router = DefaultRouter()
router.register(r'reports', ReportViewSet, basename='report')
router.register(r'user-reviews', UserReviewViewSet, basename='user-review')

urlpatterns = [
    path('', include(router.urls)),
]
