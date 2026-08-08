"""
Product URL configuration for Junkbin.io
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import ProductViewSet, SchematicViewSet, FirmwareViewSet, ProductImageViewSet

router = DefaultRouter()
router.register(r'products', ProductViewSet, basename='product')
router.register(r'schematics', SchematicViewSet, basename='schematic')
router.register(r'firmware', FirmwareViewSet, basename='firmware')
router.register(r'product-images', ProductImageViewSet, basename='product-image')

urlpatterns = [
    path('', include(router.urls)),
]
