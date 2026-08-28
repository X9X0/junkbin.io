"""
Tests for the notifications API endpoints.
"""
import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.notifications.models import Notification, PushSubscription
from apps.users.tests.factories import UserFactory


@pytest.fixture
def user(db):
    return UserFactory()


@pytest.fixture
def authed_client(user):
    client = APIClient()
    refresh = RefreshToken.for_user(user)
    client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
    return client


class TestNotificationList:
    def test_only_returns_own_notifications(self, authed_client, user):
        other = UserFactory()
        Notification.objects.create(recipient=user, category='new_message', title='Mine')
        Notification.objects.create(recipient=other, category='new_message', title='Not mine')

        resp = authed_client.get(reverse('notification-list'))

        assert resp.status_code == status.HTTP_200_OK
        titles = [n['title'] for n in resp.data['results']]
        assert titles == ['Mine']

    def test_requires_auth(self):
        resp = APIClient().get(reverse('notification-list'))
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED


class TestUnreadCount:
    def test_counts_only_unread(self, authed_client, user):
        Notification.objects.create(recipient=user, category='new_message', title='A', is_read=False)
        Notification.objects.create(recipient=user, category='new_message', title='B', is_read=True)

        resp = authed_client.get(reverse('notification-unread-count'))

        assert resp.status_code == status.HTTP_200_OK
        assert resp.data['count'] == 1


class TestMarkRead:
    def test_mark_read(self, authed_client, user):
        n = Notification.objects.create(recipient=user, category='new_message', title='A')

        resp = authed_client.post(reverse('notification-mark-read', kwargs={'pk': n.pk}))

        assert resp.status_code == status.HTTP_200_OK
        n.refresh_from_db()
        assert n.is_read is True
        assert n.read_at is not None

    def test_mark_all_read(self, authed_client, user):
        Notification.objects.create(recipient=user, category='new_message', title='A')
        Notification.objects.create(recipient=user, category='new_message', title='B')

        resp = authed_client.post(reverse('notification-mark-all-read'))

        assert resp.status_code == status.HTTP_200_OK
        assert resp.data['updated'] == 2
        assert not Notification.objects.filter(recipient=user, is_read=False).exists()


class TestPushSubscribe:
    def test_subscribe_creates_row(self, authed_client, user):
        resp = authed_client.post(reverse('push-subscribe'), {
            'endpoint': 'https://push.example.com/abc123',
            'keys': {'p256dh': 'fake-p256dh', 'auth': 'fake-auth'},
        }, format='json')

        assert resp.status_code == status.HTTP_201_CREATED
        assert PushSubscription.objects.filter(user=user, endpoint='https://push.example.com/abc123').exists()

    def test_unsubscribe_deletes_row(self, authed_client, user):
        PushSubscription.objects.create(
            user=user, endpoint='https://push.example.com/xyz',
            p256dh='p', auth='a',
        )

        resp = authed_client.post(reverse('push-unsubscribe'), {'endpoint': 'https://push.example.com/xyz'})

        assert resp.status_code == status.HTTP_204_NO_CONTENT
        assert not PushSubscription.objects.filter(endpoint='https://push.example.com/xyz').exists()
