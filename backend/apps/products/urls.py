"""
Product URL configuration for Junkbin.io
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import ProductViewSet, SchematicViewSet

router = DefaultRouter()
router.register(r'products', ProductViewSet, basename='product')
router.register(r'schematics', SchematicViewSet, basename='schematic')

urlpatterns = [
    path('', include(router.urls)),
]
