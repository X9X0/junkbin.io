from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import BackgroundRemovalPreviewViewSet

router = DefaultRouter()
router.register(r'bg-removal', BackgroundRemovalPreviewViewSet, basename='bg-removal')

urlpatterns = [
    path('', include(router.urls)),
]
