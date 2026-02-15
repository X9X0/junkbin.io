"""
User serializers for Junkbin.io API
"""
from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    """Public user profile serializer."""

    display_name = serializers.CharField(read_only=True)
    badges = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id', 'username', 'display_name', 'bio', 'avatar',
            'location', 'website', 'reputation_score',
            'contribution_count', 'is_trusted', 'created_at', 'badges'
        ]
        read_only_fields = [
            'id', 'reputation_score', 'contribution_count',
            'is_trusted', 'created_at'
        ]

    def get_badges(self, obj):
        from apps.users.badges import get_user_badges_display
        return get_user_badges_display(obj)


class UserDetailSerializer(serializers.ModelSerializer):
    """Detailed user serializer for profile owner."""

    display_name = serializers.CharField(read_only=True)
    badges = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name',
            'display_name', 'bio', 'avatar', 'location', 'website',
            'reputation_score', 'contribution_count', 'report_count',
            'is_trusted', 'is_moderator', 'email_verified',
            'oauth_provider', 'preferences', 'created_at', 'updated_at',
            'last_contribution_at', 'badges'
        ]
        read_only_fields = [
            'id', 'email', 'reputation_score', 'contribution_count',
            'report_count', 'is_trusted', 'is_moderator', 'email_verified',
            'oauth_provider', 'created_at', 'updated_at', 'last_contribution_at'
        ]

    def get_badges(self, obj):
        from apps.users.badges import get_user_badges_display
        return get_user_badges_display(obj)


class UserRegistrationSerializer(serializers.ModelSerializer):
    """Serializer for user registration."""

    password = serializers.CharField(
        write_only=True,
        required=True,
        validators=[validate_password],
        style={'input_type': 'password'}
    )
    password_confirm = serializers.CharField(
        write_only=True,
        required=True,
        style={'input_type': 'password'}
    )

    class Meta:
        model = User
        fields = ['username', 'email', 'password', 'password_confirm']

    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError({
                'password_confirm': "Password fields didn't match."
            })
        return attrs

    def create(self, validated_data):
        validated_data.pop('password_confirm')
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            password=validated_data['password']
        )
        return user


class UserStatsSerializer(serializers.Serializer):
    """Serializer for user statistics."""

    total_contributions = serializers.IntegerField()
    approved_products = serializers.IntegerField()
    approved_components = serializers.IntegerField()
    pending_submissions = serializers.IntegerField()
    reports_submitted = serializers.IntegerField()
    reports_received = serializers.IntegerField()
    reputation_rank = serializers.IntegerField()


class PasswordChangeSerializer(serializers.Serializer):
    """Serializer for password change."""

    current_password = serializers.CharField(
        required=True,
        style={'input_type': 'password'}
    )
    new_password = serializers.CharField(
        required=True,
        validators=[validate_password],
        style={'input_type': 'password'}
    )
    new_password_confirm = serializers.CharField(
        required=True,
        style={'input_type': 'password'}
    )

    def validate_current_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError('Current password is incorrect.')
        return value

    def validate(self, attrs):
        if attrs['new_password'] != attrs['new_password_confirm']:
            raise serializers.ValidationError({
                'new_password_confirm': "New passwords didn't match."
            })
        return attrs


class PreferencesSerializer(serializers.Serializer):
    """Serializer for user preferences."""

    # Master toggle — when off, all notification emails are suppressed
    email_notifications = serializers.BooleanField(default=True)
    # Granular notification categories
    notify_messages = serializers.BooleanField(default=True)
    notify_submissions = serializers.BooleanField(default=True)
    notify_reports = serializers.BooleanField(default=True)
    notify_account = serializers.BooleanField(default=True)
    notify_junkbin = serializers.BooleanField(default=True)
    # UI preferences
    dark_mode = serializers.BooleanField(default=True)
    show_advanced_fields = serializers.BooleanField(default=False)


class PasswordResetRequestSerializer(serializers.Serializer):
    """Serializer for password reset request."""

    email = serializers.EmailField(required=True)


class PasswordResetConfirmSerializer(serializers.Serializer):
    """Serializer for password reset confirmation."""

    uid = serializers.CharField(required=True)
    token = serializers.CharField(required=True)
    new_password = serializers.CharField(
        required=True,
        validators=[validate_password],
        style={'input_type': 'password'}
    )
    new_password_confirm = serializers.CharField(
        required=True,
        style={'input_type': 'password'}
    )

    def validate(self, attrs):
        if attrs['new_password'] != attrs['new_password_confirm']:
            raise serializers.ValidationError({
                'new_password_confirm': "New passwords didn't match."
            })
        return attrs
