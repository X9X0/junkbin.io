"""
Celery tasks for messaging app.
"""
from celery import shared_task


@shared_task
def notify_new_message(message_id):
    """Send email notification for a new message."""
    from .models import Message
    from utils.email import send_new_message_email

    try:
        message = Message.objects.select_related(
            'conversation__participant_1',
            'conversation__participant_2',
            'sender',
        ).get(pk=message_id)
    except Message.DoesNotExist:
        return

    if not message.sender:
        return

    # Determine recipient
    recipient = message.conversation.other_participant(message.sender)
    if not recipient or not recipient.email:
        return

    # Skip if message already read (user was online)
    if message.is_read:
        return

    # Respect user email notification preferences
    prefs = getattr(recipient, 'preferences', None) or {}
    if not prefs.get('email_notifications', True):
        return
    if not prefs.get('notify_messages', True):
        return

    send_new_message_email(message, recipient)
