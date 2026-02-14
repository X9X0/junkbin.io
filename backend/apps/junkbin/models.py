"""
Junkbin models for Junkbin.io

Personal collection management — tracks items users have and want.
"""
import uuid

from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.utils.translation import gettext_lazy as _


class JunkbinItem(models.Model):
    """
    A single item in a user's personal junkbin.

    Covers both "have" (items they own) and "want" (items they're looking for).
    Uses ContentType for polymorphic references to Product or Component.
    """

    ITEM_TYPE_CHOICES = [
        ('have', 'Have'),
        ('want', 'Want'),
    ]
    STATUS_CHOICES = [
        ('available', 'Available for Trade'),
        ('not_for_trade', 'Not for Trade'),
    ]
    CONDITION_CHOICES = [
        ('new', 'New'),
        ('working', 'Working'),
        ('broken', 'Broken / For Parts'),
        ('unknown', 'Unknown'),
    ]
    VISIBILITY_CHOICES = [
        ('public', 'Public'),
        ('private', 'Private'),
    ]

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='junkbin_items'
    )

    # Polymorphic reference to Product or Component
    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        limit_choices_to={'model__in': ('product', 'component')}
    )
    object_id = models.UUIDField()
    content_object = GenericForeignKey('content_type', 'object_id')

    item_type = models.CharField(
        max_length=4,
        choices=ITEM_TYPE_CHOICES,
        help_text=_('Whether user has or wants this item')
    )
    status = models.CharField(
        max_length=15,
        choices=STATUS_CHOICES,
        default='not_for_trade',
        help_text=_('Trade availability (only for "have" items)')
    )
    condition = models.CharField(
        max_length=10,
        choices=CONDITION_CHOICES,
        default='unknown',
        help_text=_('Item condition (only for "have" items)')
    )
    visibility = models.CharField(
        max_length=7,
        choices=VISIBILITY_CHOICES,
        default='public',
        help_text=_('Whether this item is publicly visible')
    )
    notes = models.TextField(
        blank=True,
        max_length=500,
        help_text=_('Optional notes about this item')
    )
    quantity = models.PositiveIntegerField(
        default=1,
        help_text=_('Number of units')
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('junkbin item')
        verbose_name_plural = _('junkbin items')
        ordering = ['-created_at']
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'content_type', 'object_id', 'item_type'],
                name='unique_junkbin_item'
            )
        ]
        indexes = [
            models.Index(fields=['user', 'item_type']),
            models.Index(fields=['content_type', 'object_id']),
        ]

    def __str__(self):
        return f'{self.user.username} - {self.get_item_type_display()} - {self.content_object}'
