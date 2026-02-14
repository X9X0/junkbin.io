"""
Celery tasks for junkbin app.
"""
from celery import shared_task


@shared_task
def match_want_lists(junkbin_item_id):
    """
    When a 'have' item is set to available + public, check if any users
    want it and send notification emails.
    """
    from django.core.mail import send_mail
    from django.conf import settings

    from .models import JunkbinItem

    try:
        item = JunkbinItem.objects.select_related(
            'user', 'content_type'
        ).get(pk=junkbin_item_id)
    except JunkbinItem.DoesNotExist:
        return

    # Only match for public+available "have" items
    if item.item_type != 'have' or item.status != 'available' or item.visibility != 'public':
        return

    # Find matching want-list items from other users
    matches = JunkbinItem.objects.select_related('user').filter(
        content_type=item.content_type,
        object_id=item.object_id,
        item_type='want',
    ).exclude(user=item.user)

    for match in matches:
        recipient = match.user
        if not recipient.email:
            continue

        # Respect email preferences
        prefs = getattr(recipient, 'preferences', None) or {}
        if not prefs.get('email_notifications', True):
            continue
        if not prefs.get('notify_junkbin', True):
            continue

        target = item.content_object
        item_name = str(target) if target else 'an item'
        frontend_url = getattr(settings, 'FRONTEND_URL', '')
        owner_profile_url = f"{frontend_url}/users/{item.user.username}"

        send_mail(
            subject=f'[Junkbin.io] {item_name} is now available for trade!',
            message=(
                f'Hi {recipient.username},\n\n'
                f'{item.user.username} just listed "{item_name}" as available '
                f'for trade on Junkbin.io — and it\'s on your want list!\n\n'
                f'View their profile: {owner_profile_url}\n\n'
                f'— Junkbin.io'
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[recipient.email],
            fail_silently=True,
        )
