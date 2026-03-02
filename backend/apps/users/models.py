"""
User models for Junkbin.io

Custom user model with reputation, contribution tracking, and OAuth support.
"""
import uuid

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _


class User(AbstractUser):
    """
    Custom user model with extended fields for the Junkbin.io platform.

    Includes reputation tracking, contribution counts, and moderation status.
    """

    class OAuthProvider(models.TextChoices):
        NONE = '', _('None (Email/Password)')
        GOOGLE = 'google', _('Google')
        GITHUB = 'github', _('GitHub')
        MICROSOFT = 'microsoft', _('Microsoft')

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    # Email is required and must be unique
    email = models.EmailField(
        _('email address'),
        unique=True,
        error_messages={
            'unique': _('A user with that email already exists.'),
        }
    )

    # OAuth/SSO provider if used
    oauth_provider = models.CharField(
        max_length=20,
        choices=OAuthProvider.choices,
        default=OAuthProvider.NONE,
        blank=True,
    )

    # Profile fields
    bio = models.TextField(
        max_length=500,
        blank=True,
        help_text=_('Brief description about yourself')
    )
    avatar = models.ImageField(
        upload_to='avatars/',
        blank=True,
        null=True
    )
    location = models.CharField(
        max_length=100,
        blank=True,
        help_text=_('City, Country')
    )
    website = models.URLField(
        blank=True,
        help_text=_('Personal website or portfolio')
    )
    preferred_language = models.CharField(
        max_length=10,
        blank=True,
        default='',
        help_text=_('Preferred UI language code (e.g. en, de, pl)')
    )

    # Reputation and contribution tracking
    reputation_score = models.IntegerField(
        default=0,
        help_text=_('Calculated reputation based on contributions and reviews')
    )
    contribution_count = models.PositiveIntegerField(
        default=0,
        help_text=_('Total number of approved contributions')
    )
    report_count = models.PositiveIntegerField(
        default=0,
        help_text=_('Number of times user content was reported')
    )
    review_count = models.PositiveIntegerField(
        default=0,
        help_text=_('Number of times user triggered admin review')
    )

    # Trust status
    is_trusted = models.BooleanField(
        default=False,
        help_text=_('Trusted users can submit without moderation queue')
    )
    messaging_blocked = models.BooleanField(
        default=False,
        help_text=_('User is blocked from sending/receiving messages (set by moderators)')
    )
    is_moderator = models.BooleanField(
        default=False,
        help_text=_('User can moderate submissions and reports')
    )

    # Email verification
    email_verified = models.BooleanField(
        default=False,
        help_text=_('Whether email address has been verified')
    )
    email_verified_at = models.DateTimeField(
        null=True,
        blank=True
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_contribution_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_('Last time user made an approved contribution')
    )

    # Settings/Preferences stored as JSON
    preferences = models.JSONField(
        default=dict,
        blank=True,
        help_text=_('User preferences and settings')
    )

    # Badges/achievements stored as JSON list of {slug, awarded_at}
    badges = models.JSONField(
        default=list,
        blank=True,
        help_text=_('Earned badges and achievements')
    )

    class Meta:
        verbose_name = _('user')
        verbose_name_plural = _('users')
        ordering = ['-created_at']

    def __str__(self):
        return self.username

    @property
    def display_name(self):
        """Return full name if available, otherwise username."""
        full_name = self.get_full_name()
        return full_name if full_name else self.username

    @property
    def can_submit_without_review(self):
        """Check if user's submissions bypass the moderation queue."""
        return self.is_trusted or self.is_staff or self.is_moderator

    def increment_contribution(self):
        """Increment contribution count and update reputation."""
        from django.utils import timezone
        self.contribution_count += 1
        self.reputation_score += 10  # Base points per contribution
        self.last_contribution_at = timezone.now()
        self._check_trusted_status()
        self.save(update_fields=[
            'contribution_count', 'reputation_score',
            'last_contribution_at', 'is_trusted'
        ])
        from apps.users.badges import check_and_award_badges
        check_and_award_badges(self)

    def increment_report_count(self):
        """Increment report count when content is reported."""
        from django.conf import settings
        self.report_count += 1
        self.reputation_score = max(0, self.reputation_score - 5)

        # Check if threshold reached for automatic review
        if self.report_count % settings.REPORT_STRIKE_THRESHOLD == 0:
            self.review_count += 1
            # Create UserReview record is handled by signal

        self.save(update_fields=['report_count', 'reputation_score', 'review_count'])

        # Notify user about the strike via email
        from apps.reports.tasks import notify_user_strike
        notify_user_strike.delay(str(self.pk))

    def _check_trusted_status(self):
        """Check and update trusted user status."""
        from django.conf import settings
        if not self.is_trusted:
            if (self.contribution_count >= settings.TRUSTED_USER_CONTRIBUTION_THRESHOLD and
                    self.reputation_score >= settings.TRUSTED_USER_MIN_REPUTATION):
                self.is_trusted = True


class UserActivity(models.Model):
    """
    Track user activity for analytics and engagement.
    """

    class ActivityType(models.TextChoices):
        LOGIN = 'login', _('Login')
        PRODUCT_VIEW = 'product_view', _('Product View')
        COMPONENT_VIEW = 'component_view', _('Component View')
        SEARCH = 'search', _('Search')
        SUBMISSION = 'submission', _('Submission')
        REPORT = 'report', _('Report Submitted')

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='activities'
    )
    activity_type = models.CharField(
        max_length=20,
        choices=ActivityType.choices
    )
    details = models.JSONField(
        default=dict,
        blank=True,
        help_text=_('Additional activity details')
    )
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True
    )
    user_agent = models.CharField(
        max_length=500,
        blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _('user activity')
        verbose_name_plural = _('user activities')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['activity_type', '-created_at']),
        ]

    def __str__(self):
        return f'{self.user.username} - {self.activity_type} at {self.created_at}'


class AdminAuditLog(models.Model):
    """
    Audit log for admin actions to track who did what and when.
    Critical for security monitoring and accountability.
    """

    class ActionType(models.TextChoices):
        USER_TRUSTED = 'user_trusted', _('Granted Trusted Status')
        USER_UNTRUSTED = 'user_untrusted', _('Revoked Trusted Status')
        USER_MODERATOR = 'user_moderator', _('Granted Moderator Status')
        USER_UNMODERATOR = 'user_unmoderator', _('Revoked Moderator Status')
        USER_SUSPENDED = 'user_suspended', _('Suspended User')
        USER_UNSUSPENDED = 'user_unsuspended', _('Unsuspended User')
        MESSAGING_BLOCKED = 'messaging_blocked', _('Blocked User Messaging')
        MESSAGING_UNBLOCKED = 'messaging_unblocked', _('Unblocked User Messaging')
        PRODUCT_APPROVED = 'product_approved', _('Approved Product')
        PRODUCT_UNAPPROVED = 'product_unapproved', _('Unapproved Product')
        PRODUCT_FEATURED = 'product_featured', _('Featured Product')
        SUBMISSION_APPROVED = 'submission_approved', _('Approved Submission')
        SUBMISSION_REJECTED = 'submission_rejected', _('Rejected Submission')
        COMPONENT_VERIFIED = 'component_verified', _('Verified Component')
        REPORT_RESOLVED = 'report_resolved', _('Resolved Report')
        OTHER = 'other', _('Other Action')

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    admin_user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='admin_actions',
        help_text=_('Admin who performed the action')
    )
    action_type = models.CharField(
        max_length=30,
        choices=ActionType.choices
    )
    target_model = models.CharField(
        max_length=100,
        help_text=_('Model type affected (e.g., User, Product)')
    )
    target_id = models.CharField(
        max_length=100,
        help_text=_('ID of the affected object')
    )
    target_repr = models.CharField(
        max_length=255,
        blank=True,
        help_text=_('String representation of the target at action time')
    )
    details = models.JSONField(
        default=dict,
        blank=True,
        help_text=_('Additional action details and changes made')
    )
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _('admin audit log')
        verbose_name_plural = _('admin audit logs')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['admin_user', '-created_at']),
            models.Index(fields=['action_type', '-created_at']),
            models.Index(fields=['target_model', 'target_id']),
        ]

    def __str__(self):
        return f'{self.admin_user} - {self.action_type} - {self.target_repr}'

    @classmethod
    def log_action(cls, request, action_type, target, details=None):
        """
        Helper method to log an admin action.

        Args:
            request: The HTTP request object
            action_type: ActionType enum value
            target: The object being acted upon
            details: Optional dict of additional details
        """
        ip_address = None
        if request:
            x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
            if x_forwarded_for:
                ip_address = x_forwarded_for.split(',')[0].strip()
            else:
                ip_address = request.META.get('REMOTE_ADDR')

        return cls.objects.create(
            admin_user=request.user if request and request.user.is_authenticated else None,
            action_type=action_type,
            target_model=target.__class__.__name__,
            target_id=str(target.pk),
            target_repr=str(target)[:255],
            details=details or {},
            ip_address=ip_address,
        )
