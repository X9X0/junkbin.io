"""
Celery configuration for Junkbin.io

This module configures Celery for async task processing.
"""
import os

from celery import Celery

# Set the default Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.production')

app = Celery('junkbin')

# Load configuration from Django settings
app.config_from_object('django.conf:settings', namespace='CELERY')

# Auto-discover tasks from installed apps
app.autodiscover_tasks()


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    """Debug task for testing Celery configuration."""
    print(f'Request: {self.request!r}')


# Notify admins on Celery task failures
from celery.signals import task_failure as task_failure_signal


@task_failure_signal.connect
def on_task_failure(sender=None, task_id=None, exception=None,
                    traceback=None, **kwargs):
    """Forward Celery task failures to the notification system."""
    task_name = sender.name if sender else 'unknown'
    # Skip notification task failures to avoid recursion
    if task_name.startswith('apps.api.tasks.notify_'):
        return
    try:
        from apps.api.tasks import notify_task_failure
        notify_task_failure.delay(
            task_name,
            str(exception),
            str(traceback)[:1000] if traceback else '',
        )
    except Exception:
        pass
