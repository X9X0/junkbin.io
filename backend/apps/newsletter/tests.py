from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from .models import Subscriber
from .tokens import make_unsubscribe_token


class SubscriberModelTests(TestCase):
    """Tests for the Subscriber model."""

    def test_create_subscriber(self):
        """Test creating a subscriber."""
        subscriber = Subscriber.objects.create(
            email='test@example.com',
            source='landing',
        )
        self.assertEqual(subscriber.email, 'test@example.com')
        self.assertEqual(subscriber.source, 'landing')
        self.assertTrue(subscriber.is_active)
        self.assertIsNone(subscriber.unsubscribed_at)

    def test_subscriber_str(self):
        """Test subscriber string representation."""
        subscriber = Subscriber.objects.create(email='test@example.com')
        self.assertEqual(str(subscriber), 'test@example.com')

    def test_email_unique(self):
        """Test that email must be unique."""
        Subscriber.objects.create(email='test@example.com')
        with self.assertRaises(Exception):
            Subscriber.objects.create(email='test@example.com')


class SubscribeAPITests(APITestCase):
    """Tests for the subscribe API endpoint."""
    throttle_classes = []

    def setUp(self):
        self.url = reverse('newsletter-subscribe')

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        from apps.newsletter.views import SubscribeView
        cls._orig_throttle = SubscribeView.throttle_classes
        SubscribeView.throttle_classes = []

    @classmethod
    def tearDownClass(cls):
        from apps.newsletter.views import SubscribeView
        SubscribeView.throttle_classes = cls._orig_throttle
        super().tearDownClass()

    def test_subscribe_success(self):
        """Test successful subscription."""
        response = self.client.post(self.url, {'email': 'test@example.com'})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['email'], 'test@example.com')
        self.assertTrue(Subscriber.objects.filter(email='test@example.com').exists())

    def test_subscribe_with_source(self):
        """Test subscription with custom source."""
        response = self.client.post(self.url, {
            'email': 'test@example.com',
            'source': 'footer'
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        subscriber = Subscriber.objects.get(email='test@example.com')
        self.assertEqual(subscriber.source, 'footer')

    def test_subscribe_normalizes_email(self):
        """Test that email is normalized to lowercase."""
        response = self.client.post(self.url, {'email': 'TEST@EXAMPLE.COM'})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(Subscriber.objects.filter(email='test@example.com').exists())

    def test_subscribe_duplicate_email(self):
        """Test subscribing with duplicate email returns error."""
        Subscriber.objects.create(email='test@example.com')
        response = self.client.post(self.url, {'email': 'test@example.com'})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('email', response.data)

    def test_subscribe_reactivate_unsubscribed(self):
        """Test that unsubscribed email can be reactivated."""
        from django.utils import timezone
        subscriber = Subscriber.objects.create(
            email='test@example.com',
            is_active=False,
            unsubscribed_at=timezone.now()
        )
        response = self.client.post(self.url, {'email': 'test@example.com'})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        subscriber.refresh_from_db()
        self.assertTrue(subscriber.is_active)
        self.assertIsNone(subscriber.unsubscribed_at)

    def test_subscribe_invalid_email(self):
        """Test subscribing with invalid email returns error."""
        response = self.client.post(self.url, {'email': 'notanemail'})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_subscribe_missing_email(self):
        """Test subscribing without email returns error."""
        response = self.client.post(self.url, {})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_subscribe_captures_metadata(self):
        """Test that IP and user agent are captured."""
        response = self.client.post(
            self.url,
            {'email': 'test@example.com'},
            HTTP_USER_AGENT='TestBrowser/1.0'
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        subscriber = Subscriber.objects.get(email='test@example.com')
        self.assertEqual(subscriber.user_agent, 'TestBrowser/1.0')


class UnsubscribeAPITests(APITestCase):
    """Tests for the one-click unsubscribe API endpoint."""

    def _url(self, token):
        return reverse('newsletter-unsubscribe', args=[token])

    def test_unsubscribe_subscriber_via_get(self):
        subscriber = Subscriber.objects.create(email='test@example.com', is_active=True)
        token = make_unsubscribe_token('subscriber', str(subscriber.id))

        response = self.client.get(self._url(token))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['email'], 'test@example.com')
        subscriber.refresh_from_db()
        self.assertFalse(subscriber.is_active)
        self.assertIsNotNone(subscriber.unsubscribed_at)

    def test_unsubscribe_subscriber_via_post_is_one_click(self):
        """RFC 8058: mail clients POST automatically with no user interaction."""
        subscriber = Subscriber.objects.create(email='test@example.com', is_active=True)
        token = make_unsubscribe_token('subscriber', str(subscriber.id))

        response = self.client.post(self._url(token))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        subscriber.refresh_from_db()
        self.assertFalse(subscriber.is_active)

    def test_unsubscribe_is_idempotent(self):
        subscriber = Subscriber.objects.create(email='test@example.com', is_active=True)
        token = make_unsubscribe_token('subscriber', str(subscriber.id))

        first = self.client.get(self._url(token))
        second = self.client.get(self._url(token))

        self.assertEqual(first.status_code, status.HTTP_200_OK)
        self.assertEqual(second.status_code, status.HTTP_200_OK)
        subscriber.refresh_from_db()
        self.assertFalse(subscriber.is_active)

    def test_unsubscribe_user_flips_email_notifications(self):
        from apps.users.models import User
        user = User.objects.create_user(
            username='unsubtest', email='unsubtest@example.com', password='testpass123',
        )
        user.preferences = {'email_notifications': True}
        user.save()
        token = make_unsubscribe_token('user', str(user.id))

        response = self.client.get(self._url(token))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['email'], 'unsubtest@example.com')
        user.refresh_from_db()
        self.assertFalse(user.preferences.get('email_notifications'))

    def test_unsubscribe_invalid_token_rejected(self):
        response = self.client.get(self._url('not-a-real-token'))
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_unsubscribe_tampered_token_rejected(self):
        subscriber = Subscriber.objects.create(email='test@example.com', is_active=True)
        token = make_unsubscribe_token('subscriber', str(subscriber.id))
        tampered = token[:-1] + ('x' if token[-1] != 'x' else 'y')

        response = self.client.get(self._url(tampered))

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        subscriber.refresh_from_db()
        self.assertTrue(subscriber.is_active)

    def test_unsubscribe_token_for_deleted_subscriber_handled(self):
        subscriber = Subscriber.objects.create(email='test@example.com', is_active=True)
        token = make_unsubscribe_token('subscriber', str(subscriber.id))
        subscriber.delete()

        response = self.client.get(self._url(token))

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_unsubscribe_cannot_target_another_subscriber_by_editing_id(self):
        """A token is only valid for the exact kind:id it was signed for -
        swapping in a different id invalidates the signature entirely."""
        victim = Subscriber.objects.create(email='victim@example.com', is_active=True)
        attacker_token = make_unsubscribe_token('subscriber', str(victim.id))
        forged = attacker_token.replace(str(victim.id), '00000000-0000-0000-0000-000000000000')

        response = self.client.get(self._url(forged))

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        victim.refresh_from_db()
        self.assertTrue(victim.is_active)
