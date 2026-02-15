"""
Recipe Celery tasks for Junkbin.io
"""
from celery import shared_task


@shared_task
def notify_recipe_approved(recipe_id):
    """Send email notification when a recipe is approved."""
    from django.core.mail import send_mail
    from django.conf import settings
    from .models import Recipe

    try:
        recipe = Recipe.objects.select_related('created_by').get(pk=recipe_id)
    except Recipe.DoesNotExist:
        return

    user = recipe.created_by
    if not user or not user.email:
        return

    # Check user notification preferences
    prefs = user.preferences or {}
    if not prefs.get('notify_submissions', True):
        return

    send_mail(
        subject=f'Your recipe "{recipe.name}" has been approved!',
        message=(
            f'Hi {user.username},\n\n'
            f'Your recipe "{recipe.name}" has been reviewed and approved. '
            f'It is now visible to all users on Junkbin.io.\n\n'
            f'View it at: {settings.FRONTEND_URL}/recipes/{recipe.id}\n\n'
            f'Thank you for your contribution!\n'
            f'- The Junkbin.io Team'
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        fail_silently=True,
    )
