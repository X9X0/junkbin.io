"""
Celery tasks for user notifications.
"""
from celery import shared_task


@shared_task
def notify_contribution_reviewed(user_id, content_type, content_str, content_url, approved, notes='',
                                 reviewer_id=None):
    """Notify a user that a product/schematic/image/recipe/etc. they contributed was reviewed
    (not when they reviewed it themselves: reviewer_id)."""
    if reviewer_id is not None and str(reviewer_id) == str(user_id):
        return
    from django.contrib.auth import get_user_model
    from utils.email import send_contribution_approved_email, send_contribution_rejected_email

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
    if not prefs.get('notify_submissions', True):
        return

    if approved:
        send_contribution_approved_email(user, content_type, content_str, content_url)
    else:
        send_contribution_rejected_email(user, content_type, content_str, notes)
