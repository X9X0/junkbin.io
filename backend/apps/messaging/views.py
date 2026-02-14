"""
Messaging views for Junkbin.io API
"""
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from django.contrib.auth import get_user_model
from django.db.models import Q
from django.utils import timezone

from .models import Conversation, Message, UserBlock
from .serializers import (
    ConversationListSerializer,
    ConversationDetailSerializer,
    MessageSerializer,
    MessageCreateSerializer,
    UserBlockSerializer,
)
from apps.api.permissions import IsVerifiedEmail
from apps.api.throttling import MessageRateThrottle

User = get_user_model()


class ConversationViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for listing and retrieving conversations.

    list:     GET /conversations/              - paginated inbox
    retrieve: GET /conversations/{id}/         - conversation detail (marks messages read)
    messages: GET /conversations/{id}/messages/ - paginated messages
    """

    permission_classes = [permissions.IsAuthenticated, IsVerifiedEmail]

    def get_serializer_class(self):
        if self.action == 'list':
            return ConversationListSerializer
        return ConversationDetailSerializer

    def get_queryset(self):
        user = self.request.user
        return Conversation.objects.filter(
            Q(participant_1=user) | Q(participant_2=user)
        ).select_related(
            'participant_1', 'participant_2'
        ).prefetch_related('messages').order_by('-updated_at')

    def retrieve(self, request, *args, **kwargs):
        conversation = self.get_object()
        # Mark all unread messages from other participant as read
        Message.objects.filter(
            conversation=conversation,
            is_read=False,
        ).exclude(sender=request.user).update(is_read=True)

        serializer = self.get_serializer(conversation)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def messages(self, request, pk=None):
        """Paginated messages for a conversation."""
        conversation = self.get_object()
        messages = conversation.messages.select_related('sender').order_by('-created_at')

        page = self.paginate_queryset(messages)
        if page is not None:
            serializer = MessageSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = MessageSerializer(messages, many=True)
        return Response(serializer.data)


class SendMessageView(APIView):
    """
    POST /messages/send/

    Send a message to an existing conversation (conversation_id)
    or start a new one (recipient_id).
    """

    permission_classes = [permissions.IsAuthenticated, IsVerifiedEmail]
    throttle_classes = [MessageRateThrottle]

    def post(self, request):
        serializer = MessageCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        sender = request.user
        content = serializer.validated_data['content']
        conversation_id = request.data.get('conversation_id')
        recipient_id = serializer.validated_data.get('recipient_id')

        # Check sender is not messaging-blocked
        if sender.messaging_blocked:
            return Response(
                {'detail': 'Your messaging privileges have been suspended.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        if conversation_id:
            try:
                conversation = Conversation.objects.get(
                    Q(pk=conversation_id),
                    Q(participant_1=sender) | Q(participant_2=sender),
                )
            except Conversation.DoesNotExist:
                return Response(
                    {'detail': 'Conversation not found.'},
                    status=status.HTTP_404_NOT_FOUND,
                )
            recipient = conversation.other_participant(sender)
        elif recipient_id:
            try:
                recipient = User.objects.get(pk=recipient_id, is_active=True)
            except User.DoesNotExist:
                return Response(
                    {'detail': 'Recipient not found.'},
                    status=status.HTTP_404_NOT_FOUND,
                )

            if recipient == sender:
                return Response(
                    {'detail': 'You cannot message yourself.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Find or create conversation in canonical order
            p1, p2 = Conversation.ordered_participants(sender, recipient)
            conversation, _created = Conversation.objects.get_or_create(
                participant_1=p1,
                participant_2=p2,
            )
        else:
            return Response(
                {'detail': 'Either conversation_id or recipient_id is required.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Check recipient is not messaging-blocked
        if recipient.messaging_blocked:
            return Response(
                {'detail': 'This user is not available for messaging.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        # Check user-to-user blocks (either direction)
        if UserBlock.objects.filter(
            Q(blocker=sender, blocked_user=recipient) |
            Q(blocker=recipient, blocked_user=sender)
        ).exists():
            return Response(
                {'detail': 'You cannot message this user.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        # Check recipient has verified email
        if not recipient.email_verified:
            return Response(
                {'detail': 'This user has not verified their email.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        # Create the message
        message = Message.objects.create(
            conversation=conversation,
            sender=sender,
            content=content,
        )

        # Bump conversation updated_at
        conversation.updated_at = timezone.now()
        conversation.save(update_fields=['updated_at'])

        # Trigger email notification async
        from .tasks import notify_new_message
        notify_new_message.delay(str(message.pk))

        return Response(
            MessageSerializer(message).data,
            status=status.HTTP_201_CREATED,
        )


class UnreadCountView(APIView):
    """
    GET /messages/unread-count/

    Returns total unread message count for the header badge.
    """

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        count = Message.objects.filter(
            Q(conversation__participant_1=request.user) |
            Q(conversation__participant_2=request.user),
            is_read=False,
        ).exclude(sender=request.user).count()

        return Response({'unread_count': count})


class UserBlockViewSet(viewsets.ModelViewSet):
    """
    Manage user-to-user blocks.

    list:    GET    /messages/blocks/       - list blocked users
    create:  POST   /messages/blocks/       - block a user ({user_id})
    destroy: DELETE /messages/blocks/{id}/  - unblock a user
    """

    permission_classes = [permissions.IsAuthenticated, IsVerifiedEmail]
    serializer_class = UserBlockSerializer
    http_method_names = ['get', 'post', 'delete', 'head', 'options']

    def get_queryset(self):
        return UserBlock.objects.filter(
            blocker=self.request.user
        ).select_related('blocked_user')

    def create(self, request, *args, **kwargs):
        user_id = request.data.get('user_id')
        if not user_id:
            return Response(
                {'detail': 'user_id is required.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            target = User.objects.get(pk=user_id, is_active=True)
        except User.DoesNotExist:
            return Response(
                {'detail': 'User not found.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        if target == request.user:
            return Response(
                {'detail': 'You cannot block yourself.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        block, created = UserBlock.objects.get_or_create(
            blocker=request.user,
            blocked_user=target,
        )

        if not created:
            return Response(
                {'detail': 'User is already blocked.'},
                status=status.HTTP_409_CONFLICT,
            )

        return Response(
            UserBlockSerializer(block).data,
            status=status.HTTP_201_CREATED,
        )
