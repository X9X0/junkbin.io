"""
Report signals for Junkbin.io

Handles automatic user review triggering on 3 strikes.
"""
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.conf import settings

from .models import Report, UserReview


@receiver(post_save, sender=Report)
def check_strike_threshold(sender, instance, created, **kwargs):
    """
    Check if a user has reached the strike threshold and trigger review.
    """
    # Only check when a report is marked as valid strike
    if not instance.counted_as_strike:
        return

    if not instance.reported_user:
        return

    user = instance.reported_user
    threshold = settings.REPORT_STRIKE_THRESHOLD

    # Count valid strikes
    strike_count = Report.objects.filter(
        reported_user=user,
        counted_as_strike=True
    ).count()

    # Check if we've hit a threshold (3, 6, 9, etc.)
    if strike_count > 0 and strike_count % threshold == 0:
        # Check if there's already a review at this threshold
        existing_review = UserReview.objects.filter(
            user=user,
            trigger_report_count=strike_count
        ).exists()

        if not existing_review:
            # Create a new user review
            review = UserReview.objects.create(
                user=user,
                review_type=UserReview.ReviewType.AUTOMATIC,
                triggered_by=instance,
                trigger_report_count=strike_count
            )

            # Add recent reports for context
            recent_reports = Report.objects.filter(
                reported_user=user,
                counted_as_strike=True
            ).order_by('-created_at')[:10]

            review.related_reports.set(recent_reports)

            # In-app + push notification for moderators
            from django.contrib.auth import get_user_model
            from django.db.models import Q
            from apps.notifications.services import notify_staff
            from apps.notifications.models import Notification
            User = get_user_model()
            moderators = User.objects.filter(Q(is_staff=True) | Q(is_moderator=True))
            notify_staff(
                moderators, Notification.Category.STRIKE_REVIEW,
                title=f'Strike review needed: {user.username}',
                body=f'{user.username} has reached {strike_count} strikes.',
                url='/moderation',
            )
