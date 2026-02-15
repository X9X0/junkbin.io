"""
Image processing utilities for Junkbin.io
"""
import io
from PIL import Image
from django.core.files.base import ContentFile


def strip_exif(image_file):
    """
    Remove EXIF data from an image for privacy.

    Returns a new file without EXIF metadata.
    """
    try:
        image = Image.open(image_file)

        # Create a new image without EXIF
        data = list(image.getdata())
        image_without_exif = Image.new(image.mode, image.size)
        image_without_exif.putdata(data)

        # Save to buffer
        buffer = io.BytesIO()
        format = image.format or 'JPEG'
        image_without_exif.save(buffer, format=format, quality=95)
        buffer.seek(0)

        return ContentFile(buffer.read())
    except Exception:
        # If processing fails, return original
        image_file.seek(0)
        return image_file


def optimize_image(image_file, max_dimension=2000, quality=85):
    """
    Optimize an image for web display.

    - Resize if larger than max_dimension
    - Convert to RGB if necessary
    - Compress to reduce file size
    """
    try:
        image = Image.open(image_file)

        # Convert to RGB if necessary (for PNG with alpha, etc.)
        # Use black background to match the cyberpunk dark theme
        if image.mode in ('RGBA', 'P'):
            background = Image.new('RGB', image.size, (0, 0, 0))
            if image.mode == 'P':
                image = image.convert('RGBA')
            background.paste(image, mask=image.split()[-1])
            image = background
        elif image.mode != 'RGB':
            image = image.convert('RGB')

        # Resize if too large
        if max(image.size) > max_dimension:
            image.thumbnail((max_dimension, max_dimension), Image.Resampling.LANCZOS)

        # Save optimized
        buffer = io.BytesIO()
        image.save(buffer, format='JPEG', quality=quality, optimize=True)
        buffer.seek(0)

        return ContentFile(buffer.read())
    except Exception:
        image_file.seek(0)
        return image_file


def create_thumbnail(image_file, size=(300, 300)):
    """
    Create a thumbnail of the image.
    """
    try:
        image = Image.open(image_file)

        # Convert to RGB with black background for transparency
        if image.mode in ('RGBA', 'P'):
            background = Image.new('RGB', image.size, (0, 0, 0))
            if image.mode == 'P':
                image = image.convert('RGBA')
            background.paste(image, mask=image.split()[-1])
            image = background
        elif image.mode not in ('RGB', 'L'):
            image = image.convert('RGB')

        # Create thumbnail (maintains aspect ratio)
        image.thumbnail(size, Image.Resampling.LANCZOS)

        buffer = io.BytesIO()
        image.save(buffer, format='JPEG', quality=85)
        buffer.seek(0)

        return ContentFile(buffer.read())
    except Exception:
        return None


def get_image_dimensions(image_file):
    """
    Get the dimensions of an image file.

    Returns (width, height) tuple or (None, None) on error.
    """
    try:
        image = Image.open(image_file)
        return image.size
    except Exception:
        return (None, None)
