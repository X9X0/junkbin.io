"""
Central entry point for creating notifications. Every hook point elsewhere
in the codebase (messaging, reports, submissions, products) should call
`notify()` rather than creating Notification rows directly, so "create the
row" and "fan out a push" never drift apart.
"""
from .models import Notification
from .tasks import send_push_to_user


def notify(recipient, category, title, body='', url='', actor=None):
    """Create a Notification for `recipient` and asynchronously push it."""
    if actor is not None and actor == recipient:
        # Don't notify someone about their own action (e.g. commenting on
        # your own product, or a moderator resolving their own report).
        return None

    notification = Notification.objects.create(
        recipient=recipient,
        actor=actor,
        category=category,
        title=title,
        body=body,
        url=url,
    )
    send_push_to_user.delay(str(notification.id))
    return notification


def notify_staff(users, category, title, body='', url='', actor=None):
    """Convenience wrapper for fanning a notification out to several
    staff/moderator users (e.g. "new report filed")."""
    return [
        notify(user, category, title=title, body=body, url=url, actor=actor)
        for user in users
    ]
