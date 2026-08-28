"""
Tests for apps.media_tools.bg_removal - runs the real rembg model (the
model files are baked into the image at build time, see Dockerfile, so
this needs no network access), not a mock, since a mock would only prove
we call the library correctly, not that the output is usable.
"""
import io

import pytest
from PIL import Image

from apps.media_tools.bg_removal import remove_background


def _make_test_image():
    """A simple subject-on-white square, small enough to process quickly."""
    img = Image.new('RGB', (64, 64), (255, 255, 255))
    for x in range(16, 48):
        for y in range(16, 48):
            img.putpixel((x, y), (200, 30, 30))
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    return buf.getvalue()


class TestRemoveBackground:
    def test_returns_valid_png(self):
        result = remove_background(_make_test_image())
        img = Image.open(io.BytesIO(result))
        assert img.format == 'PNG'

    def test_output_has_no_alpha_channel(self):
        """Composited onto black - the whole point is a flat, opaque
        image, not a transparent cutout."""
        result = remove_background(_make_test_image())
        img = Image.open(io.BytesIO(result))
        assert img.mode == 'RGB'

    def test_corners_are_black(self):
        """The corners of a subject-in-the-middle image should have been
        classified as background and composited onto AlphaToBlack's black."""
        result = remove_background(_make_test_image())
        img = Image.open(io.BytesIO(result)).convert('RGB')
        for corner in [(0, 0), (img.width - 1, 0), (0, img.height - 1), (img.width - 1, img.height - 1)]:
            assert img.getpixel(corner) == (0, 0, 0)

    def test_alpha_matting_does_not_crash(self):
        """Regression test: alpha matting previously deadlocked when run
        inside a Celery prefork worker (fixed by running the actual job in
        a subprocess - see process_bg_removal_job). This just confirms the
        underlying function itself still works with alpha_matting=True."""
        result = remove_background(_make_test_image(), alpha_matting=True)
        img = Image.open(io.BytesIO(result))
        assert img.format == 'PNG'

    def test_unknown_model_raises(self):
        with pytest.raises(Exception):
            remove_background(_make_test_image(), model='not-a-real-model')
