"""
Media tools models for Junkbin.io

BackgroundRemovalPreview is deliberately not attached to a Product/
Component image - it's a throwaway workspace for the pre-submission
preview step (upload -> auto-remove -> compare/tweak -> decide) in
ImageUpload.tsx. Nothing here is ever the image actually attached to a
listing; the frontend uploads whichever version (original or result) the
user lands on through the normal image-upload endpoints, and these rows
get swept up by cleanup_stale_previews once they're a few hours old.
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
