"""
Self-hosted background removal (rembg/ONNX, no external API - models are
baked into the Docker image at build time, see Dockerfile).

Every result is composited onto black rather than left transparent - a
cutout floating on checkerboard/white looks out of place everywhere it's
actually used (product cards, component thumbnails). Reuses
AlphaToBlack, the same flattening apps.products.models already applies
when generating thumbnails from a transparent source image, so a
background-removed photo and its later-generated thumbnail agree on
exactly the same black.
"""
import io

from PIL import Image

from apps.products.models import AlphaToBlack

# Curated subset of rembg's bundled models - general-purpose only, nothing
# specialized for anime/cloth/etc. that wouldn't apply to component photos.
MODEL_CHOICES = [
    ('isnet-general-use', 'General purpose (sharper edges, newer model) (default)'),
    ('u2net', 'General purpose (older model)'),
    ('u2netp', 'Fast/lightweight (lower quality)'),
]
MODEL_NAMES = {value for value, _ in MODEL_CHOICES}
DEFAULT_MODEL = 'isnet-general-use'

_sessions = {}


def _get_session(model_name):
    # Imported lazily, not at module level: rembg pulls in pymatting, whose
    # numba-jitted alpha-matting kernels use an explicit @njit(signature)
    # with no cache=True, so they eagerly compile - for ~100s of real CPU
    # time - the moment rembg is imported, every process, unconditionally
    # (numba has no way to cache them, so this can't be baked into the
    # Docker image either). This module used to import rembg at module
    # level, and since models.py imports MODEL_CHOICES/DEFAULT_MODEL from
    # here, that dragged the full rembg import into every `manage.py`
    # invocation via Django's ordinary app-loading - including `migrate`,
    # stalling every deploy by ~2 minutes for a feature most deploys never
    # touch. Deferring the import to here means only an actual background-
    # removal call (a real celery task/management command) pays that cost.
    from rembg import new_session

    if model_name not in _sessions:
        _sessions[model_name] = new_session(model_name)
    return _sessions[model_name]


def remove_background(
    image_bytes,
    *,
    model=DEFAULT_MODEL,
    alpha_matting=False,
    foreground_threshold=240,
    background_threshold=10,
    erode_size=10,
):
    """Return PNG bytes with the background removed and replaced with the
    site's background color."""
    from rembg import remove

    session = _get_session(model)
    cutout_bytes = remove(
        image_bytes,
        session=session,
        alpha_matting=alpha_matting,
        alpha_matting_foreground_threshold=foreground_threshold,
        alpha_matting_background_threshold=background_threshold,
        alpha_matting_erode_size=erode_size,
    )

    cutout = Image.open(io.BytesIO(cutout_bytes)).convert('RGBA')
    flattened = AlphaToBlack().process(cutout)

    out = io.BytesIO()
    flattened.save(out, format='PNG')
    return out.getvalue()
