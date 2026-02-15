"""
Celery tasks for admin notifications.
"""
import logging
from datetime import timedelta

from celery import shared_task
from django.core.cache import cache
from django.utils import timezone

logger = logging.getLogger(__name__)

# Cooldown durations in seconds
COOLDOWNS = {
    'system_health': 1800,       # 30 minutes
    'system_performance': 1800,
    'task_failure': 3600,        # 1 hour
    'new_submission': 21600,     # 6 hours
    'new_report': 21600,
    'new_user_review': 0,        # always send (rare, important)
    'new_member': 86400,         # 24 hours
    'new_subscriber': 86400,
    'new_content': 86400,
}


def _get_recipients(category):
    """Get email addresses of admins who have this category enabled."""
    from .models import NotificationPreference
    prefs = NotificationPreference.objects.filter(
        enabled=True,
    ).select_related('user')
    return [
        p.user.email
        for p in prefs
        if p.user.email and p.is_enabled_for(category)
    ]


def _check_cooldown(category, identifier='default'):
    """Return True if notification should be suppressed (within cooldown)."""
    cooldown = COOLDOWNS.get(category, 0)
    if cooldown == 0:
        return False
    key = f'notif_cd:{category}:{identifier}'
    if cache.get(key):
        return True
    cache.set(key, 1, cooldown)
    return False


def _log_notification(category, subject, recipients, status='sent', error=''):
    """Record a notification in the log."""
    try:
        from .models import NotificationLog
        NotificationLog.objects.create(
            category=category,
            subject=subject,
            recipients=recipients,
            status=status,
            error_message=error,
        )
    except Exception as e:
        logger.error('Failed to log notification: %s', e)


def _send(category, subject, template_name, context, identifier='default'):
    """Core notification sender with cooldown and logging."""
    if _check_cooldown(category, identifier):
        logger.debug('Notification %s:%s suppressed by cooldown', category, identifier)
        return

    recipients = _get_recipients(category)
    if not recipients:
        return

    try:
        from utils.email import send_templated_email
        send_templated_email(
            subject=f'[Junkbin Admin] {subject}',
            template_name=f'admin/{template_name}',
            context=context,
            recipient_list=recipients,
        )
        _log_notification(category, subject, recipients)
        logger.info('Sent %s notification to %d recipients', category, len(recipients))
    except Exception as e:
        logger.error('Failed to send %s notification: %s', category, e)
        _log_notification(category, subject, recipients, status='failed', error=str(e))


# ---------------------------------------------------------------------------
# Periodic tasks
# ---------------------------------------------------------------------------

@shared_task(name='apps.api.tasks.check_system_health')
def check_system_health():
    """Check service health and alert on state transitions (OK → error)."""
    from .admin_views import (
        _check_database, _check_redis, _check_celery, _check_celery_beat,
        _get_system_metrics,
    )

    checks = {
        'PostgreSQL': _check_database(),
        'Redis': _check_redis(),
        'Celery Workers': _check_celery(),
        'Celery Beat': _check_celery_beat(),
    }

    # Load previous state from cache
    prev_state = cache.get('notif_prev_health', {})
    new_failures = {}

    for name, result in checks.items():
        was_ok = prev_state.get(name, 'ok') == 'ok'
        is_bad = result['status'] != 'ok'
        if is_bad and was_ok:
            new_failures[name] = result['detail']

    # Save current state
    cache.set('notif_prev_health', {
        name: result['status'] for name, result in checks.items()
    }, 600)  # 10 min TTL

    if new_failures:
        _send(
            'system_health',
            f'Service Alert: {", ".join(new_failures.keys())}',
            'system_alert',
            {'failed_services': new_failures, 'all_checks': checks},
            identifier='health',
        )

    # Performance checks
    try:
        metrics = _get_system_metrics()
        exceeded = {}
        threshold = 80
        if metrics['cpu']['percent'] > threshold:
            exceeded['CPU'] = f"{metrics['cpu']['percent']}%"
        if metrics['memory']['percent'] > threshold:
            exceeded['Memory'] = f"{metrics['memory']['percent']}% ({metrics['memory']['used']} / {metrics['memory']['total']})"
        if metrics['disk']['percent'] > threshold:
            exceeded['Disk'] = f"{metrics['disk']['percent']}% ({metrics['disk']['used']} / {metrics['disk']['total']})"

        if exceeded:
            _send(
                'system_performance',
                f'Performance Alert: {", ".join(exceeded.keys())} high',
                'system_alert',
                {'exceeded_metrics': exceeded, 'metrics': metrics},
                identifier='performance',
            )
    except Exception as e:
        logger.error('Performance check failed: %s', e)


@shared_task(name='apps.api.tasks.send_daily_digest')
def send_daily_digest():
    """Send daily activity digest to admins who opted in."""
    from django.conf import settings as django_settings
    from .models import NotificationPreference
    from .admin_views import (
        _check_database, _check_redis, _check_celery, _check_celery_beat,
        _get_system_metrics,
    )
    from apps.users.models import User
    from apps.newsletter.models import Subscriber
    from apps.products.models import Product
    from apps.components.models import Component
    from apps.submissions.models import Submission
    from apps.reports.models import Report, UserReview

    since = timezone.now() - timedelta(hours=24)

    summary = {
        'new_users': User.objects.filter(date_joined__gte=since, is_staff=False).count(),
        'new_subscribers': Subscriber.objects.filter(created_at__gte=since).count(),
        'new_products': Product.objects.filter(created_at__gte=since).count(),
        'new_components': Component.objects.filter(created_at__gte=since).count(),
        'pending_submissions': Submission.objects.filter(status='pending').count(),
        'pending_reports': Report.objects.filter(status='pending').count(),
        'pending_reviews': UserReview.objects.filter(status='pending').count(),
    }

    # Gather system health status
    services = {
        'PostgreSQL': _check_database(),
        'Redis': _check_redis(),
        'Celery Workers': _check_celery(),
        'Celery Beat': _check_celery_beat(),
    }

    try:
        metrics = _get_system_metrics()
    except Exception:
        metrics = None

    prefs = NotificationPreference.objects.filter(
        enabled=True, digest_mode=True,
    ).select_related('user')
    recipients = [p.user.email for p in prefs if p.user.email]
    if not recipients:
        return

    # Build dashboard URL from settings
    frontend_url = getattr(django_settings, 'FRONTEND_URL', 'https://junkbin.io')
    admin_url = getattr(django_settings, 'ADMIN_URL', 'admin/')
    dashboard_url = f"{frontend_url}/{admin_url}system-status/"

    try:
        from utils.email import send_templated_email
        send_templated_email(
            subject='[Junkbin Admin] Daily Activity Digest',
            template_name='admin/activity_digest',
            context={
                'summary': summary,
                'period': '24 hours',
                'services': services,
                'metrics': metrics,
                'dashboard_url': dashboard_url,
            },
            recipient_list=recipients,
        )
        _log_notification('new_content', 'Daily Activity Digest', recipients)
    except Exception as e:
        logger.error('Failed to send daily digest: %s', e)
        _log_notification('new_content', 'Daily Activity Digest', recipients,
                          status='failed', error=str(e))


# ---------------------------------------------------------------------------
# Event-triggered tasks
# ---------------------------------------------------------------------------

@shared_task(name='apps.api.tasks.notify_new_user')
def notify_new_user(user_id):
    """Notify admins of a new user registration."""
    from apps.users.models import User
    try:
        user = User.objects.get(pk=user_id)
    except User.DoesNotExist:
        return
    _send(
        'new_member',
        f'New member: {user.username}',
        'moderation_alert',
        {'event': 'New Member Registration', 'detail': f'{user.username} ({user.email})',
         'item_type': 'user', 'created_at': user.date_joined},
        identifier='new_member',
    )


@shared_task(name='apps.api.tasks.notify_new_subscriber')
def notify_new_subscriber(subscriber_id):
    """Notify admins of a new newsletter subscriber."""
    from apps.newsletter.models import Subscriber
    try:
        sub = Subscriber.objects.get(pk=subscriber_id)
    except Subscriber.DoesNotExist:
        return
    _send(
        'new_subscriber',
        f'New subscriber: {sub.email}',
        'moderation_alert',
        {'event': 'Newsletter Subscription', 'detail': sub.email,
         'item_type': 'subscriber', 'created_at': sub.created_at},
        identifier='new_subscriber',
    )


@shared_task(name='apps.api.tasks.notify_new_product')
def notify_new_product(product_id):
    """Notify admins of a new product added."""
    from apps.products.models import Product
    try:
        product = Product.objects.get(pk=product_id)
    except Product.DoesNotExist:
        return
    _send(
        'new_content',
        f'New product: {product.manufacturer} {product.model_number}',
        'moderation_alert',
        {'event': 'New Product Added',
         'detail': f'{product.manufacturer} {product.model_number}',
         'item_type': 'product', 'created_at': product.created_at},
        identifier='new_content',
    )


@shared_task(name='apps.api.tasks.notify_new_component')
def notify_new_component(component_id):
    """Notify admins of a new component added."""
    from apps.components.models import Component
    try:
        component = Component.objects.get(pk=component_id)
    except Component.DoesNotExist:
        return
    _send(
        'new_content',
        f'New component: {component.manufacturer} {component.part_number}',
        'moderation_alert',
        {'event': 'New Component Added',
         'detail': f'{component.manufacturer} {component.part_number}',
         'item_type': 'component', 'created_at': component.created_at},
        identifier='new_content',
    )


@shared_task(name='apps.api.tasks.notify_pending_submission')
def notify_pending_submission(submission_id):
    """Notify admins of a new submission needing review."""
    from apps.submissions.models import Submission
    try:
        sub = Submission.objects.select_related('submitted_by', 'product').get(pk=submission_id)
    except Submission.DoesNotExist:
        return
    submitter = sub.submitted_by.username if sub.submitted_by else 'Unknown'
    product = f'{sub.product.manufacturer} {sub.product.model_number}' if sub.product else 'N/A'
    _send(
        'new_submission',
        f'Submission pending review: {sub.get_submission_type_display()}',
        'moderation_alert',
        {'event': 'Submission Pending Review',
         'detail': f'{sub.get_submission_type_display()} by {submitter} for {product}',
         'item_type': 'submission', 'created_at': sub.submitted_at},
        identifier='submission',
    )


@shared_task(name='apps.api.tasks.notify_new_report')
def notify_new_report(report_id):
    """Notify admins of a new user report."""
    from apps.reports.models import Report
    try:
        report = Report.objects.select_related('reporter').get(pk=report_id)
    except Report.DoesNotExist:
        return
    reporter = report.reporter.username if report.reporter else 'Anonymous'
    _send(
        'new_report',
        f'New report: {report.get_reason_display()}',
        'moderation_alert',
        {'event': 'New Report Filed',
         'detail': f'{report.get_reason_display()} — reported by {reporter}',
         'item_type': 'report', 'created_at': report.created_at},
        identifier='report',
    )


@shared_task(name='apps.api.tasks.notify_new_user_review')
def notify_new_user_review(review_id):
    """Notify admins of a new automatic user review (3-strike threshold)."""
    from apps.reports.models import UserReview
    try:
        review = UserReview.objects.select_related('user').get(pk=review_id)
    except UserReview.DoesNotExist:
        return
    _send(
        'new_user_review',
        f'User review triggered: {review.user.username}',
        'moderation_alert',
        {'event': 'Automatic User Review',
         'detail': f'{review.user.username} has {review.trigger_report_count} strikes',
         'item_type': 'user_review', 'created_at': review.created_at},
        identifier=f'review_{review_id}',
    )


@shared_task(name='apps.api.tasks.notify_task_failure')
def notify_task_failure(task_name, exception, traceback_str=''):
    """Notify admins of a Celery task failure."""
    _send(
        'task_failure',
        f'Task failed: {task_name}',
        'system_alert',
        {'failed_services': {}, 'all_checks': {},
         'task_error': {'name': task_name, 'exception': exception,
                        'traceback': traceback_str[:1000]}},
        identifier=f'task_{task_name}',
    )


# ---------------------------------------------------------------------------
# Analytics cleanup tasks
# ---------------------------------------------------------------------------

@shared_task(name='apps.api.tasks.cleanup_old_search_queries')
def cleanup_old_search_queries():
    """Delete search query logs older than 90 days."""
    from .models import SearchQuery as SearchQueryLog
    cutoff = timezone.now() - timedelta(days=90)
    deleted, _ = SearchQueryLog.objects.filter(created_at__lt=cutoff).delete()
    logger.info('Cleaned up %d old search queries', deleted)
    return deleted


@shared_task(name='apps.api.tasks.cleanup_old_activity')
def cleanup_old_activity():
    """Delete user activity logs older than 180 days."""
    from apps.users.models import UserActivity
    cutoff = timezone.now() - timedelta(days=180)
    deleted, _ = UserActivity.objects.filter(created_at__lt=cutoff).delete()
    logger.info('Cleaned up %d old activity records', deleted)
    return deleted
