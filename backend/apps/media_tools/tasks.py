import logging
import subprocess
import sys
from datetime import timedelta

from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)

# Previews are a throwaway pre-submission workspace, not content - nothing
# should still be polling one this old.
STALE_AFTER = timedelta(hours=6)

# Generous relative to the ~30s worst case observed for alpha matting on a
# large photo - this bounds a hung/crashed subprocess, not normal runs.
JOB_TIMEOUT_SECONDS = 180


@shared_task
def process_bg_removal(preview_id):
    """Supervises the actual work, which runs in a fresh subprocess - see
    the process_bg_removal_job management command docstring for why."""
    from .models import BackgroundRemovalPreview

    try:
        proc = subprocess.run(
            [sys.executable, 'manage.py', 'process_bg_removal_job', str(preview_id)],
            cwd='/app',
            capture_output=True,
            text=True,
            timeout=JOB_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired:
        logger.warning('Background removal timed out for preview %s', preview_id)
        _mark_failed(preview_id, 'Processing took too long. Try a different model or turn off Refine Edges.')
        return

    if proc.returncode != 0:
        logger.warning(
            'Background removal subprocess failed for preview %s (exit %s): %s',
            preview_id, proc.returncode, proc.stderr[-2000:],
        )
        _mark_failed(preview_id, 'Processing failed. Try a different model or turn off Refine Edges.')


def _mark_failed(preview_id, message):
    from .models import BackgroundRemovalPreview

    BackgroundRemovalPreview.objects.filter(id=preview_id).update(
        status=BackgroundRemovalPreview.Status.FAILED,
        error=message,
        updated_at=timezone.now(),
    )


@shared_task
def cleanup_bg_removal_previews():
    """Sweeps up abandoned scratch-space previews. Applied previews
    (applied_at is set) are excluded - once /apply/ has run, the row is
    the undo record for that change, not scratch space, and is kept
    indefinitely so a moderator can /revert/ it later."""
    from .models import BackgroundRemovalPreview

    cutoff = timezone.now() - STALE_AFTER
    stale = BackgroundRemovalPreview.objects.filter(created_at__lt=cutoff, applied_at__isnull=True)
    count = 0
    for preview in stale.iterator():
        if preview.original:
            preview.original.delete(save=False)
        if preview.result:
            preview.result.delete(save=False)
        preview.delete()
        count += 1
    if count:
        logger.info('Cleaned up %d stale background-removal preview(s).', count)
