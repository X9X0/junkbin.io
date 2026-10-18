"""
Make a reviewed bulk-import batch public.

    manage.py approve_import_batch                     show every batch's review progress
    manage.py approve_import_batch BATCH [--force]     approve (requires the review gate unless --force)
"""
from django.core.management.base import BaseCommand, CommandError

from apps.products.import_review import BATCHES, approve_batch, stats


class Command(BaseCommand):
    help = 'Approve a reviewed bulk-import batch'

    def add_arguments(self, parser):
        parser.add_argument('batch', nargs='?', choices=list(BATCHES))
        parser.add_argument('--force', action='store_true', help='Approve without meeting the review gate')

    def handle(self, *args, **options):
        if not options['batch']:
            for b in BATCHES:
                s = stats(b)
                self.stdout.write(f"{b:15} {s['label'][:45]:45} items {s['total']:5}  reviewed "
                                  f"{s['correct']}/{s['target']} correct, {s['flagged']} flagged, "
                                  f"{s['unapproved']} unapproved{'  READY' if s['can_approve'] else ''}")
            return
        try:
            counts = approve_batch(options['batch'], force=options['force'])
        except ValueError as exc:
            raise CommandError(str(exc))
        self.stdout.write(self.style.SUCCESS(f"{options['batch']} approved: {counts}"))
