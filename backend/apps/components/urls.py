"""
Component URL configuration for Junkbin.io
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import ComponentViewSet, ProductComponentViewSet, ComponentImageModerationViewSet, ComponentDatasheetViewSet

router = DefaultRouter()
router.register(r'components', ComponentViewSet, basename='component')
router.register(r'product-components', ProductComponentViewSet, basename='product-component')
router.register(r'component-images', ComponentImageModerationViewSet, basename='component-image')
router.register(r'component-datasheets', ComponentDatasheetViewSet, basename='component-datasheet')

urlpatterns = [
    path('', include(router.urls)),
]
