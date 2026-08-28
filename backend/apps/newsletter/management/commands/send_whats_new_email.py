"""
Send a "What's New" update email, generalized from send_launch_email.py's
proven recipient-dedup/dry-run/confirm pattern.

Content isn't parsed out of frontend/src/pages/News.tsx - that's a hand-
written TSX array, and a scraper reliable enough to trust against real
subscribers wasn't worth building versus just re-supplying the same
paragraph you already wrote for the site. Feed it back in via --file (a
JSON dump of the entry you just added) or the --week/--dates/--intro/
--item flags directly.

Usage:
    python manage.py send_whats_new_email --file week.json --dry-run
    python manage.py send_whats_new_email --file week.json

    # or inline, no file:
    python manage.py send_whats_new_email \
        --week "Week 12" --dates "Aug 27, 2026" \
        --intro "..." --item "First thing" --item "Second thing"

week.json shape:
    {
      "week": "Week 12",
      "dates": "Aug 27, 2026",
      "intro": "...",
      "items": ["...", "..."],
      "earlier": ["...", "..."]   // optional - shown in an "Earlier improvements" section
    }
"""
import json
import time

from django.core.management.base import BaseCommand, CommandError

from apps.newsletter.models import Subscriber
from apps.users.models import User
from utils.email import send_templated_email


class Command(BaseCommand):
    help = "Send a What's New update email to active newsletter subscribers and opted-in registered members."

    def add_arguments(self, parser):
        parser.add_argument('--file', help='Path to a JSON file with week/dates/intro/items (see module docstring)')
        parser.add_argument('--week', help='e.g. "Week 12"')
        parser.add_argument('--dates', help='e.g. "Aug 27, 2026"')
        parser.add_argument('--intro', help='Intro paragraph')
        parser.add_argument('--item', action='append', dest='items', help='One changelog bullet - repeat for each item')
        parser.add_argument('--earlier', action='append', dest='earlier', help='One "earlier improvements" bullet - repeat for each item (optional)')
        parser.add_argument('--dry-run', action='store_true', help='Show recipients and the rendered content without sending')
        parser.add_argument('--yes', action='store_true', help='Skip the confirmation prompt')

    def handle(self, *args, **options):
        content = self._load_content(options)

        subscriber_emails = set(
            Subscriber.objects.filter(is_active=True).values_list('email', flat=True)
        )
        user_emails = set()
        for user in User.objects.filter(is_active=True).exclude(email=''):
            prefs = getattr(user, 'preferences', None) or {}
            if prefs.get('email_notifications', True):
                user_emails.add(user.email)

        recipients = sorted(subscriber_emails | user_emails)
        count = len(recipients)

        self.stdout.write(self.style.NOTICE(
            f"\nSubject: What's New on Junkbin.io — {content['week']}\n"
        ))
        self.stdout.write(f"{content['week']} ({content['dates']})\n")
        self.stdout.write(content['intro'] + '\n')
        for item in content['items']:
            self.stdout.write(f'  - {item}')
        if content.get('earlier'):
            self.stdout.write('\nEarlier improvements:')
            for item in content['earlier']:
                self.stdout.write(f'  - {item}')
        self.stdout.write('')

        if count == 0:
            self.stdout.write(self.style.WARNING('No recipients found.'))
            return

        if options['dry_run']:
            self.stdout.write(self.style.NOTICE(
                f'DRY RUN — {count} recipient(s) would receive this '
                f'({len(subscriber_emails)} subscribers, {len(user_emails)} members):\n'
            ))
            for email in recipients:
                self.stdout.write(f'  {email}')
            return

        if not options['yes']:
            self.stdout.write(
                f"\nAbout to send to {count} recipient(s) "
                f"({len(subscriber_emails)} subscribers, {len(user_emails)} members)."
            )
            confirm = input('Type "yes" to continue: ')
            if confirm.strip().lower() != 'yes':
                self.stdout.write(self.style.WARNING('Aborted.'))
                return

        sent = 0
        failed = 0
        for email in recipients:
            self.stdout.write(f'Sending to {email}... ', ending='')
            try:
                send_templated_email(
                    subject=f"What's New on Junkbin.io — {content['week']}",
                    template_name='whats_new',
                    context={
                        'week': content['week'],
                        'dates': content['dates'],
                        'intro': content['intro'],
                        'items': content['items'],
                        'earlier': content.get('earlier'),
                    },
                    recipient_list=[email],
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

    def _load_content(self, options):
        if options.get('file'):
            try:
                with open(options['file']) as f:
                    data = json.load(f)
            except OSError as e:
                raise CommandError(f'Could not read --file: {e}')
            except json.JSONDecodeError as e:
                raise CommandError(f'--file is not valid JSON: {e}')
            missing = [k for k in ('week', 'dates', 'intro', 'items') if not data.get(k)]
            if missing:
                raise CommandError(f'--file is missing required key(s): {", ".join(missing)}')
            if not isinstance(data['items'], list) or not all(isinstance(i, str) for i in data['items']):
                raise CommandError('--file "items" must be a list of strings')
            earlier = data.get('earlier')
            if earlier is not None and (not isinstance(earlier, list) or not all(isinstance(i, str) for i in earlier)):
                raise CommandError('--file "earlier" must be a list of strings')
            return data

        if not (options.get('week') and options.get('dates') and options.get('intro') and options.get('items')):
            raise CommandError(
                'Provide --file, or all of --week, --dates, --intro, and at least one --item.'
            )
        return {
            'week': options['week'],
            'dates': options['dates'],
            'intro': options['intro'],
            'items': options['items'],
            'earlier': options.get('earlier'),
        }
