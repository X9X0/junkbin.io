"""
Celery tasks for reports app.
"""
from celery import shared_task


@shared_task
def notify_user_strike(user_id):
    """Notify a user that they received a strike."""
    from django.contrib.auth import get_user_model
    from utils.email import send_strike_warning_email

    User = get_user_model()

    try:
        user = User.objects.get(pk=user_id)
    except User.DoesNotExist:
        return

    if not user.email:
        return

    # Respect email notification preferences
    prefs = getattr(user, 'preferences', None) or {}
    if not prefs.get('email_notifications', True):
        return
    if not prefs.get('notify_reports', True):
        return

    send_strike_warning_email(user)


@shared_task
def notify_account_action(review_id):
    """Notify a user about an account action (warning, restriction, suspension)."""
    from .models import UserReview
    from utils.email import send_account_action_email

    try:
        review = UserReview.objects.select_related('user').get(pk=review_id)
    except UserReview.DoesNotExist:
        return

    if not review.user.email:
        return

    # Respect email notification preferences
    prefs = getattr(review.user, 'preferences', None) or {}
    if not prefs.get('email_notifications', True):
        return
    if not prefs.get('notify_account', True):
        return

    # Only notify for actionable outcomes
    if review.status not in (
        UserReview.Status.WARNING_ISSUED,
        UserReview.Status.RESTRICTED,
        UserReview.Status.SUSPENDED,
    ):
        return

    send_account_action_email(review)
