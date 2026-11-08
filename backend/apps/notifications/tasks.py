"""
Celery tasks for the notifications app -- Web Push delivery.
"""
import json
import logging

from celery import shared_task
from django.conf import settings

logger = logging.getLogger(__name__)

# pywebpush defaults ttl=0, which per the Web Push protocol (RFC 8030) means
# "deliver right now or discard" -- if the device isn't actively connected to
# the push service at that exact instant (common on mobile), the push service
# silently drops the message instead of queuing it. Give it real time to land.
PUSH_TTL_SECONDS = 4 * 60 * 60  # 4 hours


@shared_task
def send_push_to_user(notification_id):
    """Fan a Notification out to every PushSubscription its recipient has."""
    from .models import Notification, PushSubscription

    try:
        notification = Notification.objects.select_related('recipient').get(pk=notification_id)
    except Notification.DoesNotExist:
        return

    if not settings.VAPID_PRIVATE_KEY:
        logger.info('VAPID keys not configured; skipping web push for notification %s', notification_id)
        return

    from apps.notifications.models import Notification as NotificationModel
    unread_count = NotificationModel.objects.filter(recipient=notification.recipient, is_read=False).count()

    payload = json.dumps({
        'title': notification.title,
        'body': notification.body,
        'url': notification.url,
        'unreadCount': unread_count,
    })

    subscriptions = PushSubscription.objects.filter(user=notification.recipient)
    for sub in subscriptions:
        _send_one(sub, payload)


def _send_one(subscription, payload):
    from pywebpush import webpush, WebPushException

    try:
        response = webpush(
            subscription_info={
                'endpoint': subscription.endpoint,
                'keys': {'p256dh': subscription.p256dh, 'auth': subscription.auth},
            },
            data=payload,
            vapid_private_key=settings.VAPID_PRIVATE_KEY,
            vapid_claims=dict(settings.VAPID_CLAIMS),
            ttl=PUSH_TTL_SECONDS,
            headers={'Urgency': 'high'},
        )
        logger.info(
            'Web push sent for subscription %s: push-service status %s',
            subscription.id, getattr(response, 'status_code', 'unknown'),
        )
    except WebPushException as e:
        status_code = getattr(e.response, 'status_code', None)
        if status_code in (404, 410):
            # Subscription expired/unsubscribed on the browser side -- clean it up.
            subscription.delete()
        else:
            logger.warning('Web push failed for subscription %s: %s', subscription.id, e)


# A mail provider caps how many messages an account sends per minute/hour; one email per user
# per run keeps moderation from using up the allowance that sign-up verification mail needs.
REVIEW_DIGEST_MAX_EMAILS = 40       # users mailed per run; the rest go out on the next run
REVIEW_EMAIL_KEEP_DAYS = 30


@shared_task
def send_review_email_digests():
    """Email each user one summary of their approved/rejected contributions queued since the
    last run (beat: every 5 minutes)."""
    import datetime

    from django.db import transaction
    from django.utils import timezone

    from utils.email import send_review_digest_email

    from .models import ReviewEmail

    user_ids = list(ReviewEmail.objects.filter(sent_at__isnull=True)
                    .order_by('user_id').values_list('user_id', flat=True).distinct()[:REVIEW_DIGEST_MAX_EMAILS])
    sent = 0
    for user_id in user_ids:
        with transaction.atomic():
            items = list(ReviewEmail.objects.select_for_update(skip_locked=True)
                         .select_related('user').filter(user_id=user_id, sent_at__isnull=True))
            if not items:
                continue
            user = items[0].user
            if user.email:
                try:
                    send_review_digest_email(user, [i for i in items if i.approved],
                                             [i for i in items if not i.approved])
                except Exception:
                    logger.exception('review digest to user %s failed; retrying next run', user_id)
                    continue
                sent += 1
            ReviewEmail.objects.filter(pk__in=[i.pk for i in items]).update(sent_at=timezone.now())
    ReviewEmail.objects.filter(
        sent_at__lt=timezone.now() - datetime.timedelta(days=REVIEW_EMAIL_KEEP_DAYS)).delete()
    return sent
