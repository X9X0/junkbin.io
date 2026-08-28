"""
Messaging models for Junkbin.io

Models for user-to-user private messaging.
"""
import mimetypes
import os
import uuid
from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _


def message_attachment_path(instance, filename):
    ext = os.path.splitext(filename)[1]
    return f'messages/{instance.message.conversation_id}/{uuid.uuid4()}{ext}'


class Conversation(models.Model):
    """
    A private conversation between exactly two users.

    participant_1 always has the lexicographically smaller UUID
    to enforce the unique constraint via ordered_participants().
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    participant_1 = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='conversations_as_participant_1',
    )
    participant_2 = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='conversations_as_participant_2',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('conversation')
        verbose_name_plural = _('conversations')
        ordering = ['-updated_at']
        constraints = [
            models.UniqueConstraint(
                fields=['participant_1', 'participant_2'],
                name='unique_conversation_pair',
            ),
            models.CheckConstraint(
                check=~models.Q(participant_1=models.F('participant_2')),
                name='no_self_conversation',
            ),
        ]
        indexes = [
            models.Index(fields=['participant_1', '-updated_at']),
            models.Index(fields=['participant_2', '-updated_at']),
        ]

    def __str__(self):
        return f'Conversation between {self.participant_1} and {self.participant_2}'

    def other_participant(self, user):
        """Return the other participant given one user."""
        return self.participant_2 if self.participant_1 == user else self.participant_1

    @staticmethod
    def ordered_participants(user_a, user_b):
        """Return (participant_1, participant_2) in canonical UUID order."""
        if str(user_a.pk) < str(user_b.pk):
            return user_a, user_b
        return user_b, user_a


class Message(models.Model):
    """A single message within a conversation."""

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name='messages',
    )
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='sent_messages',
    )
    content = models.TextField(
        max_length=5000,
        blank=True,
        help_text=_('Message content')
    )
    is_read = models.BooleanField(
        default=False,
        help_text=_('Whether recipient has read this')
    )
    forwarded_from_conversation = models.ForeignKey(
        Conversation,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='+',
        help_text=_(
            'Set only on auto-forwarded copies/relays: the conversation this '
            'message was mirrored from or back into (see forward_messages_to).'
        ),
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _('message')
        verbose_name_plural = _('messages')
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['conversation', 'created_at']),
            models.Index(fields=['sender', 'is_read']),
        ]

    def __str__(self):
        sender_name = self.sender.username if self.sender else 'deleted'
        return f'Message by {sender_name} at {self.created_at}'


class MessageAttachment(models.Model):
    """A file attached to a message."""

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    message = models.ForeignKey(
        Message,
        on_delete=models.CASCADE,
        related_name='attachments',
    )
    file = models.FileField(upload_to=message_attachment_path)
    original_filename = models.CharField(max_length=255)
    file_type = models.CharField(max_length=100, blank=True)
    file_size = models.PositiveIntegerField(default=0)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _('message attachment')
        verbose_name_plural = _('message attachments')
        ordering = ['uploaded_at']

    def __str__(self):
        return f'Attachment {self.original_filename} on {self.message_id}'

    def save(self, *args, **kwargs):
        # file_type/file_size are set by the caller (view) from the uploaded
        # file object where f.content_type and f.size are reliable.
        # Fall back to mimetypes if somehow file_type is still blank.
        if not self.file_type and self.original_filename:
            mime, _ = mimetypes.guess_type(self.original_filename)
            self.file_type = mime or 'application/octet-stream'
        super().save(*args, **kwargs)


class UserBlock(models.Model):
    """
    User-to-user block. Prevents messaging in either direction.
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    blocker = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='blocked_users',
    )
    blocked_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='blocked_by',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _('user block')
        verbose_name_plural = _('user blocks')
        constraints = [
            models.UniqueConstraint(
                fields=['blocker', 'blocked_user'],
                name='unique_user_block',
            ),
            models.CheckConstraint(
                check=~models.Q(blocker=models.F('blocked_user')),
                name='no_self_block',
            ),
        ]

    def __str__(self):
        return f'{self.blocker} blocked {self.blocked_user}'
