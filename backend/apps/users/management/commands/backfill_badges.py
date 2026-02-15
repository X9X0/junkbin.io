"""
One-time management command to backfill badges for all existing users.

Usage:
    python manage.py backfill_badges
"""
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from apps.users.badges import check_and_award_badges


class Command(BaseCommand):
    help = 'Backfill badges for all existing users based on current criteria'

    def handle(self, *args, **options):
        User = get_user_model()
        users = User.objects.all()
        total = users.count()
        awarded_count = 0

        self.stdout.write(f'Checking badges for {total} users...')

        for i, user in enumerate(users.iterator(), 1):
            new_badges = check_and_award_badges(user)
            if new_badges:
                awarded_count += len(new_badges)
                names = ', '.join(b['slug'] for b in new_badges)
                self.stdout.write(f'  {user.username}: +{len(new_badges)} ({names})')

            if i % 100 == 0:
                self.stdout.write(f'  Processed {i}/{total}...')

        self.stdout.write(self.style.SUCCESS(
            f'Done. Awarded {awarded_count} badges across {total} users.'
        ))
