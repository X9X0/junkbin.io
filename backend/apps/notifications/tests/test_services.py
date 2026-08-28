"""
Tests for apps.notifications.services.notify().
"""
import pytest

from apps.notifications.models import Notification
from apps.users.tests.factories import UserFactory


@pytest.fixture
def user(db):
    return UserFactory()


@pytest.fixture
def other_user(db):
    return UserFactory()


class TestNotify:
    def test_creates_notification(self, user, other_user):
        from apps.notifications.services import notify

        n = notify(
            user, Notification.Category.NEW_MESSAGE,
            title='Hello', body='World', url='/messages/1', actor=other_user,
        )

        assert n is not None
        assert Notification.objects.filter(pk=n.pk).exists()
        assert n.recipient == user
        assert n.actor == other_user
        assert n.is_read is False

    def test_skips_self_notification(self, user):
        from apps.notifications.services import notify

        n = notify(
            user, Notification.Category.PRODUCT_COMMENT,
            title='Self comment', actor=user,
        )

        assert n is None
        assert not Notification.objects.filter(recipient=user, title='Self comment').exists()

    def test_notify_staff_fans_out(self, user, other_user):
        from apps.notifications.services import notify_staff

        results = notify_staff(
            [user, other_user], Notification.Category.REPORT_FILED,
            title='New report',
        )

        assert len(results) == 2
        assert Notification.objects.filter(title='New report').count() == 2
