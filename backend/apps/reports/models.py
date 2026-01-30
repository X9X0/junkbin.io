"""
Report models for Junkbin.io

Models for user reports and the 3-strike moderation system.
"""
import uuid
from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType


class Report(models.Model):
    """
    User-submitted reports about content issues.
    """

    class ReportReason(models.TextChoices):
        INCORRECT_INFO = 'incorrect_info', _('Incorrect Information')
        DUPLICATE = 'duplicate', _('Duplicate Entry')
        SPAM = 'spam', _('Spam/Advertising')
        INAPPROPRIATE = 'inappropriate', _('Inappropriate Content')
        COPYRIGHT = 'copyright', _('Copyright Violation')
        OTHER = 'other', _('Other')

    class Status(models.TextChoices):
        PENDING = 'pending', _('Pending')
        INVESTIGATING = 'investigating', _('Under Investigation')
        RESOLVED_VALID = 'resolved_valid', _('Resolved - Valid')
        RESOLVED_INVALID = 'resolved_invalid', _('Resolved - Invalid')
        DISMISSED = 'dismissed', _('Dismissed')

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    # Generic foreign key to reported content
    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        help_text=_('Type of content being reported')
    )
    object_id = models.UUIDField(
        help_text=_('ID of the reported item')
    )
    reported_item = GenericForeignKey('content_type', 'object_id')

    # Report details
    reason = models.CharField(
        max_length=20,
        choices=ReportReason.choices,
        help_text=_('Reason for report')
    )
    description = models.TextField(
        help_text=_('Detailed description of the issue')
    )

    # Reporter info
    reporter = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='submitted_reports'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    # Reported user (owner of the content)
    reported_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reports_received'
    )

    # Resolution
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True
    )
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='resolved_reports'
    )
    resolution_notes = models.TextField(blank=True)

    # Whether this report counted as a strike against the user
    counted_as_strike = models.BooleanField(
        default=False,
        help_text=_('Whether this report counted against the user')
    )

    class Meta:
        verbose_name = _('report')
        verbose_name_plural = _('reports')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', '-created_at']),
            models.Index(fields=['reported_user', 'counted_as_strike']),
            models.Index(fields=['content_type', 'object_id']),
        ]

    def __str__(self):
        return f'Report by {self.reporter} - {self.get_reason_display()}'

    def resolve_as_valid(self, resolver, notes=''):
        """Resolve report as valid and apply strike if applicable."""
        from django.utils import timezone

        self.status = self.Status.RESOLVED_VALID
        self.resolved_at = timezone.now()
        self.resolved_by = resolver
        self.resolution_notes = notes
        self.counted_as_strike = True
        self.save()

        # Increment strike count on reported user
        if self.reported_user:
            self.reported_user.increment_report_count()

    def resolve_as_invalid(self, resolver, notes=''):
        """Resolve report as invalid (false report)."""
        from django.utils import timezone

        self.status = self.Status.RESOLVED_INVALID
        self.resolved_at = timezone.now()
        self.resolved_by = resolver
        self.resolution_notes = notes
        self.counted_as_strike = False
        self.save()

    def dismiss(self, resolver, notes=''):
        """Dismiss the report."""
        from django.utils import timezone

        self.status = self.Status.DISMISSED
        self.resolved_at = timezone.now()
        self.resolved_by = resolver
        self.resolution_notes = notes
        self.save()


class UserReview(models.Model):
    """
    Admin review triggered when a user reaches 3 strikes.
    """

    class ReviewType(models.TextChoices):
        AUTOMATIC = 'automatic', _('Automatic (3 Strike Threshold)')
        MANUAL = 'manual', _('Manual Review Request')

    class Status(models.TextChoices):
        PENDING = 'pending', _('Pending Review')
        IN_PROGRESS = 'in_progress', _('In Progress')
        CLEARED = 'cleared', _('Cleared')
        WARNING_ISSUED = 'warning_issued', _('Warning Issued')
        RESTRICTED = 'restricted', _('Account Restricted')
        SUSPENDED = 'suspended', _('Account Suspended')

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    # User being reviewed
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='user_reviews'
    )

    # Review trigger
    review_type = models.CharField(
        max_length=20,
        choices=ReviewType.choices
    )
    triggered_by = models.ForeignKey(
        Report,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text=_('Report that triggered this review')
    )
    trigger_report_count = models.PositiveIntegerField(
        default=0,
        help_text=_('User report count at time of trigger')
    )

    # Review status
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING
    )

    # Review timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    reviewer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='conducted_reviews'
    )

    # Notes and details
    notes = models.TextField(
        blank=True,
        help_text=_('Internal notes about the review')
    )
    action_taken = models.TextField(
        blank=True,
        help_text=_('Description of action taken')
    )

    # Related reports to consider
    related_reports = models.ManyToManyField(
        Report,
        blank=True,
        related_name='user_reviews'
    )

    class Meta:
        verbose_name = _('user review')
        verbose_name_plural = _('user reviews')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['status', '-created_at']),
        ]

    def __str__(self):
        return f'Review of {self.user.username} - {self.get_status_display()}'

    def complete_review(self, reviewer, status, notes='', action_taken=''):
        """Complete the user review with a decision."""
        from django.utils import timezone

        self.status = status
        self.reviewed_at = timezone.now()
        self.reviewer = reviewer
        self.notes = notes
        self.action_taken = action_taken
        self.save()

        # Apply account restrictions if needed
        if status == self.Status.SUSPENDED:
            self.user.is_active = False
            self.user.save(update_fields=['is_active'])
        elif status == self.Status.RESTRICTED:
            self.user.is_trusted = False
            self.user.save(update_fields=['is_trusted'])
