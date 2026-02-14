"""
Junkbin URL configuration for Junkbin.io
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import JunkbinItemViewSet

router = DefaultRouter()
router.register(r'junkbin', JunkbinItemViewSet, basename='junkbin')

urlpatterns = [
    path('', include(router.urls)),
]
