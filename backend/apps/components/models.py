"""
Component models for Junkbin.io

Models for electronic components and their relationships to products.
"""
import uuid
from django.db import models
from django.conf import settings
from django.contrib.postgres.indexes import GinIndex
from django.contrib.postgres.search import SearchVector, SearchVectorField
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

    # Full-text search vector (auto-updated on save)
    search_vector = SearchVectorField(null=True, editable=False)

    class Meta:
        verbose_name = _('component')
        verbose_name_plural = _('components')
        ordering = ['manufacturer', 'part_number']
        indexes = [
            models.Index(fields=['part_number']),
            models.Index(fields=['manufacturer', 'part_number']),
            models.Index(fields=['component_type', '-usage_count']),
            GinIndex(fields=['search_vector']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['manufacturer', 'part_number'],
                name='unique_component'
            )
        ]

    def __str__(self):
        return f'{self.manufacturer} {self.part_number}'

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # Update search vector after save (uses SQL so needs pk)
        Component.objects.filter(pk=self.pk).update(
            search_vector=(
                SearchVector('part_number', weight='A') +
                SearchVector('manufacturer', weight='A') +
                SearchVector('typical_function', weight='B') +
                SearchVector('description', weight='C')
            )
        )

    @property
    def primary_value(self):
        """Extract the main characteristic from specifications based on component type."""
        specs = self.specifications or {}
        if not specs:
            return ''

        # Map component types to their primary spec key and unit
        extraction_rules = {
            'resistor':   [('resistance_ohm', self._format_ohms)],
            'capacitor':  [('capacitance_nf', self._format_farads_from_nf),
                           ('capacitance_pf', self._format_farads_from_pf),
                           ('capacitance_uf', self._format_farads_from_uf)],
            'inductor':   [('inductance_uh', self._format_henries_from_uh),
                           ('inductance_nh', self._format_henries_from_nh)],
            'ferrite':    [('impedance_ohm', lambda v: f'{v} \u03A9 @ {specs.get("frequency_mhz", "?")} MHz')],
            'crystal':    [('frequency_mhz', lambda v: self._format_freq(v))],
            'ic':         [('frequency_ghz', lambda v: f'{v} GHz'),
                           ('frequency_mhz', lambda v: self._format_freq(v)),
                           ('speed_mbps', lambda v: f'{v} Mbps'),
                           ('capacity_gb', lambda v: f'{v} GB'),
                           ('capacity_tb', lambda v: f'{v} TB'),
                           ('channels', lambda v: f'{v}-ch'),
                           ('charge_current_a', lambda v: f'{v} A'),
                           ('cores', lambda v: f'{v}-core')],
            'mcu':        [('frequency_mhz', lambda v: f'{v} MHz'),
                           ('flash_kb', lambda v: f'{v} KB flash')],
            'regulator':  [('iout_a', lambda v: f'{v} A'),
                           ('output_a', lambda v: f'{v} A')],
            'rf_module':  [('frequency_ghz', lambda v: f'{v} GHz'),
                           ('pout_dbm', lambda v: f'{v} dBm')],
            'sensor':     [('axes', lambda v: f'{v}-axis IMU'),
                           ('frequency_khz', lambda v: f'{v} kHz')],
            'connector':  [('pins', lambda v: f'{v}-pin'),
                           ('standard', lambda v: str(v))],
            'led':        [('wavelength_nm', lambda v: f'{v} nm'),
                           ('color', lambda v: str(v))],
            'diode':      [('vf_v', lambda v: f'{v} V'),
                           ('current_a', lambda v: f'{v} A')],
            'mosfet':     [('vds_v', lambda v: f'{v} V'),
                           ('rds_mohm', lambda v: f'{v} m\u03A9')],
            'transistor': [('hfe', lambda v: f'hFE {v}'),
                           ('vce_v', lambda v: f'{v} V')],
            'battery':    [('capacity_mah', lambda v: f'{v} mAh'),
                           ('voltage_v', lambda v: f'{v} V')],
            'fuse':       [('current_a', lambda v: f'{v} A'),
                           ('voltage_v', lambda v: f'{v} V')],
            'display':    [('resolution', lambda v: str(v)),
                           ('size_in', lambda v: f'{v}"')],
            'other':      [('frequency_ghz', lambda v: f'{v} GHz'),
                           ('frequency_mhz', lambda v: self._format_freq(v))],
        }

        rules = extraction_rules.get(self.component_type, [])
        for key, formatter in rules:
            val = specs.get(key)
            if val is not None:
                return formatter(val)

        return ''

    @staticmethod
    def _format_ohms(val):
        if val >= 1_000_000:
            return f'{val / 1_000_000:g} M\u03A9'
        if val >= 1_000:
            return f'{val / 1_000:g} k\u03A9'
        return f'{val:g} \u03A9'

    @staticmethod
    def _format_farads_from_nf(val):
        if val >= 1_000:
            return f'{val / 1_000:g} \u00B5F'
        if val < 1:
            return f'{val * 1_000:g} pF'
        return f'{val:g} nF'

    @staticmethod
    def _format_farads_from_pf(val):
        if val >= 1_000_000:
            return f'{val / 1_000_000:g} \u00B5F'
        if val >= 1_000:
            return f'{val / 1_000:g} nF'
        return f'{val:g} pF'

    @staticmethod
    def _format_farads_from_uf(val):
        if val >= 1_000:
            return f'{val / 1_000:g} mF'
        return f'{val:g} \u00B5F'

    @staticmethod
    def _format_henries_from_uh(val):
        if val >= 1_000:
            return f'{val / 1_000:g} mH'
        return f'{val:g} \u00B5H'

    @staticmethod
    def _format_henries_from_nh(val):
        if val >= 1_000:
            return f'{val / 1_000:g} \u00B5H'
        return f'{val:g} nH'

    @staticmethod
    def _format_freq(val):
        if val >= 1_000:
            return f'{val / 1_000:g} GHz'
        return f'{val:g} MHz'

    def update_usage_count(self):
        """Update the denormalized usage count."""
        self.usage_count = self.product_components.count()
        self.save(update_fields=['usage_count'])


class ComponentViewStats(models.Model):
    """Daily aggregate view counts for component popularity tracking."""

    component = models.ForeignKey(
        Component,
        on_delete=models.CASCADE,
        related_name='view_stats',
    )
    date = models.DateField(db_index=True)
    view_count = models.IntegerField(default=0)

    class Meta:
        verbose_name = _('component view stats')
        verbose_name_plural = _('component view stats')
        unique_together = ['component', 'date']

    def __str__(self):
        return f'{self.component} - {self.date}: {self.view_count} views'


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
        max_length=255,
        blank=True,
        help_text=_('Reference designator(s), e.g. "U1" or "C1, C3, C8, C10"')
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

    # Denormalized vote counts
    vote_score = models.IntegerField(
        default=0,
        help_text=_('Net weighted score (confirms - disputes)')
    )
    confirm_count = models.PositiveIntegerField(
        default=0,
        help_text=_('Number of confirm votes')
    )
    dispute_count = models.PositiveIntegerField(
        default=0,
        help_text=_('Number of dispute votes')
    )
    needs_review = models.BooleanField(
        default=False,
        help_text=_('Flagged for moderator review due to disputes')
    )

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

    def recalculate_votes(self):
        """Recalculate denormalized vote counts from the votes table."""
        from django.db.models import Sum, Count, Q

        aggregates = self.votes.aggregate(
            total_score=Sum('weight', filter=Q(vote_type='confirm'), default=0)
            - Sum('weight', filter=Q(vote_type='dispute'), default=0),
            total_confirms=Count('id', filter=Q(vote_type='confirm')),
            total_disputes=Count('id', filter=Q(vote_type='dispute')),
        )

        self.vote_score = aggregates['total_score']
        self.confirm_count = aggregates['total_confirms']
        self.dispute_count = aggregates['total_disputes']
        self.save(update_fields=['vote_score', 'confirm_count', 'dispute_count'])

        self._check_verification_threshold()
        self._check_dispute_threshold()

    def _check_verification_threshold(self):
        """Auto-verify when vote_score reaches threshold."""
        from django.conf import settings as app_settings
        from django.utils import timezone

        if self.is_verified:
            return

        if self.vote_score >= app_settings.VERIFICATION_VOTE_THRESHOLD:
            self.is_verified = True
            self.verified_by = None  # None = community-verified
            self.verified_at = timezone.now()
            self.needs_review = False
            self.save(update_fields=[
                'is_verified', 'verified_by', 'verified_at', 'needs_review'
            ])

            # Award reputation bonus to confirm voters
            bonus = app_settings.VOTE_REPUTATION_BONUS
            if bonus > 0:
                from apps.users.models import User
                confirm_user_ids = self.votes.filter(
                    vote_type='confirm'
                ).values_list('user_id', flat=True)
                User.objects.filter(id__in=confirm_user_ids).update(
                    reputation_score=models.F('reputation_score') + bonus
                )

    def _check_dispute_threshold(self):
        """Flag for review when vote_score drops below threshold."""
        from django.conf import settings as app_settings

        if self.vote_score <= app_settings.DISPUTE_REVIEW_THRESHOLD:
            if not self.needs_review:
                self.needs_review = True
                self.save(update_fields=['needs_review'])
        elif self.needs_review and self.vote_score > app_settings.DISPUTE_REVIEW_THRESHOLD:
            self.needs_review = False
            self.save(update_fields=['needs_review'])


class ComponentVote(models.Model):
    """
    A user's vote on a product-component mapping.
    One vote per user per mapping.
    """

    class VoteType(models.TextChoices):
        CONFIRM = 'confirm', _('Confirm')
        DISPUTE = 'dispute', _('Dispute')

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    product_component = models.ForeignKey(
        ProductComponent,
        on_delete=models.CASCADE,
        related_name='votes'
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='component_votes'
    )
    vote_type = models.CharField(
        max_length=10,
        choices=VoteType.choices,
    )
    weight = models.PositiveSmallIntegerField(
        default=1,
        help_text=_('Vote weight, set at vote time based on trust status')
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('component vote')
        verbose_name_plural = _('component votes')
        constraints = [
            models.UniqueConstraint(
                fields=['product_component', 'user'],
                name='unique_vote_per_user'
            )
        ]
        indexes = [
            models.Index(fields=['product_component', 'vote_type']),
            models.Index(fields=['user', '-created_at']),
        ]

    def __str__(self):
        return f'{self.user} → {self.vote_type} on {self.product_component}'
