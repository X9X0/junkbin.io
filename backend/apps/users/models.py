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
