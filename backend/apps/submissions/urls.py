"""
Submission URL configuration for Junkbin.io
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import SubmissionViewSet

router = DefaultRouter()
router.register(r'submissions', SubmissionViewSet, basename='submission')

urlpatterns = [
    path('', include(router.urls)),
]
