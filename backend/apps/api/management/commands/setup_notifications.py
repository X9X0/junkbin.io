"""
Management command to set up notification periodic tasks and preferences.
"""
from django.core.management.base import BaseCommand

from django_celery_beat.models import PeriodicTask, IntervalSchedule, CrontabSchedule


class Command(BaseCommand):
    help = 'Create periodic tasks for notifications and preferences for existing staff.'

    def handle(self, *args, **options):
        self._create_periodic_tasks()
        self._create_staff_preferences()

    def _create_periodic_tasks(self):
        # Health check every 5 minutes
        interval, _ = IntervalSchedule.objects.get_or_create(
            every=5, period=IntervalSchedule.MINUTES,
        )
        task, created = PeriodicTask.objects.get_or_create(
            name='Check System Health',
            defaults={
                'task': 'apps.api.tasks.check_system_health',
                'interval': interval,
                'enabled': True,
            },
        )
        if created:
            self.stdout.write(self.style.SUCCESS('Created periodic task: Check System Health (every 5 min)'))
        else:
            self.stdout.write('Periodic task already exists: Check System Health')

        # Daily digest at 9 AM UTC
        crontab, _ = CrontabSchedule.objects.get_or_create(
            minute='0', hour='9',
            day_of_week='*', day_of_month='*', month_of_year='*',
        )
        task, created = PeriodicTask.objects.get_or_create(
            name='Send Daily Digest',
            defaults={
                'task': 'apps.api.tasks.send_daily_digest',
                'crontab': crontab,
                'enabled': True,
            },
        )
        if created:
            self.stdout.write(self.style.SUCCESS('Created periodic task: Send Daily Digest (daily 9 AM UTC)'))
        else:
            self.stdout.write('Periodic task already exists: Send Daily Digest')

    def _create_staff_preferences(self):
        from apps.api.models import NotificationPreference
        from apps.users.models import User

        staff = User.objects.filter(is_staff=True)
        created_count = 0
        for user in staff:
            _, created = NotificationPreference.objects.get_or_create(user=user)
            if created:
                created_count += 1

        if created_count:
            self.stdout.write(self.style.SUCCESS(
                f'Created notification preferences for {created_count} staff user(s)'
            ))
        else:
            self.stdout.write('All staff users already have notification preferences')
