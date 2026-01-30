"""
Component models for Junkbin.io

Models for electronic components and their relationships to products.
"""
import uuid
from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _


class Component(models.Model):
    """
    Represents an electronic component (IC, transistor, capacitor, etc.)
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    # Part identification
    part_number = models.CharField(
        max_length=200,
        db_index=True,
        help_text=_('Manufacturer part number')
    )
    manufacturer = models.CharField(
        max_length=200,
        db_index=True,
        help_text=_('Component manufacturer')
    )
    manufacturer_aliases = models.JSONField(
        default=list,
        blank=True,
        help_text=_('Alternative manufacturer names')
    )

    # Classification
    component_type = models.CharField(
        max_length=50,
        choices=settings.COMPONENT_TYPES,
        db_index=True,
        help_text=_('Type of component')
    )
    package_type = models.CharField(
        max_length=50,
        blank=True,
        help_text=_('Package type (SOT-23, SOIC-8, 0805, etc.)')
    )

    # Description and function
    description = models.TextField(
        blank=True,
        help_text=_('Component description')
    )
    typical_function = models.CharField(
        max_length=200,
        blank=True,
        help_text=_('Typical application (voltage regulator, MCU, etc.)')
    )

    # Technical specifications (stored as JSON for flexibility)
    specifications = models.JSONField(
        default=dict,
        blank=True,
        help_text=_('Technical specifications')
    )

    # External references
    datasheet_url = models.URLField(
        blank=True,
        help_text=_('Link to datasheet')
    )
    octopart_url = models.URLField(
        blank=True,
        help_text=_('Octopart listing URL')
    )

    # Cross-references (equivalent parts from other manufacturers)
    cross_references = models.ManyToManyField(
        'self',
        blank=True,
        symmetrical=True,
        help_text=_('Equivalent parts')
    )

    # Alternative part numbers for the same component
    alternative_part_numbers = models.JSONField(
        default=list,
        blank=True,
        help_text=_('Alternative part numbers for this component')
    )

    # Metadata
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_components'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Moderation
    is_verified = models.BooleanField(
        default=False,
        help_text=_('Component information has been verified')
    )

    # Statistics
    usage_count = models.PositiveIntegerField(
        default=0,
        help_text=_('Number of products containing this component')
    )

    class Meta:
        verbose_name = _('component')
        verbose_name_plural = _('components')
        ordering = ['manufacturer', 'part_number']
        indexes = [
            models.Index(fields=['part_number']),
            models.Index(fields=['manufacturer', 'part_number']),
            models.Index(fields=['component_type', '-usage_count']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['manufacturer', 'part_number'],
                name='unique_component'
            )
        ]

    def __str__(self):
        return f'{self.manufacturer} {self.part_number}'

    def update_usage_count(self):
        """Update the denormalized usage count."""
        self.usage_count = self.product_components.count()
        self.save(update_fields=['usage_count'])


class ProductComponent(models.Model):
    """
    Junction table linking products to components.

    Tracks where components are located on products and additional details.
    """

    class SubmissionLevel(models.TextChoices):
        BASIC = 'basic', _('Basic (Major Components)')
        ADVANCED = 'advanced', _('Advanced (Complete BOM)')

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    product = models.ForeignKey(
        'products.Product',
        on_delete=models.CASCADE,
        related_name='product_components'
    )
    component = models.ForeignKey(
        Component,
        on_delete=models.CASCADE,
        related_name='product_components'
    )

    # Location on PCB
    reference_designator = models.CharField(
        max_length=20,
        blank=True,
        help_text=_('Reference designator (U1, R5, C12, etc.)')
    )
    quantity = models.PositiveSmallIntegerField(
        default=1,
        help_text=_('Number of this component on the board')
    )
    location_description = models.CharField(
        max_length=200,
        blank=True,
        help_text=_('Description of location (near HDMI port, on power board, etc.)')
    )
    board_name = models.CharField(
        max_length=100,
        blank=True,
        help_text=_('Name of the PCB if product has multiple boards')
    )

    # Notes and additional info
    notes = models.TextField(
        blank=True,
        help_text=_('Additional notes about this component in this product')
    )

    # Reference to image showing this component
    image_reference = models.ForeignKey(
        'products.ProductImage',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text=_('Image showing this component')
    )

    # Submission level
    submission_level = models.CharField(
        max_length=20,
        choices=SubmissionLevel.choices,
        default=SubmissionLevel.BASIC,
        help_text=_('Level of detail for this entry')
    )

    # Metadata
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_product_components'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Verification
    is_verified = models.BooleanField(
        default=False,
        help_text=_('This component mapping has been verified')
    )
    verified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='verified_product_components'
    )
    verified_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = _('product component')
        verbose_name_plural = _('product components')
        ordering = ['reference_designator', 'component__part_number']
        indexes = [
            models.Index(fields=['product', 'component']),
            models.Index(fields=['component', 'is_verified']),
        ]

    def __str__(self):
        if self.reference_designator:
            return f'{self.product} - {self.reference_designator}: {self.component}'
        return f'{self.product} - {self.component}'

    def save(self, *args, **kwargs):
        is_new = self._state.adding
        super().save(*args, **kwargs)

        # Update denormalized counts
        if is_new:
            self.product.update_component_count()
            self.component.update_usage_count()

    def delete(self, *args, **kwargs):
        product = self.product
        component = self.component
        super().delete(*args, **kwargs)

        # Update denormalized counts
        product.update_component_count()
        component.update_usage_count()
