import uuid

from django.db import models


class Subscriber(models.Model):
    """Email subscriber for newsletter/launch notifications."""

    SOURCE_CHOICES = [
        ('landing', 'Landing Page'),
        ('footer', 'Footer'),
        ('popup', 'Popup'),
        ('other', 'Other'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True)
    source = models.CharField(max_length=20, choices=SOURCE_CHOICES, default='landing')
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=500, blank=True)
    is_active = models.BooleanField(default=True)
    unsubscribed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Subscriber'
        verbose_name_plural = 'Subscribers'

    def __str__(self):
        return self.email
