from rest_framework import serializers

from .models import Subscriber


class SubscribeSerializer(serializers.Serializer):
    """Serializer for newsletter subscription input validation."""

    email = serializers.EmailField()
    source = serializers.ChoiceField(
        choices=Subscriber.SOURCE_CHOICES,
        default='landing',
        required=False
    )

    def validate_email(self, value):
        """Normalize email to lowercase."""
        return value.lower()
