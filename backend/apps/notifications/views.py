from django.conf import settings
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Notification, PushSubscription
from .serializers import NotificationSerializer, PushSubscribeSerializer


class NotificationViewSet(viewsets.ReadOnlyModelViewSet):
    """
    GET /notifications/                 -- paginated, newest first
    GET /notifications/unread-count/    -- {"count": N}
    POST /notifications/{id}/mark-read/
    POST /notifications/mark-all-read/
    """
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Notification.objects.filter(recipient=self.request.user)

    @action(detail=False, methods=['get'], url_path='unread-count')
    def unread_count(self, request):
        count = self.get_queryset().filter(is_read=False).count()
        return Response({'count': count})

    @action(detail=True, methods=['post'], url_path='mark-read')
    def mark_read(self, request, pk=None):
        notification = self.get_object()
        notification.mark_read()
        return Response(NotificationSerializer(notification).data)

    @action(detail=False, methods=['post'], url_path='mark-all-read')
    def mark_all_read(self, request):
        from django.utils import timezone
        updated = self.get_queryset().filter(is_read=False).update(
            is_read=True, read_at=timezone.now(),
        )
        return Response({'updated': updated})


class VapidPublicKeyView(APIView):
    """GET /notifications/vapid-public-key/ -- so the frontend never hardcodes it."""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        return Response({'key': settings.VAPID_PUBLIC_KEY})


class PushSubscribeView(APIView):
    """POST /notifications/push-subscribe/"""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = PushSubscribeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(user=request.user, user_agent=request.META.get('HTTP_USER_AGENT', ''))
        return Response(status=status.HTTP_201_CREATED)


class PushUnsubscribeView(APIView):
    """POST /notifications/push-unsubscribe/  body: {"endpoint": "..."}"""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        endpoint = request.data.get('endpoint')
        if not endpoint:
            return Response({'detail': 'endpoint is required'}, status=status.HTTP_400_BAD_REQUEST)
        PushSubscription.objects.filter(user=request.user, endpoint=endpoint).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
