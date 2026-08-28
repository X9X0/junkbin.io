"""
Submission models for Junkbin.io

Models for tracking content submissions and their review status.
"""
import uuid
from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _


class Submission(models.Model):
    """
    Tracks submissions of new products or updates to existing content.
    """

    class SubmissionType(models.TextChoices):
        NEW_PRODUCT = 'new_product', _('New Product')
        UPDATE_EXISTING = 'update_existing', _('Update Existing')
        COMPONENT_ADDITION = 'component_addition', _('Component Addition')
        IMAGE_ADDITION = 'image_addition', _('Image Addition')
        BULK_IMPORT = 'bulk_import', _('Bulk Import')

    class SubmissionLevel(models.TextChoices):
        BASIC = 'basic', _('Basic (Major Components Only)')
        ADVANCED = 'advanced', _('Advanced (Complete BOM)')

    class Status(models.TextChoices):
        DRAFT = 'draft', _('Draft')
        PENDING = 'pending', _('Pending Review')
        IN_REVIEW = 'in_review', _('In Review')
        APPROVED = 'approved', _('Approved')
        REJECTED = 'rejected', _('Rejected')
        NEEDS_CHANGES = 'needs_changes', _('Needs Changes')

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    # Submission metadata
    submission_type = models.CharField(
        max_length=30,
        choices=SubmissionType.choices,
        help_text=_('Type of submission')
    )
    submission_level = models.CharField(
        max_length=20,
        choices=SubmissionLevel.choices,
        default=SubmissionLevel.BASIC,
        help_text=_('Level of detail')
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True
    )

    # Related content
    product = models.ForeignKey(
        'products.Product',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='submissions'
    )

    # For tracking changes made
    changes_summary = models.TextField(
        blank=True,
        help_text=_('Summary of changes made')
    )
    changes_data = models.JSONField(
        default=dict,
        blank=True,
        help_text=_('Detailed change data for audit')
    )

    # Submitter info
    submitted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='submissions'
    )
    submitted_at = models.DateTimeField(auto_now_add=True)

    # Review info
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviewed_submissions'
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    review_notes = models.TextField(
        blank=True,
        help_text=_('Notes from reviewer')
    )

    # Auto-approval tracking
    auto_approved = models.BooleanField(
        default=False,
        help_text=_('Whether this was auto-approved (trusted user)')
    )

    class Meta:
        verbose_name = _('submission')
        verbose_name_plural = _('submissions')
        ordering = ['-submitted_at']
        indexes = [
            models.Index(fields=['status', '-submitted_at']),
            models.Index(fields=['submitted_by', '-submitted_at']),
        ]

    def __str__(self):
        return f'{self.get_submission_type_display()} by {self.submitted_by} - {self.get_status_display()}'

    def approve(self, reviewer, notes=''):
        """Approve this submission."""
        from django.utils import timezone

        self.status = self.Status.APPROVED
        self.reviewed_by = reviewer
        self.reviewed_at = timezone.now()
        self.review_notes = notes
        self.save()

        # Update related content
        if self.product:
            self.product.is_approved = True
            self.product.save(update_fields=['is_approved'])

        # Update user contribution
        if self.submitted_by:
            self.submitted_by.increment_contribution()

        if self.submitted_by:
            from apps.notifications.services import notify
            from apps.notifications.models import Notification
            notify(
                self.submitted_by, Notification.Category.SUBMISSION_APPROVED,
                title='Your submission was approved',
                body=notes,
                url=f'/products/{self.product.slug}' if self.product else '',
                actor=reviewer,
            )

    def reject(self, reviewer, notes=''):
        """Reject this submission."""
        from django.utils import timezone

        self.status = self.Status.REJECTED
        self.reviewed_by = reviewer
        self.reviewed_at = timezone.now()
        self.review_notes = notes
        self.save()

        if self.submitted_by:
            from apps.notifications.services import notify
            from apps.notifications.models import Notification
            notify(
                self.submitted_by, Notification.Category.SUBMISSION_REJECTED,
                title='Your submission was rejected',
                body=notes,
                url='/my-submissions',
                actor=reviewer,
            )

    def request_changes(self, reviewer, notes=''):
        """Request changes to this submission."""
        from django.utils import timezone

        self.status = self.Status.NEEDS_CHANGES
        self.reviewed_by = reviewer
        self.reviewed_at = timezone.now()
        self.review_notes = notes
        self.save()


class SubmissionComment(models.Model):
    """
    Comments on submissions for discussion between submitter and reviewers.
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    submission = models.ForeignKey(
        Submission,
        on_delete=models.CASCADE,
        related_name='comments'
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='submission_comments'
    )
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('submission comment')
        verbose_name_plural = _('submission comments')
        ordering = ['created_at']

    def __str__(self):
        return f'Comment by {self.author} on {self.submission}'
