import time

from django.core.management.base import BaseCommand

from apps.newsletter.models import Subscriber
from utils.email import send_templated_email


class Command(BaseCommand):
    help = 'Send launch announcement email to all active newsletter subscribers'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Print recipients without sending emails',
        )
        parser.add_argument(
            '--yes',
            action='store_true',
            help='Skip confirmation prompt',
        )

    def handle(self, *args, **options):
        subscribers = Subscriber.objects.filter(is_active=True)
        count = subscribers.count()

        if count == 0:
            self.stdout.write(self.style.WARNING('No active subscribers found.'))
            return

        if options['dry_run']:
            self.stdout.write(self.style.NOTICE(f'DRY RUN — {count} subscribers would receive the launch email:\n'))
            for sub in subscribers:
                self.stdout.write(f'  {sub.email}')
            return

        if not options['yes']:
            self.stdout.write(f'\nAbout to send launch email to {count} subscriber(s).')
            confirm = input('Type "yes" to continue: ')
            if confirm.strip().lower() != 'yes':
                self.stdout.write(self.style.WARNING('Aborted.'))
                return

        sent = 0
        failed = 0

        for sub in subscribers:
            self.stdout.write(f'Sending to {sub.email}... ', ending='')
            try:
                send_templated_email(
                    subject='Junkbin.io is live',
                    template_name='launch_announcement',
                    context={},
                    recipient_list=[sub.email],
                )
                self.stdout.write(self.style.SUCCESS('OK'))
                sent += 1
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'FAILED ({e})'))
                failed += 1

            # Small delay between sends to avoid rate limits
            time.sleep(0.5)

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS(f'Done. Sent: {sent}, Failed: {failed}'))
