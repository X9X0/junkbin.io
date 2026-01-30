"""
Celery tasks for submissions app.
"""
from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings


@shared_task
def notify_submission_approved(submission_id):
    """Send notification when a submission is approved."""
    from .models import Submission

    try:
        submission = Submission.objects.select_related(
            'submitted_by', 'product'
        ).get(pk=submission_id)
    except Submission.DoesNotExist:
        return

    if not submission.submitted_by or not submission.submitted_by.email:
        return

    subject = f'[Junkbin.io] Your submission has been approved!'
    message = f'''
Hello {submission.submitted_by.username},

Your {submission.get_submission_type_display().lower()} submission has been approved.

{'Product: ' + str(submission.product) if submission.product else ''}

Thank you for contributing to the Junkbin.io community!

- The Junkbin.io Team

"NO USER SERVICEABLE PARTS INSIDE" - We took that personally.
'''

    send_mail(
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL,
        [submission.submitted_by.email],
        fail_silently=True,
    )


@shared_task
def notify_submission_rejected(submission_id):
    """Send notification when a submission is rejected."""
    from .models import Submission

    try:
        submission = Submission.objects.select_related(
            'submitted_by', 'product'
        ).get(pk=submission_id)
    except Submission.DoesNotExist:
        return

    if not submission.submitted_by or not submission.submitted_by.email:
        return

    subject = f'[Junkbin.io] Submission needs attention'
    message = f'''
Hello {submission.submitted_by.username},

Your {submission.get_submission_type_display().lower()} submission was not approved.

{f'Reviewer notes: {submission.review_notes}' if submission.review_notes else ''}

Please review the feedback and consider resubmitting with corrections.

- The Junkbin.io Team
'''

    send_mail(
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL,
        [submission.submitted_by.email],
        fail_silently=True,
    )


@shared_task
def cleanup_old_draft_submissions():
    """Remove draft submissions older than 30 days."""
    from django.utils import timezone
    from datetime import timedelta
    from .models import Submission

    cutoff = timezone.now() - timedelta(days=30)
    deleted_count, _ = Submission.objects.filter(
        status='draft',
        submitted_at__lt=cutoff
    ).delete()

    return f'Deleted {deleted_count} old draft submissions'
