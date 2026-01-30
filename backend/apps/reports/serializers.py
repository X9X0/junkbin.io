"""
Report serializers for Junkbin.io API
"""
from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType

from .models import Report, UserReview

User = get_user_model()


class UserMinimalSerializer(serializers.ModelSerializer):
    """Minimal user serializer."""

    class Meta:
        model = User
        fields = ['id', 'username', 'is_trusted', 'is_moderator']


class ReportListSerializer(serializers.ModelSerializer):
    """Serializer for report list view."""

    reporter = UserMinimalSerializer(read_only=True)
    reported_user = UserMinimalSerializer(read_only=True)
    reason_display = serializers.CharField(
        source='get_reason_display',
        read_only=True
    )
    status_display = serializers.CharField(
        source='get_status_display',
        read_only=True
    )
    content_type_name = serializers.SerializerMethodField()

    class Meta:
        model = Report
        fields = [
            'id', 'content_type', 'content_type_name', 'object_id',
            'reason', 'reason_display', 'description',
            'reporter', 'reported_user', 'created_at',
            'status', 'status_display', 'counted_as_strike'
        ]

    def get_content_type_name(self, obj):
        return obj.content_type.model


class ReportDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for single report view."""

    reporter = UserMinimalSerializer(read_only=True)
    reported_user = UserMinimalSerializer(read_only=True)
    resolved_by = UserMinimalSerializer(read_only=True)
    reason_display = serializers.CharField(
        source='get_reason_display',
        read_only=True
    )
    status_display = serializers.CharField(
        source='get_status_display',
        read_only=True
    )
    reported_item_data = serializers.SerializerMethodField()

    class Meta:
        model = Report
        fields = [
            'id', 'content_type', 'object_id', 'reported_item_data',
            'reason', 'reason_display', 'description',
            'reporter', 'reported_user', 'created_at',
            'status', 'status_display',
            'resolved_at', 'resolved_by', 'resolution_notes',
            'counted_as_strike'
        ]

    def get_reported_item_data(self, obj):
        """Get serialized data for the reported item."""
        item = obj.reported_item
        if not item:
            return None

        # Return basic info about the reported item
        model_name = obj.content_type.model
        data = {'type': model_name, 'id': str(obj.object_id)}

        if hasattr(item, 'manufacturer'):
            data['manufacturer'] = item.manufacturer
        if hasattr(item, 'model_number'):
            data['model_number'] = item.model_number
        if hasattr(item, 'part_number'):
            data['part_number'] = item.part_number
        if hasattr(item, '__str__'):
            data['display'] = str(item)

        return data


class ReportCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating reports."""

    content_type = serializers.CharField(write_only=True)
    object_id = serializers.UUIDField()

    class Meta:
        model = Report
        fields = ['content_type', 'object_id', 'reason', 'description']

    def validate_content_type(self, value):
        """Convert content type string to ContentType object."""
        try:
            app_label, model = value.split('.')
            ct = ContentType.objects.get(app_label=app_label, model=model)
            return ct
        except (ValueError, ContentType.DoesNotExist):
            raise serializers.ValidationError(
                'Invalid content type. Use format: app_label.model'
            )

    def validate(self, attrs):
        # Check that the object exists
        ct = attrs['content_type']
        object_id = attrs['object_id']

        model_class = ct.model_class()
        if not model_class.objects.filter(pk=object_id).exists():
            raise serializers.ValidationError({
                'object_id': 'Object not found.'
            })

        return attrs

    def create(self, validated_data):
        validated_data['reporter'] = self.context['request'].user

        # Get the reported user (owner of the content)
        ct = validated_data['content_type']
        object_id = validated_data['object_id']
        model_class = ct.model_class()
        item = model_class.objects.get(pk=object_id)

        if hasattr(item, 'created_by'):
            validated_data['reported_user'] = item.created_by

        return super().create(validated_data)


class ReportResolveSerializer(serializers.Serializer):
    """Serializer for resolving reports."""

    action = serializers.ChoiceField(
        choices=['valid', 'invalid', 'dismiss']
    )
    notes = serializers.CharField(required=False, allow_blank=True)


class UserReviewListSerializer(serializers.ModelSerializer):
    """Serializer for user review list view."""

    user = UserMinimalSerializer(read_only=True)
    reviewer = UserMinimalSerializer(read_only=True)
    review_type_display = serializers.CharField(
        source='get_review_type_display',
        read_only=True
    )
    status_display = serializers.CharField(
        source='get_status_display',
        read_only=True
    )

    class Meta:
        model = UserReview
        fields = [
            'id', 'user', 'review_type', 'review_type_display',
            'status', 'status_display', 'trigger_report_count',
            'created_at', 'reviewed_at', 'reviewer'
        ]


class UserReviewDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for user review."""

    user = UserMinimalSerializer(read_only=True)
    reviewer = UserMinimalSerializer(read_only=True)
    triggered_by = ReportListSerializer(read_only=True)
    related_reports = ReportListSerializer(many=True, read_only=True)
    review_type_display = serializers.CharField(
        source='get_review_type_display',
        read_only=True
    )
    status_display = serializers.CharField(
        source='get_status_display',
        read_only=True
    )

    class Meta:
        model = UserReview
        fields = [
            'id', 'user', 'review_type', 'review_type_display',
            'triggered_by', 'trigger_report_count',
            'status', 'status_display',
            'created_at', 'reviewed_at', 'reviewer',
            'notes', 'action_taken', 'related_reports'
        ]


class UserReviewCompleteSerializer(serializers.Serializer):
    """Serializer for completing user reviews."""

    status = serializers.ChoiceField(
        choices=['cleared', 'warning_issued', 'restricted', 'suspended']
    )
    notes = serializers.CharField(required=False, allow_blank=True)
    action_taken = serializers.CharField(required=False, allow_blank=True)
