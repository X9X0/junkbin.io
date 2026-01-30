"""
Component URL configuration for Junkbin.io
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import ComponentViewSet, ProductComponentViewSet

router = DefaultRouter()
router.register(r'components', ComponentViewSet, basename='component')
router.register(r'product-components', ProductComponentViewSet, basename='product-component')

urlpatterns = [
    path('', include(router.urls)),
]
