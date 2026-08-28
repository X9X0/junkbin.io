from rest_framework import serializers

from .models import Notification, PushSubscription


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = [
            'id', 'category', 'title', 'body', 'url',
            'is_read', 'read_at', 'created_at',
        ]
        read_only_fields = fields


class PushSubscriptionKeysSerializer(serializers.Serializer):
    p256dh = serializers.CharField()
    auth = serializers.CharField()


class PushSubscribeSerializer(serializers.Serializer):
    """Matches the shape of the browser's PushSubscription.toJSON()."""
    endpoint = serializers.URLField(max_length=500)
    keys = PushSubscriptionKeysSerializer()

    def save(self, user, user_agent=''):
        endpoint = self.validated_data['endpoint']
        keys = self.validated_data['keys']
        subscription, _ = PushSubscription.objects.update_or_create(
            endpoint=endpoint,
            defaults={
                'user': user,
                'p256dh': keys['p256dh'],
                'auth': keys['auth'],
                'user_agent': user_agent[:300],
            },
        )
        return subscription
