import time
from datetime import datetime, timedelta, timezone

from django.conf import settings
from django.core.management.base import BaseCommand

from apps.newsletter.models import Subscriber
from apps.newsletter.tokens import make_unsubscribe_token
from apps.users.models import User
from utils.email import send_templated_email

# Day one of OpenSauce 2026 is also our launch day (Pacific time).
OPENSAUCE_START = datetime(2026, 7, 17, 0, 0, 0, tzinfo=timezone(timedelta(hours=-7)))


class Command(BaseCommand):
    help = 'Send launch announcement email to all active newsletter subscribers and opted-in registered users'

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
        # A registered User's identity takes priority over a same-email
        # Subscriber row - see send_whats_new_email.py for why.
        user_map = {}
        for user in User.objects.filter(is_active=True).exclude(email=''):
            prefs = getattr(user, 'preferences', None) or {}
            if prefs.get('email_notifications', True):
                user_map[user.email] = str(user.id)

        subscriber_map = {}
        for sub in Subscriber.objects.filter(is_active=True):
            if sub.email not in user_map:
                subscriber_map[sub.email] = str(sub.id)

        recipients = sorted(
            [(email, 'user', uid) for email, uid in user_map.items()]
            + [(email, 'subscriber', sid) for email, sid in subscriber_map.items()],
            key=lambda r: r[0],
        )
        count = len(recipients)
        subscriber_emails = subscriber_map.keys()
        user_emails = user_map.keys()

        if count == 0:
            self.stdout.write(self.style.WARNING('No recipients found.'))
            return

        if options['dry_run']:
            self.stdout.write(self.style.NOTICE(
                f'DRY RUN — {count} recipient(s) would receive the launch email '
                f'({len(subscriber_emails)} subscribers, {len(user_emails)} members):\n'
            ))
            for email, _kind, _id in recipients:
                self.stdout.write(f'  {email}')
            return

        if not options['yes']:
            self.stdout.write(
                f'\nAbout to send launch email to {count} recipient(s) '
                f'({len(subscriber_emails)} subscribers, {len(user_emails)} members).'
            )
            confirm = input('Type "yes" to continue: ')
            if confirm.strip().lower() != 'yes':
                self.stdout.write(self.style.WARNING('Aborted.'))
                return

        days_until_opensauce = max((OPENSAUCE_START - datetime.now(timezone.utc)).days, 0)
        site_url = getattr(settings, 'SITE_URL', '')

        sent = 0
        failed = 0

        for email, kind, identifier in recipients:
            self.stdout.write(f'Sending to {email}... ', ending='')
            try:
                unsubscribe_url = f"{site_url}/unsubscribe/{make_unsubscribe_token(kind, identifier)}"
                send_templated_email(
                    subject="Junkbin.io is live — and we'll be at OpenSauce 2026",
                    template_name='launch_announcement',
                    context={'days_until_opensauce': days_until_opensauce},
                    recipient_list=[email],
                    unsubscribe_url=unsubscribe_url,
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
