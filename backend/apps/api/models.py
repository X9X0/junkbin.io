"""
Admin notification models for Junkbin.io.
"""
import uuid

from django.conf import settings
from django.db import models


class NotificationCategory(models.TextChoices):
    SYSTEM_HEALTH = 'system_health', 'System Health'
    SYSTEM_PERFORMANCE = 'system_performance', 'System Performance'
    TASK_FAILURE = 'task_failure', 'Task Failure'
    NEW_SUBMISSION = 'new_submission', 'New Submission'
    NEW_REPORT = 'new_report', 'New Report'
    NEW_USER_REVIEW = 'new_user_review', 'New User Review'
    NEW_MEMBER = 'new_member', 'New Member'
    NEW_SUBSCRIBER = 'new_subscriber', 'New Subscriber'
    NEW_CONTENT = 'new_content', 'New Content'


class NotificationPreference(models.Model):
    """Per-staff-user notification preferences."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notification_preferences',
    )
    enabled = models.BooleanField(
        default=True,
        help_text='Master switch — disables all notifications when off.',
    )
    digest_mode = models.BooleanField(
        default=False,
        help_text='Batch community/content notifications into a daily digest.',
    )

    # System alerts (default on)
    system_health = models.BooleanField(
        default=True, help_text='Database, Redis, Celery outages',
    )
    system_performance = models.BooleanField(
        default=True, help_text='CPU, memory, or disk usage exceeds 80%',
    )
    task_failures = models.BooleanField(
        default=True, help_text='Celery task errors',
    )

    # Moderation alerts (default on)
    new_submission = models.BooleanField(
        default=True, help_text='Content submitted for review',
    )
    new_report = models.BooleanField(
        default=True, help_text='User reports filed',
    )
    new_user_review = models.BooleanField(
        default=True, help_text='3-strike automatic user reviews',
    )

    # Community/content alerts (default off)
    new_member = models.BooleanField(
        default=False, help_text='New user registrations',
    )
    new_subscriber = models.BooleanField(
        default=False, help_text='Newsletter signups',
    )
    new_content = models.BooleanField(
        default=False, help_text='New products or components added',
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Notification Preference'
        verbose_name_plural = 'Notification Preferences'

    def __str__(self):
        status = 'enabled' if self.enabled else 'disabled'
        return f'{self.user.username} ({status})'

    def is_enabled_for(self, category):
        """Check if this user has a specific notification category enabled."""
        if not self.enabled:
            return False
        field_map = {
            NotificationCategory.SYSTEM_HEALTH: self.system_health,
            NotificationCategory.SYSTEM_PERFORMANCE: self.system_performance,
            NotificationCategory.TASK_FAILURE: self.task_failures,
            NotificationCategory.NEW_SUBMISSION: self.new_submission,
            NotificationCategory.NEW_REPORT: self.new_report,
            NotificationCategory.NEW_USER_REVIEW: self.new_user_review,
            NotificationCategory.NEW_MEMBER: self.new_member,
            NotificationCategory.NEW_SUBSCRIBER: self.new_subscriber,
            NotificationCategory.NEW_CONTENT: self.new_content,
        }
        return field_map.get(category, False)


class NotificationLog(models.Model):
    """Audit trail of sent notifications."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    category = models.CharField(
        max_length=30, choices=NotificationCategory.choices, db_index=True,
    )
    subject = models.CharField(max_length=255)
    recipients = models.JSONField(default=list, help_text='List of email addresses')
    sent_at = models.DateTimeField(auto_now_add=True, db_index=True)
    status = models.CharField(
        max_length=10,
        choices=[('sent', 'Sent'), ('failed', 'Failed')],
        default='sent',
    )
    error_message = models.TextField(blank=True, default='')

    class Meta:
        verbose_name = 'Notification Log'
        verbose_name_plural = 'Notification Logs'
        ordering = ['-sent_at']

    def __str__(self):
        return f'[{self.get_category_display()}] {self.subject}'
