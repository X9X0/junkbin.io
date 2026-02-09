"""
Submission serializers for Junkbin.io API
"""
from rest_framework import serializers
from django.contrib.auth import get_user_model

from .models import Submission, SubmissionComment

User = get_user_model()


class UserMinimalSerializer(serializers.ModelSerializer):
    """Minimal user serializer."""

    class Meta:
        model = User
        fields = ['id', 'username', 'is_trusted', 'is_moderator']


class SubmissionCommentSerializer(serializers.ModelSerializer):
    """Serializer for submission comments."""

    author = UserMinimalSerializer(read_only=True)

    class Meta:
        model = SubmissionComment
        fields = ['id', 'author', 'content', 'created_at', 'updated_at']
        read_only_fields = ['id', 'author', 'created_at', 'updated_at']


class SubmissionListSerializer(serializers.ModelSerializer):
    """Serializer for submission list view."""

    submitted_by = UserMinimalSerializer(read_only=True)
    reviewed_by = UserMinimalSerializer(read_only=True)
    submission_type_display = serializers.CharField(
        source='get_submission_type_display',
        read_only=True
    )
    status_display = serializers.CharField(
        source='get_status_display',
        read_only=True
    )
    product_name = serializers.SerializerMethodField()

    class Meta:
        model = Submission
        fields = [
            'id', 'submission_type', 'submission_type_display',
            'submission_level', 'status', 'status_display',
            'product', 'product_name', 'changes_summary',
            'submitted_by', 'submitted_at', 'reviewed_by', 'reviewed_at',
            'auto_approved'
        ]

    def get_product_name(self, obj):
        if obj.product:
            return str(obj.product)
        return None


class SubmissionDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for single submission view."""

    submitted_by = UserMinimalSerializer(read_only=True)
    reviewed_by = UserMinimalSerializer(read_only=True)
    comments = SubmissionCommentSerializer(many=True, read_only=True)
    submission_type_display = serializers.CharField(
        source='get_submission_type_display',
        read_only=True
    )
    status_display = serializers.CharField(
        source='get_status_display',
        read_only=True
    )

    class Meta:
        model = Submission
        fields = [
            'id', 'submission_type', 'submission_type_display',
            'submission_level', 'status', 'status_display',
            'product', 'changes_summary', 'changes_data',
            'submitted_by', 'submitted_at',
            'reviewed_by', 'reviewed_at', 'review_notes',
            'auto_approved', 'comments'
        ]
        read_only_fields = [
            'id', 'submitted_by', 'submitted_at',
            'reviewed_by', 'reviewed_at', 'auto_approved'
        ]


class SubmissionCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating submissions."""

    class Meta:
        model = Submission
        fields = [
            'submission_type', 'submission_level', 'product',
            'changes_summary', 'changes_data'
        ]

    def create(self, validated_data):
        user = self.context['request'].user
        validated_data['submitted_by'] = user

        # Auto-approve for trusted users
        if user.can_submit_without_review:
            validated_data['status'] = Submission.Status.APPROVED
            validated_data['auto_approved'] = True

        return super().create(validated_data)


class SubmissionReviewSerializer(serializers.Serializer):
    """Serializer for submission review actions."""

    action = serializers.ChoiceField(
        choices=['approve', 'reject', 'request_changes']
    )
    notes = serializers.CharField(required=False, allow_blank=True, max_length=5000)


class SubmissionCommentCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating submission comments."""

    class Meta:
        model = SubmissionComment
        fields = ['content']

    def create(self, validated_data):
        validated_data['author'] = self.context['request'].user
        validated_data['submission'] = self.context['submission']
        return super().create(validated_data)
