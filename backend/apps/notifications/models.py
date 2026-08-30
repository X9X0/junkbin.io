"""
Notification models for Junkbin.io

Per-user in-app notifications (bell/badge) and the Web Push subscriptions
used to deliver them even when the tab is closed. Distinct from
apps.api.NotificationPreference/NotificationLog, which are admin-only email
digest preferences/audit trail -- this is the end-user-facing counterpart.
"""
import uuid

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


class Notification(models.Model):
    """A single in-app notification for one recipient."""

    class Category(models.TextChoices):
        NEW_MESSAGE = 'new_message', _('New Message')
        REPORT_FILED = 'report_filed', _('Report Filed')
        SUBMISSION_PENDING = 'submission_pending', _('Submission Pending Review')
        STRIKE_REVIEW = 'strike_review', _('Strike Review Needed')
        ACCOUNT_ACTION = 'account_action', _('Account Action')
        SUBMISSION_APPROVED = 'submission_approved', _('Submission Approved')
        SUBMISSION_REJECTED = 'submission_rejected', _('Submission Rejected')
        CONTENT_APPROVED = 'content_approved', _('Content Approved')
        CONTENT_REJECTED = 'content_rejected', _('Content Rejected')
        PRODUCT_COMMENT = 'product_comment', _('Product Comment')
        SUBMISSION_COMMENT = 'submission_comment', _('Submission Comment')
        PRODUCT_REPAIR = 'product_repair', _('New Repair Report')

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notifications',
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='+',
        help_text=_('User whose action triggered this notification, if any'),
    )
    category = models.CharField(max_length=30, choices=Category.choices)

    title = models.CharField(max_length=200)
    body = models.TextField(blank=True)
    url = models.CharField(
        max_length=300,
        blank=True,
        help_text=_('Frontend path to navigate to when this notification is clicked'),
    )

    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['recipient', 'is_read', '-created_at']),
        ]

    def __str__(self):
        return f'{self.category} -> {self.recipient}: {self.title}'

    def mark_read(self):
        if not self.is_read:
            from django.utils import timezone
            self.is_read = True
            self.read_at = timezone.now()
            self.save(update_fields=['is_read', 'read_at'])


class PushSubscription(models.Model):
    """A browser's Web Push subscription (one per device/browser)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='push_subscriptions',
    )
    endpoint = models.URLField(max_length=500, unique=True)
    p256dh = models.CharField(max_length=200)
    auth = models.CharField(max_length=100)
    user_agent = models.CharField(max_length=300, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.user} @ {self.endpoint[:60]}'
