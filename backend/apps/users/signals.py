"""
User signals for Junkbin.io

Handles user-related events like email verification and profile creation.
"""
from django.db.models.signals import post_save
from django.dispatch import receiver
from allauth.account.signals import email_confirmed

from .models import User


@receiver(email_confirmed)
def email_confirmed_handler(request, email_address, **kwargs):
    """Update user when email is confirmed."""
    from django.utils import timezone

    user = email_address.user
    user.email_verified = True
    user.email_verified_at = timezone.now()
    user.save(update_fields=['email_verified', 'email_verified_at'])


@receiver(post_save, sender=User)
def user_post_save(sender, instance, created, **kwargs):
    """Handle post-save actions for users."""
    if created:
        # Initialize default preferences
        if not instance.preferences:
            instance.preferences = {
                'email_notifications': True,
                'notify_messages': True,
                'notify_submissions': True,
                'notify_reports': True,
                'notify_account': True,
                'dark_mode': True,
                'show_advanced_fields': False,
            }
            instance.save(update_fields=['preferences'])
