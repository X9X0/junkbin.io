import logging

from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from rest_framework.views import APIView

from utils.email import send_templated_email

from .models import Subscriber
from .serializers import SubscribeSerializer

logger = logging.getLogger(__name__)


class SubscribeRateThrottle(AnonRateThrottle):
    """Rate limit for newsletter subscriptions: 10 per hour per IP."""
    rate = '10/hour'


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
