"""
Custom validators for Junkbin.io
"""
import re
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from django.conf import settings


def validate_image_size(image):
    """Validate that image doesn't exceed maximum size."""
    if image.size > settings.MAX_IMAGE_SIZE:
        max_mb = settings.MAX_IMAGE_SIZE_MB
        raise ValidationError(
            _('Image file too large. Maximum size is %(max_size)s MB.'),
            params={'max_size': max_mb}
        )


def validate_image_type(image):
    """Validate that image is an allowed type."""
    content_type = getattr(image, 'content_type', None)
    if content_type and content_type not in settings.ALLOWED_IMAGE_TYPES:
        raise ValidationError(
            _('Invalid image type. Allowed types: JPEG, PNG, WebP.')
        )


def validate_part_number(value):
    """
    Validate part number format.

    Part numbers should be alphanumeric with optional dashes and underscores.
    """
    pattern = r'^[A-Za-z0-9\-_./]+$'
    if not re.match(pattern, value):
        raise ValidationError(
            _('Part number can only contain letters, numbers, dashes, underscores, dots, and slashes.')
        )


def validate_reference_designator(value):
    """
    Validate reference designator format.

    Common formats: U1, R23, C100, Q5, D12, etc.
    """
    if not value:
        return  # Empty is allowed

    pattern = r'^[A-Z]{1,3}\d{1,4}[A-Z]?$'
    if not re.match(pattern, value.upper()):
        raise ValidationError(
            _('Invalid reference designator format. Expected format: U1, R23, C100, etc.')
        )


def validate_fcc_id(value):
    """
    Validate FCC ID format.

    FCC IDs are typically 3-5 characters (grantee code) followed by alphanumeric equipment code.
    """
    if not value:
        return  # Empty is allowed

    pattern = r'^[A-Z0-9]{3,5}[A-Z0-9\-]{1,25}$'
    if not re.match(pattern, value.upper()):
        raise ValidationError(
            _('Invalid FCC ID format.')
        )


def validate_url_safe_string(value):
    """Validate that a string is safe for use in URLs."""
    pattern = r'^[a-z0-9\-]+$'
    if not re.match(pattern, value):
        raise ValidationError(
            _('Value can only contain lowercase letters, numbers, and dashes.')
        )


def validate_year(value):
    """Validate manufacturing year is reasonable."""
    from datetime import datetime
    current_year = datetime.now().year

    if value < 1970:
        raise ValidationError(
            _('Year must be 1970 or later.')
        )
    if value > current_year + 1:
        raise ValidationError(
            _('Year cannot be in the future.')
        )
