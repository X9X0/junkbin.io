"""
Signal handlers for admin notifications.
"""
import logging

from django.db.models.signals import post_save
from django.dispatch import receiver

logger = logging.getLogger(__name__)


@receiver(post_save, sender='users.User')
def on_user_created(sender, instance, created, **kwargs):
    if created and instance.is_staff:
        from .models import NotificationPreference
        NotificationPreference.objects.get_or_create(user=instance)
    if created and not instance.is_staff:
        from .tasks import notify_new_user
        notify_new_user.delay(str(instance.id))


@receiver(post_save, sender='newsletter.Subscriber')
def on_subscriber_created(sender, instance, created, **kwargs):
    if created:
        from .tasks import notify_new_subscriber
        notify_new_subscriber.delay(str(instance.id))


@receiver(post_save, sender='products.Product')
def on_product_created(sender, instance, created, **kwargs):
    if created:
        from .tasks import notify_new_product
        notify_new_product.delay(str(instance.id))


@receiver(post_save, sender='components.Component')
def on_component_created(sender, instance, created, **kwargs):
    if created:
        from .tasks import notify_new_component
        notify_new_component.delay(str(instance.id))


@receiver(post_save, sender='submissions.Submission')
def on_submission_pending(sender, instance, created, **kwargs):
    if instance.status == 'pending':
        from .tasks import notify_pending_submission
        notify_pending_submission.delay(str(instance.id))


@receiver(post_save, sender='reports.Report')
def on_report_created(sender, instance, created, **kwargs):
    if created:
        from .tasks import notify_new_report
        notify_new_report.delay(str(instance.id))


@receiver(post_save, sender='reports.UserReview')
def on_user_review_created(sender, instance, created, **kwargs):
    if created:
        from .tasks import notify_new_user_review
        notify_new_user_review.delay(str(instance.id))
