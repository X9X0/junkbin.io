import logging

from django.core import signing
from django.core.exceptions import ValidationError
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from rest_framework.views import APIView

from apps.users.models import User
from utils.email import send_templated_email

from .models import Subscriber
from .serializers import SubscribeSerializer
from .tokens import parse_unsubscribe_token

logger = logging.getLogger(__name__)


class SubscribeRateThrottle(AnonRateThrottle):
    """Rate limit for newsletter subscriptions: 10 per hour per IP."""
    scope = 'subscribe'


class SubscribeView(APIView):
    """Public endpoint for newsletter subscription."""

    permission_classes = [AllowAny]
    throttle_classes = [SubscribeRateThrottle]

    def get_client_ip(self, request):
        """Extract client IP from request."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR')

    def _send_confirmation(self, email):
        """Send confirmation email, swallowing errors so the endpoint still succeeds."""
        try:
            send_templated_email(
                subject='You\'re subscribed to Junkbin.io',
                template_name='newsletter_confirm',
                context={},
                recipient_list=[email],
            )
        except Exception:
            logger.exception('Failed to send newsletter confirmation to %s', email)

    def post(self, request):
        """Subscribe an email to the newsletter."""
        serializer = SubscribeSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        email = serializer.validated_data['email']
        source = serializer.validated_data.get('source', 'landing')

        # Check if already subscribed
        existing = Subscriber.objects.filter(email=email).first()
        if existing:
            if existing.is_active:
                return Response(
                    {'email': ['This email is already subscribed.']},
                    status=status.HTTP_400_BAD_REQUEST
                )
            # Reactivate if previously unsubscribed
            existing.is_active = True
            existing.unsubscribed_at = None
            existing.save(update_fields=['is_active', 'unsubscribed_at', 'updated_at'])
            self._send_confirmation(email)
            return Response(
                {'message': 'Successfully resubscribed!', 'email': email},
                status=status.HTTP_201_CREATED
            )

        # Create new subscriber
        Subscriber.objects.create(
            email=email,
            source=source,
            ip_address=self.get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', '')[:500],
        )
        self._send_confirmation(email)

        return Response(
            {'message': 'Successfully subscribed!', 'email': email},
            status=status.HTTP_201_CREATED
        )


class UnsubscribeView(APIView):
    """
    Public, unauthenticated one-click unsubscribe (RFC 8058).

    Accepts both GET (a human clicking the link in the email body, or in the
    frontend confirmation page) and POST (what mail clients send
    automatically for a List-Unsubscribe-Post header, no user interaction).
    Both do the same thing and are idempotent - re-visiting an already-used
    link just confirms the existing unsubscribed state instead of erroring.
    """

    permission_classes = [AllowAny]

    def _process(self, token):
        try:
            kind, identifier = parse_unsubscribe_token(token)
        except signing.BadSignature:
            return None, 'This unsubscribe link is invalid.'

        if kind == 'subscriber':
            try:
                subscriber = Subscriber.objects.get(id=identifier)
            except (Subscriber.DoesNotExist, ValueError, ValidationError):
                return None, 'This unsubscribe link is no longer valid.'
            if subscriber.is_active:
                subscriber.is_active = False
                subscriber.unsubscribed_at = timezone.now()
                subscriber.save(update_fields=['is_active', 'unsubscribed_at', 'updated_at'])
            return subscriber.email, None

        if kind == 'user':
            try:
                user = User.objects.get(id=identifier)
            except (User.DoesNotExist, ValueError, ValidationError):
                return None, 'This unsubscribe link is no longer valid.'
            prefs = user.preferences or {}
            if prefs.get('email_notifications', True):
                prefs['email_notifications'] = False
                user.preferences = prefs
                user.save(update_fields=['preferences', 'updated_at'])
            return user.email, None

        return None, 'This unsubscribe link is invalid.'

    def get(self, request, token):
        email, error = self._process(token)
        if error:
            return Response({'error': error}, status=status.HTTP_400_BAD_REQUEST)
        return Response({'email': email, 'message': 'You have been unsubscribed.'})

    def post(self, request, token):
        return self.get(request, token)
