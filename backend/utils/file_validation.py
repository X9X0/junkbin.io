"""
File validation utilities for Junkbin.io

Provides magic byte verification to ensure uploaded files match their claimed type.
"""
import magic
from django.core.exceptions import ValidationError


# MIME type to allowed extensions mapping
MIME_TO_EXTENSIONS = {
    'image/jpeg': ['jpg', 'jpeg', 'jfif'],
    'image/png': ['png'],
    'image/gif': ['gif'],
    'image/webp': ['webp'],
    'image/avif': ['avif'],
    'image/svg+xml': ['svg'],
    'application/pdf': ['pdf'],
}

# Extension to expected MIME types mapping
EXTENSION_TO_MIMES = {
    'jpg': ['image/jpeg'],
    'jpeg': ['image/jpeg'],
    'jfif': ['image/jpeg'],
    'png': ['image/png'],
    'gif': ['image/gif'],
    'webp': ['image/webp'],
    'avif': ['image/avif'],
    'svg': ['image/svg+xml', 'text/xml', 'application/xml'],
    'pdf': ['application/pdf'],
}


def validate_file_magic(file, allowed_extensions=None):
    """
    Validate that a file's actual content matches its declared extension.

    Uses libmagic to detect the real file type based on magic bytes,
    not just the file extension which can be spoofed.

    Args:
        file: Django UploadedFile or file-like object
        allowed_extensions: Optional list of allowed extensions. If not provided,
                          only validates that content matches declared extension.

    Raises:
        ValidationError: If file type doesn't match extension or isn't allowed

    Returns:
        str: The detected MIME type
    """
    # Get file extension
    filename = getattr(file, 'name', '')
    if '.' in filename:
        extension = filename.rsplit('.', 1)[-1].lower()
    else:
        extension = ''

    # Check if extension is in allowed list
    if allowed_extensions and extension not in allowed_extensions:
        raise ValidationError(
            f"File extension '.{extension}' is not allowed. "
            f"Allowed extensions: {', '.join(allowed_extensions)}"
        )

    # Read file content to detect MIME type
    file.seek(0)
    file_content = file.read(2048)  # Read first 2KB for magic detection
    file.seek(0)  # Reset file pointer

    # Detect MIME type using libmagic
    try:
        mime = magic.Magic(mime=True)
        detected_mime = mime.from_buffer(file_content)
    except Exception as e:
        raise ValidationError(f"Could not determine file type: {str(e)}")

    # Validate that detected MIME matches expected for extension
    if extension:
        expected_mimes = EXTENSION_TO_MIMES.get(extension, [])
        if expected_mimes and detected_mime not in expected_mimes:
            raise ValidationError(
                f"File content does not match extension '.{extension}'. "
                f"Detected type: {detected_mime}"
            )

    return detected_mime


def validate_image_file(file):
    """
    Validate that a file is a genuine image.

    Args:
        file: Django UploadedFile

    Raises:
        ValidationError: If file is not a valid image

    Returns:
        str: The detected MIME type
    """
    allowed_extensions = ['jpg', 'jpeg', 'jfif', 'png', 'gif', 'webp', 'avif']
    return validate_file_magic(file, allowed_extensions)


def validate_schematic_file(file):
    """
    Validate that a file is a valid schematic/document type.

    Args:
        file: Django UploadedFile

    Raises:
        ValidationError: If file is not a valid schematic type

    Returns:
        str: The detected MIME type
    """
    allowed_extensions = ['pdf', 'png', 'jpg', 'jpeg', 'jfif', 'gif', 'webp', 'svg', 'zip']
    return validate_file_magic(file, allowed_extensions)
