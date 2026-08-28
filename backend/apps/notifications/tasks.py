"""
Celery tasks for the notifications app -- Web Push delivery.
"""
import json
import logging

from celery import shared_task
from django.conf import settings

logger = logging.getLogger(__name__)


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
        webpush(
            subscription_info={
                'endpoint': subscription.endpoint,
                'keys': {'p256dh': subscription.p256dh, 'auth': subscription.auth},
            },
            data=payload,
            vapid_private_key=settings.VAPID_PRIVATE_KEY,
            vapid_claims=dict(settings.VAPID_CLAIMS),
        )
    except WebPushException as e:
        status_code = getattr(e.response, 'status_code', None)
        if status_code in (404, 410):
            # Subscription expired/unsubscribed on the browser side -- clean it up.
            subscription.delete()
        else:
            logger.warning('Web push failed for subscription %s: %s', subscription.id, e)
