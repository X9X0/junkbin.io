"""
Webhook models for Discord/Slack notification delivery.
"""
import uuid

from django.db import models
from django.utils.translation import gettext_lazy as _


class WebhookEndpoint(models.Model):
    """An admin-configured webhook destination (Discord or Slack channel)."""

    class Platform(models.TextChoices):
        DISCORD = 'discord', _('Discord')
        SLACK = 'slack', _('Slack')

    EVENT_TYPES = [
        ('product.created', 'Product Created'),
        ('schematic.uploaded', 'Schematic Uploaded'),
        ('report.filed', 'Report Filed'),
        ('user.badge_earned', 'User Badge Earned'),
        ('recipe.created', 'Recipe Created'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(
        max_length=200,
        help_text=_('Friendly name, e.g. "#new-products channel"'),
    )
    platform = models.CharField(max_length=10, choices=Platform.choices)
    url = models.URLField(
        help_text=_('The webhook URL (token is embedded in the URL)'),
    )
    events = models.JSONField(
        default=list,
        help_text=_('List of event type strings to subscribe to'),
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('webhook endpoint')
        verbose_name_plural = _('webhook endpoints')
        ordering = ['name']

    def __str__(self):
        return f'{self.name} ({self.get_platform_display()})'


class WebhookDelivery(models.Model):
    """Log of a single webhook delivery attempt."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    endpoint = models.ForeignKey(
        WebhookEndpoint,
        on_delete=models.CASCADE,
        related_name='deliveries',
    )
    event_type = models.CharField(max_length=50)
    payload = models.JSONField()
    status_code = models.IntegerField(null=True, blank=True)
    response_body = models.TextField(blank=True)
    success = models.BooleanField(default=False)
    attempted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _('webhook delivery')
        verbose_name_plural = _('webhook deliveries')
        ordering = ['-attempted_at']
        indexes = [
            models.Index(fields=['endpoint', '-attempted_at']),
        ]

    def __str__(self):
        status = 'OK' if self.success else f'FAIL ({self.status_code})'
        return f'{self.event_type} → {self.endpoint.name} [{status}]'
