"""
Media tools models for Junkbin.io

BackgroundRemovalPreview serves two flows:

1. Pre-submission preview (upload -> auto-remove -> compare/tweak ->
   decide) in ImageUpload.tsx. `product_image`/`component_image` are
   both null here - nothing in the preview is ever the image actually
   attached to a listing; the frontend uploads whichever version
   (original or result) the user lands on through the normal
   image-upload endpoints. These rows are pure scratch space, swept up
   by cleanup_bg_removal_previews once they're a few hours old.

2. Retroactive moderator apply-to-existing-image (see apps.media_tools.
   views.apply/revert) - `product_image` or `component_image` is set,
   `original` is a server-side copy of that image's content *before*
   any change, and once /apply/ has run, `applied_at` is set and the
   row becomes the undo record for that change (excluded from routine
   cleanup - see cleanup_bg_removal_previews).
"""
import uuid

from django.conf import settings
from django.core.validators import FileExtensionValidator
from django.db import models

from apps.products.models import ALLOWED_IMAGE_EXTENSIONS
from .bg_removal import MODEL_CHOICES, DEFAULT_MODEL


def bg_removal_upload_path(instance, filename):
    ext = filename.split('.')[-1]
    return f'bg_removal_previews/{instance.id}/{filename.rsplit(".", 1)[0]}.{ext}'


class BackgroundRemovalPreview(models.Model):
    """A single upload's background-removal preview/retry workspace."""

    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        DONE = 'done', 'Done'
        FAILED = 'failed', 'Failed'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='bg_removal_previews',
    )

    original = models.ImageField(
        upload_to=bg_removal_upload_path,
        validators=[FileExtensionValidator(allowed_extensions=ALLOWED_IMAGE_EXTENSIONS)],
    )
    result = models.ImageField(upload_to=bg_removal_upload_path, null=True, blank=True)

    # Set only for the retroactive moderator flow - which existing image
    # this preview was created from / will be (or was) applied to. At
    # most one of these is set; both null means a plain pre-submission
    # preview (flow 1 above).
    product_image = models.ForeignKey(
        'products.ProductImage', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='bg_removal_previews',
    )
    component_image = models.ForeignKey(
        'components.ComponentImage', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='bg_removal_previews',
    )
    applied_at = models.DateTimeField(null=True, blank=True)

    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    error = models.TextField(blank=True)

    # Parameters used for the most recent (re)processing run - kept so the
    # frontend can show what produced the current result, and so
    # /reprocess/ has something to diff against.
    model_name = models.CharField(max_length=30, choices=MODEL_CHOICES, default=DEFAULT_MODEL)
    alpha_matting = models.BooleanField(default=False)
    foreground_threshold = models.PositiveSmallIntegerField(default=240)
    background_threshold = models.PositiveSmallIntegerField(default=10)
    erode_size = models.PositiveSmallIntegerField(default=10)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return f'BackgroundRemovalPreview {self.id} ({self.status})'
