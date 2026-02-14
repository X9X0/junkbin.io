"""
Messaging serializers for Junkbin.io API
"""
from rest_framework import serializers
from django.contrib.auth import get_user_model

from .models import Conversation, Message, UserBlock

User = get_user_model()


class MessageParticipantSerializer(serializers.ModelSerializer):
    """Minimal user serializer for message context."""

    class Meta:
        model = User
        fields = ['id', 'username', 'avatar', 'is_trusted', 'is_moderator']


class MessageSerializer(serializers.ModelSerializer):
    """Serializer for a single message within a thread."""

    sender = MessageParticipantSerializer(read_only=True)

    class Meta:
        model = Message
        fields = ['id', 'sender', 'content', 'is_read', 'created_at']
        read_only_fields = ['id', 'sender', 'is_read', 'created_at']


class ConversationListSerializer(serializers.ModelSerializer):
    """
    Serializer for the inbox list view.
    Includes the other participant, last message preview, and unread count.
    """

    other_participant = serializers.SerializerMethodField()
    last_message = serializers.SerializerMethodField()
    unread_count = serializers.SerializerMethodField()

    class Meta:
        model = Conversation
        fields = ['id', 'other_participant', 'last_message', 'unread_count', 'updated_at']

    def get_other_participant(self, obj):
        request = self.context.get('request')
        other = obj.other_participant(request.user)
        return MessageParticipantSerializer(other).data

    def get_last_message(self, obj):
        if hasattr(obj, '_prefetched_last_message'):
            last = obj._prefetched_last_message
        else:
            last = obj.messages.order_by('-created_at').first()
        if last:
            return {
                'content': last.content[:120],
                'sender_id': str(last.sender_id) if last.sender_id else None,
                'created_at': last.created_at.isoformat(),
                'is_read': last.is_read,
            }
        return None

    def get_unread_count(self, obj):
        request = self.context.get('request')
        return obj.messages.filter(is_read=False).exclude(sender=request.user).count()


class ConversationDetailSerializer(serializers.ModelSerializer):
    """Serializer for a single conversation with full participant info."""

    participant_1 = MessageParticipantSerializer(read_only=True)
    participant_2 = MessageParticipantSerializer(read_only=True)

    class Meta:
        model = Conversation
        fields = ['id', 'participant_1', 'participant_2', 'created_at', 'updated_at']


class MessageCreateSerializer(serializers.Serializer):
    """Serializer for sending a message."""

    recipient_id = serializers.UUIDField(
        required=False,
        help_text='Required when starting a new conversation'
    )
    content = serializers.CharField(max_length=5000)

    def validate_content(self, value):
        stripped = value.strip()
        if not stripped:
            raise serializers.ValidationError('Message content cannot be empty.')
        from utils.content_filter import check_content
        is_clean, _ = check_content(stripped)
        if not is_clean:
            raise serializers.ValidationError(
                'Your message contains prohibited language. '
                'Please review our community guidelines.'
            )
        return stripped


class UserBlockSerializer(serializers.ModelSerializer):
    """Serializer for user blocks."""

    blocked_user = MessageParticipantSerializer(read_only=True)

    class Meta:
        model = UserBlock
        fields = ['id', 'blocked_user', 'created_at']
