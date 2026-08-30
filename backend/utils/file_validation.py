"""
File validation utilities for Junkbin.io

Provides magic byte verification to ensure uploaded files match their claimed type.
"""
import magic
from django.core.exceptions import ValidationError

from apps.products.models import ALLOWED_FIRMWARE_EXTENSIONS, ALLOWED_SCHEMATIC_EXTENSIONS


# MIME type to allowed extensions mapping
MIME_TO_EXTENSIONS = {
    'image/jpeg': ['jpg', 'jpeg', 'jfif'],
    'image/png': ['png'],
    'image/gif': ['gif'],
    'image/webp': ['webp'],
    'image/avif': ['avif'],
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
    'pdf': ['application/pdf'],
    # libmagic misidentifies stored (non-deflate) zips as application/octet-stream,
    # which is common for archives of already-compressed binary board-view data.
    'zip': ['application/zip', 'application/x-zip-compressed', 'application/octet-stream'],
    # Altium Designer documents are OLE compound files; libmagic reports these as
    # application/CDFV2 (or x-ole-storage on some distros' magic databases), and
    # falls back to octet-stream on older ones. EXTENSION_SIGNATURES below does
    # the real check via the OLE2 byte signature.
    'schdoc': ['application/CDFV2', 'application/x-ole-storage', 'application/octet-stream'],
    'pcbdoc': ['application/CDFV2', 'application/x-ole-storage', 'application/octet-stream'],
    'prjpcb': ['application/CDFV2', 'application/x-ole-storage', 'application/octet-stream'],
    # KiCad >=6 schematic/board files (S-expression text)
    'kicad_sch': ['text/plain'],
    'kicad_pcb': ['text/plain'],
    # KiCad >=6 project file is JSON, not S-expression
    'kicad_pro': ['application/json', 'text/plain'],
    # STEP 3D models (ISO-10303-21 text format)
    'step': ['text/plain'],
    'stp': ['text/plain'],
    # Legacy/tool-varying EDA formats: KiCad <6, Eagle (XML), and gEDA all use
    # '.sch'/'.brd' for differently-shaped content, so only the broad text/xml
    # MIME class is verified here rather than a specific signature.
    'sch': ['text/plain', 'text/xml', 'application/xml'],
    'brd': ['text/plain', 'text/xml', 'application/xml'],
    'dxf': ['text/plain', 'image/vnd.dxf', 'application/octet-stream'],
    'gbr': ['text/plain'],
    # XZZPCB board-view files (repair-community format read by
    # OpenBoardview) are binary with an "XZZPCB" magic header (or an
    # XOR-obfuscated variant), so libmagic reports generic octet-stream;
    # the real check is the signature below.
    'pcb': ['application/octet-stream'],
    # No MIME/signature entry for 'tvw' or 'fz' — deliberately omitted, not
    # forgotten. .tvw (Teboview) is an undocumented proprietary board-view
    # format with no public spec to check against. .fz board-view files are
    # RC6-encrypted+zlib-compressed; even OpenBoardview's own loader skips
    # content verification for .fz and trusts the extension outright. High-
    # entropy binary like this also isn't safe to pin to 'octet-stream'
    # alone — libmagic can confidently misdetect unstructured binary as an
    # unrelated specific format (e.g. image/x-tga), which would reject
    # legitimate uploads. These two extensions fall back to allowlist-only
    # gating via ALLOWED_SCHEMATIC_EXTENSIONS.

    # Intel HEX firmware images are plain ASCII text, each line starting
    # with ':'. libmagic recognizes the format specifically on most
    # systems (text/x-hex) but falls back to generic text/plain on others.
    'hex': ['text/x-hex', 'text/plain'],
    # No MIME/signature entry for 'bin', 'rom', 'img', 'dump', or 'fw' —
    # these are, by definition, raw memory/flash dumps with no header
    # format to check. Same reasoning as .tvw/.fz above: allowlist-only
    # gating via ALLOWED_FIRMWARE_EXTENSIONS is the honest option here,
    # not a fake signature that would just reject real uploads.
}

# Raw content signatures checked in addition to the MIME class above, for
# extensions where the MIME alone (e.g. generic 'text/plain') wouldn't catch
# an arbitrary renamed file.
EXTENSION_SIGNATURES = {
    'schdoc': [b'\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1'],  # OLE2 compound file header
    'pcbdoc': [b'\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1'],
    'prjpcb': [b'\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1'],
    'kicad_sch': [b'(kicad_sch'],
    'kicad_pcb': [b'(kicad_pcb'],
    'step': [b'ISO-10303-21'],
    'stp': [b'ISO-10303-21'],
    'pcb': [b'XZZPCB'],
    'elf': [b'\x7fELF'],
    # Weak but real: every line of a genuine Intel HEX file starts with
    # ':', so a file with none anywhere in the first 2KB isn't one.
    'hex': [b':'],
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

        # For formats where the MIME class alone is too generic to be
        # meaningful (e.g. plain text), also check for an expected byte signature.
        signatures = EXTENSION_SIGNATURES.get(extension)
        if signatures and not any(sig in file_content for sig in signatures):
            raise ValidationError(
                f"File content does not match expected format for '.{extension}' files."
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
    return validate_file_magic(file, ALLOWED_SCHEMATIC_EXTENSIONS)


def validate_firmware_file(file):
    """
    Validate that a file is an allowed firmware type.

    Args:
        file: Django UploadedFile

    Raises:
        ValidationError: If file is not an allowed firmware type

    Returns:
        str: The detected MIME type
    """
    return validate_file_magic(file, ALLOWED_FIRMWARE_EXTENSIONS)
