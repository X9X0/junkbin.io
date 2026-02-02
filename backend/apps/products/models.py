"""
Product models for Junkbin.io

Models for documenting consumer electronics products and their images.
"""
import uuid
from django.db import models
from django.conf import settings
from django.core.validators import FileExtensionValidator
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _
from imagekit.models import ImageSpecField
from imagekit.processors import ResizeToFill, ResizeToFit


# Allowed file extensions for uploads
ALLOWED_SCHEMATIC_EXTENSIONS = ['pdf', 'png', 'jpg', 'jpeg', 'gif', 'webp', 'svg']
ALLOWED_IMAGE_EXTENSIONS = ['png', 'jpg', 'jpeg', 'gif', 'webp']


def product_image_path(instance, filename):
    """Generate upload path for product images."""
    ext = filename.split('.')[-1]
    new_filename = f'{uuid.uuid4().hex}.{ext}'
    return f'products/{instance.product.id}/{new_filename}'


class Product(models.Model):
    """
    Represents a consumer electronics product with teardown documentation.
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    # Basic identification
    manufacturer = models.CharField(
        max_length=200,
        db_index=True,
        help_text=_('Product manufacturer (e.g., Samsung, Sony)')
    )
    model_number = models.CharField(
        max_length=200,
        db_index=True,
        help_text=_('Model number or name')
    )
    revision = models.CharField(
        max_length=50,
        blank=True,
        help_text=_('Hardware revision if applicable')
    )
    region = models.CharField(
        max_length=20,
        choices=settings.REGIONS,
        default='global',
        help_text=_('Region variant')
    )

    # Classification
    category = models.CharField(
        max_length=50,
        choices=settings.PRODUCT_CATEGORIES,
        db_index=True,
        help_text=_('Product category')
    )
    subcategory = models.CharField(
        max_length=100,
        blank=True,
        help_text=_('Optional subcategory')
    )

    # Additional info
    year_manufactured = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        help_text=_('Manufacturing year')
    )
    fcc_id = models.CharField(
        max_length=50,
        blank=True,
        db_index=True,
        help_text=_('FCC ID for US devices')
    )
    ic_id = models.CharField(
        max_length=50,
        blank=True,
        help_text=_('IC ID for Canadian devices')
    )
    part_number = models.CharField(
        max_length=100,
        blank=True,
        help_text=_('Manufacturer part number')
    )

    # Description
    description = models.TextField(
        blank=True,
        help_text=_('Product description and notes')
    )
    teardown_notes = models.TextField(
        blank=True,
        help_text=_('Notes about the teardown process')
    )

    # URL slug for SEO-friendly URLs
    slug = models.SlugField(
        max_length=300,
        unique=True,
        blank=True
    )

    # Metadata
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_products'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Moderation status
    is_approved = models.BooleanField(
        default=False,
        help_text=_('Whether product has been approved by moderator')
    )
    is_featured = models.BooleanField(
        default=False,
        help_text=_('Featured on homepage')
    )

    # Statistics (denormalized for performance)
    component_count = models.PositiveIntegerField(
        default=0,
        help_text=_('Number of documented components')
    )
    view_count = models.PositiveIntegerField(
        default=0,
        help_text=_('Number of times viewed')
    )

    class Meta:
        verbose_name = _('product')
        verbose_name_plural = _('products')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['manufacturer', 'model_number']),
            models.Index(fields=['category', '-created_at']),
            models.Index(fields=['is_approved', '-created_at']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['manufacturer', 'model_number', 'revision', 'region'],
                name='unique_product_variant'
            )
        ]

    def __str__(self):
        parts = [self.manufacturer, self.model_number]
        if self.revision:
            parts.append(f'Rev {self.revision}')
        if self.region != 'global':
            parts.append(f'({self.region.upper()})')
        return ' '.join(parts)

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(f'{self.manufacturer}-{self.model_number}')
            if self.revision:
                base_slug = f'{base_slug}-{slugify(self.revision)}'
            if self.region != 'global':
                base_slug = f'{base_slug}-{self.region}'

            # Ensure uniqueness
            slug = base_slug
            counter = 1
            while Product.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f'{base_slug}-{counter}'
                counter += 1
            self.slug = slug

        super().save(*args, **kwargs)

    @property
    def primary_image(self):
        """Return the primary/overview image."""
        return self.images.filter(image_type='overview').first()

    def increment_view_count(self):
        """Increment view count (use F() to avoid race conditions)."""
        from django.db.models import F
        Product.objects.filter(pk=self.pk).update(view_count=F('view_count') + 1)

    def update_component_count(self):
        """Update denormalized component count."""
        self.component_count = self.product_components.count()
        self.save(update_fields=['component_count'])


class ProductImage(models.Model):
    """
    Images associated with a product (PCB photos, overviews, etc.)
    """

    class ImageType(models.TextChoices):
        OVERVIEW = 'overview', _('Overview/Box')
        PCB_TOP = 'pcb_top', _('PCB Top Side')
        PCB_BOTTOM = 'pcb_bottom', _('PCB Bottom Side')
        CLOSEUP = 'closeup', _('Close-up Detail')
        LABEL = 'label', _('Label/Sticker')
        INTERNAL = 'internal', _('Internal View')
        SCHEMATIC = 'schematic', _('Schematic')
        OTHER = 'other', _('Other')

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='images'
    )

    # Image file
    image = models.ImageField(
        upload_to=product_image_path,
        help_text=_('High-resolution product image'),
        validators=[FileExtensionValidator(allowed_extensions=ALLOWED_IMAGE_EXTENSIONS)]
    )

    # Generated thumbnails
    thumbnail = ImageSpecField(
        source='image',
        processors=[ResizeToFill(300, 300)],
        format='JPEG',
        options={'quality': 85}
    )
    medium = ImageSpecField(
        source='image',
        processors=[ResizeToFit(800, 800)],
        format='JPEG',
        options={'quality': 90}
    )

    # Metadata
    image_type = models.CharField(
        max_length=20,
        choices=ImageType.choices,
        default=ImageType.OVERVIEW
    )
    caption = models.CharField(
        max_length=500,
        blank=True,
        help_text=_('Image caption or description')
    )
    display_order = models.PositiveSmallIntegerField(
        default=0,
        help_text=_('Order in image gallery')
    )

    # Upload info
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='uploaded_images'
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)

    # Image dimensions (auto-populated)
    width = models.PositiveIntegerField(null=True, blank=True)
    height = models.PositiveIntegerField(null=True, blank=True)
    file_size = models.PositiveIntegerField(null=True, blank=True)

    class Meta:
        verbose_name = _('product image')
        verbose_name_plural = _('product images')
        ordering = ['display_order', 'uploaded_at']

    def __str__(self):
        return f'{self.product} - {self.get_image_type_display()}'

    def save(self, *args, **kwargs):
        # Auto-populate image dimensions
        if self.image and not self.width:
            try:
                self.width = self.image.width
                self.height = self.image.height
                self.file_size = self.image.size
            except Exception:
                pass
        super().save(*args, **kwargs)


def schematic_file_path(instance, filename):
    """Generate upload path for schematic files."""
    ext = filename.split('.')[-1]
    new_filename = f'{uuid.uuid4().hex}.{ext}'
    return f'schematics/{instance.product.id}/{new_filename}'


class Schematic(models.Model):
    """
    Schematics and service documentation for products.

    Supports PDFs, images, and other technical documentation that aids
    in the Right to Repair movement.
    """

    class SchematicType(models.TextChoices):
        FULL_SCHEMATIC = 'full_schematic', _('Full Schematic')
        BLOCK_DIAGRAM = 'block_diagram', _('Block Diagram')
        PCB_LAYOUT = 'pcb_layout', _('PCB Layout')
        SERVICE_MANUAL = 'service_manual', _('Service Manual')
        DATASHEET = 'datasheet', _('Component Datasheet')
        PINOUT = 'pinout', _('Pinout Diagram')
        WIRING_DIAGRAM = 'wiring_diagram', _('Wiring Diagram')
        BOM = 'bom', _('Bill of Materials')
        OTHER = 'other', _('Other Documentation')

    class SourceType(models.TextChoices):
        OFFICIAL = 'official', _('Official/Manufacturer')
        COMMUNITY = 'community', _('Community Contributed')
        REVERSE_ENGINEERED = 'reverse_engineered', _('Reverse Engineered')
        FCC_FILING = 'fcc_filing', _('FCC Filing')
        LEAKED = 'leaked', _('Leaked Document')
        UNKNOWN = 'unknown', _('Unknown Source')

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='schematics'
    )

    # File
    file = models.FileField(
        upload_to=schematic_file_path,
        help_text=_('Schematic file (PDF, PNG, JPG, etc.)'),
        validators=[FileExtensionValidator(allowed_extensions=ALLOWED_SCHEMATIC_EXTENSIONS)]
    )
    file_type = models.CharField(
        max_length=20,
        blank=True,
        help_text=_('File extension/type')
    )
    file_size = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text=_('File size in bytes')
    )

    # Metadata
    schematic_type = models.CharField(
        max_length=30,
        choices=SchematicType.choices,
        default=SchematicType.FULL_SCHEMATIC
    )
    title = models.CharField(
        max_length=300,
        help_text=_('Descriptive title for this schematic')
    )
    description = models.TextField(
        blank=True,
        help_text=_('Additional details about this schematic')
    )
    version = models.CharField(
        max_length=50,
        blank=True,
        help_text=_('Version or revision of the schematic')
    )
    page_count = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        help_text=_('Number of pages (for PDFs)')
    )

    # Source attribution
    source_type = models.CharField(
        max_length=30,
        choices=SourceType.choices,
        default=SourceType.COMMUNITY
    )
    source_url = models.URLField(
        blank=True,
        help_text=_('URL where this schematic was obtained')
    )
    source_notes = models.TextField(
        blank=True,
        help_text=_('Attribution and source information')
    )

    # Right to Repair context
    repair_relevance = models.TextField(
        blank=True,
        help_text=_('How this schematic helps with repairs')
    )

    # Upload info
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='uploaded_schematics'
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Moderation
    is_approved = models.BooleanField(
        default=False,
        help_text=_('Whether schematic has been verified/approved')
    )

    # Statistics
    download_count = models.PositiveIntegerField(
        default=0,
        help_text=_('Number of times downloaded')
    )

    class Meta:
        verbose_name = _('schematic')
        verbose_name_plural = _('schematics')
        ordering = ['schematic_type', '-uploaded_at']
        indexes = [
            models.Index(fields=['product', 'schematic_type']),
            models.Index(fields=['is_approved', '-uploaded_at']),
        ]

    def __str__(self):
        return f'{self.product} - {self.title}'

    def save(self, *args, **kwargs):
        # Auto-populate file info
        if self.file:
            if not self.file_type:
                self.file_type = self.file.name.split('.')[-1].lower()
            if not self.file_size:
                try:
                    self.file_size = self.file.size
                except Exception:
                    pass
        super().save(*args, **kwargs)

    def increment_download_count(self):
        """Increment download count."""
        from django.db.models import F
        Schematic.objects.filter(pk=self.pk).update(
            download_count=F('download_count') + 1
        )
