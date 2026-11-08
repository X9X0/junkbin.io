"""
Celery tasks for user notifications.
"""
from celery import shared_task


@shared_task
def notify_contribution_reviewed(user_id, content_type, content_str, content_url, approved, notes='',
                                 reviewer_id=None):
    """Queue an email telling a user that a product/schematic/image/recipe/etc. they contributed
    was reviewed (not when they reviewed it themselves: reviewer_id). The emails go out batched,
    one per user, from apps.notifications.tasks.send_review_email_digests."""
    if reviewer_id is not None and str(reviewer_id) == str(user_id):
        return
    from django.contrib.auth import get_user_model
    from apps.notifications.models import ReviewEmail

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

    # Queued, not sent: send_review_email_digests mails each user one summary every few minutes
    ReviewEmail.objects.create(user=user, content_type=content_type[:50], content_str=content_str[:300],
                               content_url=(content_url or '')[:500], approved=approved, notes=notes or '')
