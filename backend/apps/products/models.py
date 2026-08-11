"""
Product models for Junkbin.io

Models for documenting consumer electronics products and their images.
"""
import uuid
from django.db import models
from django.conf import settings
from django.contrib.postgres.indexes import GinIndex
from django.contrib.postgres.search import SearchVector, SearchVectorField
from django.core.validators import FileExtensionValidator
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _
from imagekit.models import ImageSpecField
from imagekit.processors import ResizeToFill, ResizeToFit
from PIL import Image


class AlphaToBlack:
    """ImageKit processor that composites transparent images onto a black background."""

    def process(self, image):
        if image.mode in ('RGBA', 'P', 'LA'):
            if image.mode == 'P':
                image = image.convert('RGBA')
            background = Image.new('RGB', image.size, (0, 0, 0))
            background.paste(image, mask=image.split()[-1])
            return background
        return image


class AdaptiveThumbnail:
    """
    ImageKit processor for product thumbnails.

    Hard-crops to fill the target box when the source is reasonably close to
    the target aspect ratio, which looks natural. Photos with a much
    different aspect ratio (tall portrait shots, wide panorama/box scans,
    etc.) would have a hard crop zoom in on a thin sliver of the subject, so
    those are letterboxed onto a padded canvas instead, keeping the whole
    photo visible.
    """

    def __init__(self, width, height, max_ratio_deviation=0.2, pad_color=(10, 10, 15)):
        # 0.2 keeps common photography ratios (3:2, 5:4) hard-cropped, but pushes
        # square (1:1) images into letterbox — 1:1 vs. this class's 480x360 (4:3)
        # target deviates ~0.25, which used to sit just under a 0.3 threshold and
        # still got hard-cropped, clipping the subject on square vendor/stock photos.
        self.width = width
        self.height = height
        self.max_ratio_deviation = max_ratio_deviation
        self.pad_color = pad_color

    def process(self, image):
        target_ratio = self.width / self.height
        src_ratio = image.width / image.height
        deviation = abs(src_ratio - target_ratio) / target_ratio

        if deviation <= self.max_ratio_deviation:
            return ResizeToFill(self.width, self.height).process(image)

        fitted = ResizeToFit(self.width, self.height).process(image)
        canvas = Image.new('RGB', (self.width, self.height), self.pad_color)
        offset = ((self.width - fitted.width) // 2, (self.height - fitted.height) // 2)
        canvas.paste(fitted, offset)
        return canvas


# Allowed file extensions for uploads
ALLOWED_SCHEMATIC_EXTENSIONS = ['pdf', 'png', 'jpg', 'jpeg', 'jfif', 'gif', 'webp', 'svg']
ALLOWED_IMAGE_EXTENSIONS = ['png', 'jpg', 'jpeg', 'jfif', 'gif', 'webp', 'avif']
ALLOWED_FIRMWARE_EXTENSIONS = ['bin', 'hex', 'rom', 'img', 'dump', 'fw', 'elf', 'zip']


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

    # Full-text search vector (auto-updated on save)
    search_vector = SearchVectorField(null=True, editable=False)

    class Meta:
        verbose_name = _('product')
        verbose_name_plural = _('products')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['manufacturer', 'model_number']),
            models.Index(fields=['category', '-created_at']),
            models.Index(fields=['is_approved', '-created_at']),
            GinIndex(fields=['search_vector']),
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

        # Update search vector after save (uses SQL so needs pk)
        Product.objects.filter(pk=self.pk).update(
            search_vector=(
                SearchVector('manufacturer', weight='A') +
                SearchVector('model_number', weight='A') +
                SearchVector('fcc_id', weight='B') +
                SearchVector('description', weight='C') +
                SearchVector('teardown_notes', weight='D')
            )
        )

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
        PORTS = 'ports', _('Ports/Connectors')
        DAMAGE = 'damage', _('Damage/Issue')
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
        processors=[AlphaToBlack(), AdaptiveThumbnail(480, 360)],
        format='JPEG',
        options={'quality': 85}
    )
    medium = ImageSpecField(
        source='image',
        processors=[AlphaToBlack(), ResizeToFit(800, 800)],
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

    # Moderation
    is_approved = models.BooleanField(
        default=False,
        help_text=_('Whether image has been approved by moderator')
    )

    class Meta:
        verbose_name = _('product image')
        verbose_name_plural = _('product images')
        ordering = ['display_order', 'uploaded_at']
        indexes = [
            models.Index(fields=['is_approved', '-uploaded_at']),
        ]

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
        USER_MANUAL = 'user_manual', _('User Manual')
        DATASHEET = 'datasheet', _('Component Datasheet')
        PINOUT = 'pinout', _('Pinout Diagram')
        WIRING_DIAGRAM = 'wiring_diagram', _('Wiring Diagram')
        BOM = 'bom', _('Bill of Materials')
        OTHER = 'other', _('Other Documentation')

    # Schematic types worth running text/table BOM extraction on - i.e. ones
    # that plausibly contain an actual parts list. Circuit diagrams (full
    # schematic, block diagram, PCB layout, wiring diagram) don't have BOM
    # tables to find; their components are drawn symbols with designator
    # labels scattered spatially across the page, which needs the separate
    # OCR + spatial-matching pipeline instead of text/table extraction.
    BOM_EXTRACTABLE_TYPES = {'service_manual', 'bom'}

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

    # BOM extraction tracking (see ComponentSuggestion / extract_bom action) -
    # null means never processed; set on every run (even zero-candidate ones)
    # so a batch sweep doesn't keep reprocessing the same document.
    bom_extracted_at = models.DateTimeField(null=True, blank=True)

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


def firmware_file_path(instance, filename):
    """Generate upload path for firmware files."""
    ext = filename.split('.')[-1]
    new_filename = f'{uuid.uuid4().hex}.{ext}'
    return f'firmware/{instance.product.id}/{new_filename}'


class Firmware(models.Model):
    """
    Recovered/dumped firmware binaries for products.

    Preserving firmware images lets owners re-flash devices bricked by a
    failed OTA update or a swapped flash chip - part of the Right to
    Repair movement.
    """

    class SourceType(models.TextChoices):
        OFFICIAL = 'official', _('Official/Manufacturer Release')
        DUMPED = 'dumped', _('Dumped from Device')
        COMMUNITY = 'community', _('Community Contributed')
        REVERSE_ENGINEERED = 'reverse_engineered', _('Reverse Engineered')
        LEAKED = 'leaked', _('Leaked')
        UNKNOWN = 'unknown', _('Unknown Source')

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='firmware_files'
    )

    # File
    file = models.FileField(
        upload_to=firmware_file_path,
        help_text=_('Firmware binary (BIN, HEX, ROM, IMG, etc.)'),
        validators=[FileExtensionValidator(allowed_extensions=ALLOWED_FIRMWARE_EXTENSIONS)]
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
    title = models.CharField(
        max_length=300,
        help_text=_('Descriptive title for this firmware')
    )
    description = models.TextField(
        blank=True,
        help_text=_('Additional details about this firmware')
    )
    version = models.CharField(
        max_length=50,
        blank=True,
        help_text=_('Firmware version')
    )
    chip_architecture = models.CharField(
        max_length=100,
        blank=True,
        help_text=_('Chip or architecture this firmware targets (e.g. ESP32, ARM Cortex-M4)')
    )

    # Source attribution
    source_type = models.CharField(
        max_length=30,
        choices=SourceType.choices,
        default=SourceType.DUMPED
    )
    source_url = models.URLField(
        blank=True,
        help_text=_('URL where this firmware was obtained')
    )
    source_notes = models.TextField(
        blank=True,
        help_text=_('Attribution, extraction method, and source information')
    )

    # Upload info
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='uploaded_firmware'
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Moderation
    is_approved = models.BooleanField(
        default=False,
        help_text=_('Whether firmware has been verified/approved')
    )

    # Statistics
    download_count = models.PositiveIntegerField(
        default=0,
        help_text=_('Number of times downloaded')
    )

    class Meta:
        verbose_name = _('firmware')
        verbose_name_plural = _('firmware')
        ordering = ['-uploaded_at']
        indexes = [
            models.Index(fields=['product', '-uploaded_at']),
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
        Firmware.objects.filter(pk=self.pk).update(
            download_count=F('download_count') + 1
        )


def suggestion_source_path(instance, filename):
    """Generate upload path for the source document behind a component suggestion."""
    ext = filename.split('.')[-1]
    new_filename = f'{uuid.uuid4().hex}.{ext}'
    return f'component_suggestions/{instance.product.id}/{new_filename}'


class ComponentSuggestion(models.Model):
    """
    A machine-extracted candidate component, pending moderator review.

    Populated by parsing a manual/service-doc PDF, OCR-scanning a circuit
    diagram, or (in future) OCR of PCB photos. Never linked into the live
    parts list directly - a moderator must approve it, at which point a
    real Component + ProductComponent pair is created from its data.
    """

    class SourceType(models.TextChoices):
        PDF_MANUAL = 'pdf_manual', _('PDF Manual/Service Doc')
        SCHEMATIC_OCR = 'schematic_ocr', _('Schematic OCR')
        PHOTO_OCR = 'photo_ocr', _('PCB Photo OCR')

    class Confidence(models.TextChoices):
        HIGH = 'high', _('High (table extraction)')
        MEDIUM = 'medium', _('Medium')
        LOW = 'low', _('Low (heuristic text match)')

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='component_suggestions'
    )

    # Source
    source_type = models.CharField(
        max_length=20,
        choices=SourceType.choices,
        default=SourceType.PDF_MANUAL
    )
    source_file = models.FileField(
        upload_to=suggestion_source_path,
        null=True,
        blank=True,
        help_text=_('The manual/document this was extracted from')
    )
    page_number = models.PositiveIntegerField(null=True, blank=True)
    extraction_context = models.TextField(
        blank=True,
        help_text=_('Raw extracted row/line, for moderator sanity-checking')
    )
    confidence = models.CharField(
        max_length=10,
        choices=Confidence.choices,
        default=Confidence.MEDIUM
    )

    # Extracted candidate data (mirrors ProductComponent + Component fields)
    part_number = models.CharField(max_length=200, blank=True)
    manufacturer = models.CharField(max_length=200, blank=True)
    reference_designator = models.CharField(max_length=255, blank=True)
    component_type = models.CharField(max_length=50, blank=True)
    package_type = models.CharField(max_length=50, blank=True)
    description = models.CharField(max_length=500, blank=True)
    value_raw = models.CharField(max_length=100, blank=True)
    quantity = models.PositiveSmallIntegerField(default=1)
    location_description = models.CharField(max_length=200, blank=True)

    # Best-effort match against the existing Component catalog
    matched_component = models.ForeignKey(
        'components.Component',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='+'
    )

    # Upload info
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='uploaded_component_suggestions'
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)

    # Moderation - approving converts this into a real ProductComponent and
    # deletes the suggestion; rejecting just deletes it. is_approved stays
    # False for the lifetime of every row still in the table, but is kept
    # for consistency with the moderation queue's is_approved=False pattern.
    is_approved = models.BooleanField(default=False)

    class Meta:
        verbose_name = _('component suggestion')
        verbose_name_plural = _('component suggestions')
        ordering = ['-uploaded_at']
        indexes = [
            models.Index(fields=['product', '-uploaded_at']),
            models.Index(fields=['is_approved', '-uploaded_at']),
        ]

    def __str__(self):
        return f'{self.product} - {self.part_number or self.reference_designator or "suggestion"}'


class ProductComment(models.Model):
    """
    User comments on products — repair tips, questions, notes.
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='comments'
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='product_comments'
    )
    content = models.TextField(
        max_length=2000,
        help_text=_('Comment text (max 2000 characters)')
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('product comment')
        verbose_name_plural = _('product comments')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['product', '-created_at']),
        ]

    def __str__(self):
        return f'Comment by {self.author} on {self.product}'
