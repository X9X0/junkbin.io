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


REVIEW_NOTES_MAX = 2000


def review_notes(request):
    """A moderator's feedback sent with an approve/reject ('notes' in the body)."""
    return str(request.data.get('notes') or '').strip()[:REVIEW_NOTES_MAX]


def notify_content_review(user, content_label, url, approved, notes='', actor=None):
    """In-app + push notification for a moderator's approve/reject; pairs with
    the notify_contribution_reviewed email task. Nothing is sent when the
    moderator (actor) reviews their own item."""
    if not user:
        return
    if approved:
        notify(user, Notification.Category.CONTENT_APPROVED,
               title=f'{content_label} approved', body=notes, url=url, actor=actor)
    else:
        notify(user, Notification.Category.CONTENT_REJECTED,
               title=f'{content_label} rejected', body=notes, url=url, actor=actor)
