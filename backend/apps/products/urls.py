"""
Product URL configuration for Junkbin.io
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    ProductViewSet, SchematicViewSet, FirmwareViewSet, ProductImageViewSet,
    ComponentSuggestionViewSet,
)

router = DefaultRouter()
router.register(r'products', ProductViewSet, basename='product')
router.register(r'schematics', SchematicViewSet, basename='schematic')
router.register(r'firmware', FirmwareViewSet, basename='firmware')
router.register(r'product-images', ProductImageViewSet, basename='product-image')
router.register(r'component-suggestions', ComponentSuggestionViewSet, basename='component-suggestion')

urlpatterns = [
    path('', include(router.urls)),
]
