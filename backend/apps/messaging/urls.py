"""
Messaging URL configuration for Junkbin.io
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    ConversationViewSet,
    SendMessageView,
    UnreadCountView,
    UserBlockViewSet,
)

router = DefaultRouter()
router.register(r'conversations', ConversationViewSet, basename='conversation')
router.register(r'messages/blocks', UserBlockViewSet, basename='user-block')

urlpatterns = [
    path('', include(router.urls)),
    path('messages/send/', SendMessageView.as_view(), name='message-send'),
    path('messages/unread-count/', UnreadCountView.as_view(), name='unread-count'),
]
