"""
Pre-compiles rembg/pymatting's numba-jitted alpha-matting kernels in a
throwaway subprocess, so the first real background-removal job after a
deploy doesn't pay that cost itself.

Run as its own subprocess (not imported/called directly), same reasoning
as process_bg_removal_job: numba initializing its threading layer inside
an already-forked Celery worker process has been observed to deadlock the
worker outright. See config/celery.py's worker_ready handler for how this
gets triggered - in a background thread of the (unforked) main worker
process, right after startup, so it never blocks the worker from picking
up other task types while it warms.
"""
import io

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = (
        'Pre-compile rembg/pymatting numba kernels (internal - invoked by '
        'config.celery worker_ready, not meant to be run manually).'
    )

    def handle(self, *args, **options):
        from PIL import Image

        from apps.media_tools.bg_removal import remove_background

        buf = io.BytesIO()
        Image.new('RGB', (32, 32), (128, 128, 128)).save(buf, format='PNG')
        remove_background(buf.getvalue(), model='u2netp')
        self.stdout.write(self.style.SUCCESS('bg-removal cache warmed'))
