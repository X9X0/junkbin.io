"""
Does the actual rembg/pymatting work for one BackgroundRemovalPreview, in
its own fresh process rather than inside a long-lived Celery worker.

Why: onnxruntime and pymatting's numba-jitted alpha-matting path both spin
up their own native thread pools. A Celery prefork worker is a process
that was fork()'d once at startup and then reused for hundreds of
unrelated tasks - if this is the first task in a given worker child to
touch alpha matting, numba initializing its threading layer at that point
has been observed here to deadlock the worker outright (reproduced: task
received, then every process in the container sits in state S/sleeping
indefinitely, no CPU use, no crash, no timeout - see the investigation
that added this command). The identical code called directly (plain
`python manage.py shell`, no prior fork) completes normally in ~30s.

Running it via subprocess.run() from the Celery task instead means every
job gets a brand-new interpreter via fork+exec - the exec() replaces the
process image entirely, so there's no inherited thread/JIT state from
anything the worker did before. A crash here costs one subprocess, never
the worker itself.
"""
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = 'Run background removal for one BackgroundRemovalPreview (internal - invoked by apps.media_tools.tasks.process_bg_removal via subprocess, not meant to be run manually).'

    def add_arguments(self, parser):
        parser.add_argument('preview_id')

    def handle(self, *args, **options):
        from apps.media_tools.bg_removal import remove_background
        from apps.media_tools.models import BackgroundRemovalPreview
        from django.core.files.base import ContentFile

        preview_id = options['preview_id']
        try:
            preview = BackgroundRemovalPreview.objects.get(id=preview_id)
        except BackgroundRemovalPreview.DoesNotExist:
            raise CommandError(f'No such preview: {preview_id}')

        with preview.original.open('rb') as f:
            source_bytes = f.read()

        result_bytes = remove_background(
            source_bytes,
            model=preview.model_name,
            alpha_matting=preview.alpha_matting,
            foreground_threshold=preview.foreground_threshold,
            background_threshold=preview.background_threshold,
            erode_size=preview.erode_size,
        )

        preview.result.save(f'{preview.id}.png', ContentFile(result_bytes), save=False)
        preview.status = BackgroundRemovalPreview.Status.DONE
        preview.error = ''
        preview.save(update_fields=['result', 'status', 'error', 'updated_at'])
        self.stdout.write(self.style.SUCCESS(f'{preview_id}: done'))
