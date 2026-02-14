"""
Email utilities for Junkbin.io
"""
from datetime import datetime

from django.core.mail import send_mail, EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings


def send_templated_email(
    subject,
    template_name,
    context,
    recipient_list,
    from_email=None
):
    """
    Send an email using a template.

    Args:
        subject: Email subject
        template_name: Base template name (without extension)
        context: Template context dictionary
        recipient_list: List of recipient email addresses
        from_email: Sender email (defaults to DEFAULT_FROM_EMAIL)
    """
    from_email = from_email or settings.DEFAULT_FROM_EMAIL

    # Add common context
    context['site_name'] = 'Junkbin.io'
    context['site_url'] = settings.SITE_URL if hasattr(settings, 'SITE_URL') else ''
    context['tagline'] = 'NO USER SERVICEABLE PARTS INSIDE'
    context['year'] = datetime.now().year

    # Render templates
    text_content = render_to_string(f'emails/{template_name}.txt', context)
    html_content = render_to_string(f'emails/{template_name}.html', context)

    # Create email
    email = EmailMultiAlternatives(
        subject=subject,
        body=text_content,
        from_email=from_email,
        to=recipient_list
    )
    email.attach_alternative(html_content, 'text/html')

    return email.send()


def send_welcome_email(user):
    """Send welcome email to new users."""
    return send_templated_email(
        subject='Welcome to Junkbin.io!',
        template_name='welcome',
        context={'user': user},
        recipient_list=[user.email]
    )


def send_submission_approved_email(submission):
    """Send email when a submission is approved."""
    if not submission.submitted_by or not submission.submitted_by.email:
        return

    return send_templated_email(
        subject='Your Junkbin.io submission has been approved!',
        template_name='submission_approved',
        context={
            'user': submission.submitted_by,
            'submission': submission
        },
        recipient_list=[submission.submitted_by.email]
    )


def send_submission_rejected_email(submission):
    """Send email when a submission is rejected."""
    if not submission.submitted_by or not submission.submitted_by.email:
        return

    return send_templated_email(
        subject='Your Junkbin.io submission needs attention',
        template_name='submission_rejected',
        context={
            'user': submission.submitted_by,
            'submission': submission
        },
        recipient_list=[submission.submitted_by.email]
    )


def send_report_resolved_email(report):
    """Send email when a user's report is resolved."""
    if not report.reporter or not report.reporter.email:
        return

    return send_templated_email(
        subject='Your Junkbin.io report has been resolved',
        template_name='report_resolved',
        context={
            'user': report.reporter,
            'report': report
        },
        recipient_list=[report.reporter.email]
    )


def generate_email_verification_token(user):
    """Generate a signed token for email verification."""
    from django.core import signing
    return signing.dumps({'user_id': str(user.pk), 'email': user.email}, salt='email-verification')


def verify_email_token(token, max_age=86400):
    """
    Verify an email verification token.

    Args:
        token: The signed token
        max_age: Token validity in seconds (default 24 hours)

    Returns:
        dict with user_id and email if valid, None otherwise
    """
    from django.core import signing
    try:
        return signing.loads(token, salt='email-verification', max_age=max_age)
    except signing.BadSignature:
        return None


def send_verification_email(user):
    """
    Send email verification link to new users.

    Args:
        user: User object
    """
    from django.conf import settings

    token = generate_email_verification_token(user)
    verify_url = f"{settings.FRONTEND_URL}/verify-email/{token}"

    return send_templated_email(
        subject='Verify your Junkbin.io email',
        template_name='email_verification',
        context={
            'user': user,
            'verify_url': verify_url,
        },
        recipient_list=[user.email]
    )


def send_new_message_email(message, recipient):
    """Send email notification for a new message."""
    from django.conf import settings

    conversation_url = f"{settings.FRONTEND_URL}/messages/{message.conversation_id}"
    preview = message.content[:200]

    return send_templated_email(
        subject=f'[Junkbin.io] New message from {message.sender.username}',
        template_name='new_message',
        context={
            'user': recipient,
            'sender': message.sender,
            'message_preview': preview,
            'conversation_url': conversation_url,
        },
        recipient_list=[recipient.email]
    )


def send_strike_warning_email(user):
    """Send email notifying a user they received a strike."""
    from django.conf import settings

    guidelines_url = f"{settings.FRONTEND_URL}/guidelines"

    return send_templated_email(
        subject='[Junkbin.io] You have received a community strike',
        template_name='strike_warning',
        context={
            'user': user,
            'strike_count': user.report_count,
            'guidelines_url': guidelines_url,
        },
        recipient_list=[user.email]
    )


def send_account_action_email(review):
    """Send email notifying a user about an account action."""
    from django.conf import settings

    guidelines_url = f"{settings.FRONTEND_URL}/guidelines"
    action_labels = {
        'warning_issued': 'Warning Issued',
        'restricted': 'Account Restricted',
        'suspended': 'Account Suspended',
    }

    return send_templated_email(
        subject=f'[Junkbin.io] Account action: {action_labels.get(review.status, review.status)}',
        template_name='account_action',
        context={
            'user': review.user,
            'action_label': action_labels.get(review.status, review.status),
            'status': review.status,
            'notes': review.notes,
            'guidelines_url': guidelines_url,
        },
        recipient_list=[review.user.email]
    )


def send_password_reset_email(user, token, uid):
    """
    Send password reset email with reset link.

    Args:
        user: User object
        token: Password reset token
        uid: URL-safe base64 encoded user ID
    """
    from django.conf import settings

    reset_url = f"{settings.FRONTEND_URL}/reset-password/{uid}/{token}"

    return send_templated_email(
        subject='Reset your Junkbin.io password',
        template_name='password_reset',
        context={
            'user': user,
            'reset_url': reset_url,
        },
        recipient_list=[user.email]
    )
