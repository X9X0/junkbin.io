"""
Celery tasks for webhook delivery with retry and rate-limit awareness.
"""
import logging

import requests
from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task
def dispatch_webhook_event(event_type, context):
    """
    Fan out a single event to all matching active endpoints.

    Called from views/badges when an event occurs. Queries the DB for
    matching WebhookEndpoints and queues a deliver_webhook task for each.
    """
    from .models import WebhookEndpoint
    from .formatters import build_payload

    endpoints = WebhookEndpoint.objects.filter(is_active=True)

    for endpoint in endpoints:
        if event_type not in (endpoint.events or []):
            continue

        try:
            payload = build_payload(endpoint.platform, event_type, context)
        except Exception:
            logger.exception(
                'Failed to build payload for %s → %s', event_type, endpoint.name
            )
            continue

        deliver_webhook.delay(str(endpoint.pk), event_type, payload)


@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def deliver_webhook(self, endpoint_id, event_type, payload):
    """
    POST a payload to a webhook URL and log the attempt.

    Handles 429 rate limiting with Retry-After header.
    Retries up to 3 times with exponential backoff.
    """
    from .models import WebhookEndpoint, WebhookDelivery

    try:
        endpoint = WebhookEndpoint.objects.get(pk=endpoint_id)
    except WebhookEndpoint.DoesNotExist:
        logger.warning('Webhook endpoint %s not found, skipping', endpoint_id)
        return

    status_code = None
    response_body = ''
    success = False

    try:
        resp = requests.post(
            endpoint.url,
            json=payload,
            headers={'Content-Type': 'application/json'},
            timeout=10,
        )
        status_code = resp.status_code
        response_body = resp.text[:500]

        # Discord returns 204, Slack returns 200 with "ok"
        if status_code in (200, 204):
            success = True
        elif status_code == 429:
            retry_after = int(resp.headers.get('Retry-After', 60))
            logger.warning(
                'Rate limited on %s, retrying after %ds', endpoint.name, retry_after
            )
            raise self.retry(countdown=retry_after)
        else:
            logger.warning(
                'Webhook %s returned %d: %s', endpoint.name, status_code, response_body[:200]
            )

    except requests.RequestException as exc:
        response_body = str(exc)[:500]
        logger.exception('Webhook delivery failed for %s', endpoint.name)
        raise self.retry(exc=exc, countdown=30 * (2 ** self.request.retries))

    finally:
        WebhookDelivery.objects.create(
            endpoint=endpoint,
            event_type=event_type,
            payload=payload,
            status_code=status_code,
            response_body=response_body,
            success=success,
        )
