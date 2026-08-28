from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    NotificationViewSet,
    VapidPublicKeyView,
    PushSubscribeView,
    PushUnsubscribeView,
)

router = DefaultRouter()
router.register(r'notifications', NotificationViewSet, basename='notification')

urlpatterns = [
    # These must come before the router include -- otherwise the router's
    # notifications/<pk>/ detail route greedily matches "push-subscribe"
    # etc. as a pk and 405s instead of reaching these views.
    path('notifications/vapid-public-key/', VapidPublicKeyView.as_view(), name='vapid-public-key'),
    path('notifications/push-subscribe/', PushSubscribeView.as_view(), name='push-subscribe'),
    path('notifications/push-unsubscribe/', PushUnsubscribeView.as_view(), name='push-unsubscribe'),
    path('', include(router.urls)),
]
