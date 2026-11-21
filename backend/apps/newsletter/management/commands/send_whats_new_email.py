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
        --week "Update 12" --dates "Aug 27, 2026" \
        --intro "..." --item "First thing" --item "Second thing"

week.json shape:
    {
      "week": "Update 12",
      "dates": "Aug 27, 2026",
      "intro": "...",
      "items": ["...", {"text": "...", "url": "https://..."}],
      "earlier": ["...", "..."]   // optional - shown in an "Earlier improvements" section
    }

Each entry in "items"/"earlier" can be a plain string, or an object with
"text" and an optional "url" to render that one bullet as a link.

The relay allows 300 mails an hour for the whole domain: sends are paced (--per-hour, default 240), a quota
refusal is waited out until the time the relay names, --sent-log records who was sent to so a re-run skips
them, and --skip N resumes a run that was cut off (recipients go in address order).
"""
import json
import re
import time
from datetime import datetime, timezone as dt_timezone

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from apps.newsletter.models import Subscriber
from apps.newsletter.tokens import make_unsubscribe_token
from apps.users.models import User
from utils.email import send_templated_email


QUOTA_TILL = re.compile(r'Quota Exceeded.*?\[time=(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}) UTC\]')


def quota_wait(error_text):
    """Seconds to wait when the relay refused for the domain's hourly quota ('5.4.6 Sender Domain Hourly Quota
    Exceeded ... till [time=2026-11-21 22:39:13 UTC]'), else 0. Never more than six hours; a minute's margin."""
    if 'Quota Exceeded' not in error_text:
        return 0
    m = QUOTA_TILL.search(error_text)
    if not m:
        return 3600
    till = datetime.strptime(m.group(1), '%Y-%m-%d %H:%M:%S').replace(tzinfo=dt_timezone.utc)
    return max(60, min(6 * 3600, int((till - datetime.now(dt_timezone.utc)).total_seconds()) + 60))


def _normalize_bullets(raw, field_name):
    """Turn a list of str | {"text", "url"?} into a uniform list of
    {"text": str, "url": str} dicts, so templates never have to branch
    on the two shapes."""
    normalized = []
    for entry in raw:
        if isinstance(entry, str):
            normalized.append({'text': entry, 'url': ''})
        elif isinstance(entry, dict) and isinstance(entry.get('text'), str):
            url = entry.get('url', '')
            if not isinstance(url, str):
                raise CommandError(f'"{field_name}" entry "url" must be a string')
            normalized.append({'text': entry['text'], 'url': url})
        else:
            raise CommandError(
                f'"{field_name}" entries must be strings or {{"text": ..., "url": ...}} objects'
            )
    return normalized


class Command(BaseCommand):
    help = "Send a What's New update email to active newsletter subscribers and opted-in registered members."

    def add_arguments(self, parser):
        parser.add_argument('--file', help='Path to a JSON file with week/dates/intro/items (see module docstring)')
        parser.add_argument('--week', help='e.g. "Update 12"')
        parser.add_argument('--dates', help='e.g. "Aug 27, 2026"')
        parser.add_argument('--intro', help='Intro paragraph')
        parser.add_argument('--item', action='append', dest='items', help='One changelog bullet - repeat for each item')
        parser.add_argument('--earlier', action='append', dest='earlier', help='One "earlier improvements" bullet - repeat for each item (optional)')
        parser.add_argument('--dry-run', action='store_true', help='Show recipients and the rendered content without sending')
        parser.add_argument('--yes', action='store_true', help='Skip the confirmation prompt')
        parser.add_argument('--per-hour', type=int, default=240,
                            help='Pace sends to at most this many an hour (the relay allows 300 for the whole domain; default 240 leaves room for the site\'s own mail)')
        parser.add_argument('--skip', type=int, default=0,
                            help='Skip the first N recipients in address order (resume a run the relay cut off: they were sent in that order)')
        parser.add_argument('--sent-log', help='File that records each address sent to; on a re-run those are skipped')

    def handle(self, *args, **options):
        content = self._load_content(options)

        # A registered User's identity takes priority over a same-email
        # Subscriber row: unsubscribing must flip the same email_notifications
        # flag that governs their account (and everything else gated on it),
        # or a stale Subscriber row would keep pulling them back into future
        # sends via the User-side membership check.
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

        self.stdout.write(self.style.NOTICE(
            f"\nSubject: What's New on Junkbin.io — {content['week']}\n"
        ))
        self.stdout.write(f"{content['week']} ({content['dates']})\n")
        self.stdout.write(content['intro'] + '\n')
        for item in content['items']:
            suffix = f" ({item['url']})" if item['url'] else ''
            self.stdout.write(f"  - {item['text']}{suffix}")
        if content.get('earlier'):
            self.stdout.write('\nEarlier improvements:')
            for item in content['earlier']:
                suffix = f" ({item['url']})" if item['url'] else ''
                self.stdout.write(f"  - {item['text']}{suffix}")
        self.stdout.write('')

        if count == 0:
            self.stdout.write(self.style.WARNING('No recipients found.'))
            return

        if options['dry_run']:
            self.stdout.write(self.style.NOTICE(
                f'DRY RUN — {count} recipient(s) would receive this '
                f'({len(subscriber_emails)} subscribers, {len(user_emails)} members):\n'
            ))
            for email, _kind, _id in recipients:
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

        site_url = getattr(settings, 'SITE_URL', '')
        already = set()
        if options.get('sent_log'):
            try:
                with open(options['sent_log']) as fh:
                    already = {line.strip() for line in fh if line.strip()}
            except OSError:
                pass
        todo = [r for r in recipients[options['skip']:] if r[0] not in already]
        if options['skip'] or already:
            self.stdout.write(f'Skipping {count - len(todo)} already sent; {len(todo)} to go.')
        pause = 3600.0 / max(1, options['per_hour'])
        sent = 0
        failed = 0
        for email, kind, identifier in todo:
            self.stdout.write(f'Sending to {email}... ', ending='')
            unsubscribe_url = f"{site_url}/unsubscribe/{make_unsubscribe_token(kind, identifier)}"
            for attempt in range(3):
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
                        unsubscribe_url=unsubscribe_url,
                    )
                    self.stdout.write(self.style.SUCCESS('OK'))
                    sent += 1
                    if options.get('sent_log'):
                        with open(options['sent_log'], 'a') as fh:
                            fh.write(email + '\n')
                    break
                except Exception as e:
                    wait = quota_wait(str(e))
                    if wait and attempt < 2:
                        # the relay's hourly domain quota: wait it out, then carry on where we were
                        self.stdout.write(self.style.WARNING(f'quota exceeded, waiting {wait // 60} min... '), ending='')
                        time.sleep(wait)
                        continue
                    self.stdout.write(self.style.ERROR(f'FAILED ({e})'))
                    failed += 1
                    break

            # paced so the domain stays under the relay's hourly quota
            time.sleep(pause)

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
            if not isinstance(data['items'], list):
                raise CommandError('--file "items" must be a list')
            data['items'] = _normalize_bullets(data['items'], 'items')
            if data.get('earlier') is not None:
                if not isinstance(data['earlier'], list):
                    raise CommandError('--file "earlier" must be a list')
                data['earlier'] = _normalize_bullets(data['earlier'], 'earlier')
            return data

        if not (options.get('week') and options.get('dates') and options.get('intro') and options.get('items')):
            raise CommandError(
                'Provide --file, or all of --week, --dates, --intro, and at least one --item.'
            )
        return {
            'week': options['week'],
            'dates': options['dates'],
            'intro': options['intro'],
            'items': _normalize_bullets(options['items'], 'items'),
            'earlier': _normalize_bullets(options['earlier'], 'earlier') if options.get('earlier') else None,
        }
