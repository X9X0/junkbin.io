from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from .models import Subscriber


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

    def setUp(self):
        self.url = reverse('newsletter-subscribe')

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
