"""
User serializers for Junkbin.io API
"""
from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.utils.translation import gettext_lazy as _

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
    forward_messages_to = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.filter(is_active=True),
        allow_null=True,
        required=False,
    )
    forward_messages_to_detail = UserSerializer(source='forward_messages_to', read_only=True)

    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name',
            'display_name', 'bio', 'avatar', 'location', 'website',
            'preferred_language',
            'reputation_score', 'contribution_count', 'report_count',
            'is_staff', 'is_trusted', 'is_moderator', 'email_verified',
            'oauth_provider', 'preferences', 'created_at', 'updated_at',
            'last_contribution_at', 'badges',
            'forward_messages_to', 'forward_messages_to_detail',
        ]
        read_only_fields = [
            'id', 'username', 'email', 'reputation_score', 'contribution_count',
            'report_count', 'is_staff', 'is_trusted', 'is_moderator',
            'email_verified', 'oauth_provider', 'created_at', 'updated_at',
            'last_contribution_at'
        ]

    def get_badges(self, obj):
        from apps.users.badges import get_user_badges_display
        return get_user_badges_display(obj)

    def validate_forward_messages_to(self, value):
        if value and self.instance and value.pk == self.instance.pk:
            raise serializers.ValidationError(_('You cannot forward your messages to yourself.'))
        return value


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
                'password_confirm': _("Password fields didn't match.")
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
            raise serializers.ValidationError(_('Current password is incorrect.'))
        return value

    def validate(self, attrs):
        if attrs['new_password'] != attrs['new_password_confirm']:
            raise serializers.ValidationError({
                'new_password_confirm': _("New passwords didn't match.")
            })
        return attrs


class CurrentPasswordConfirmMixin:
    """
    Shared password-confirmation logic for sensitive self-service actions
    (username change, account deletion). OAuth-only accounts have no
    usable password, so there's nothing to confirm against — their session
    is already the proof of identity.
    """

    def validate(self, attrs):
        user = self.context['request'].user
        if user.has_usable_password():
            current_password = attrs.get('current_password')
            if not current_password:
                raise serializers.ValidationError({
                    'current_password': _('Current password is required.')
                })
            if not user.check_password(current_password):
                raise serializers.ValidationError({
                    'current_password': _('Current password is incorrect.')
                })
        return attrs


class UsernameChangeSerializer(CurrentPasswordConfirmMixin, serializers.Serializer):
    """Serializer for self-service username change."""

    current_password = serializers.CharField(
        required=False,
        allow_blank=True,
        style={'input_type': 'password'}
    )
    new_username = serializers.CharField(required=True, max_length=150)

    def validate_new_username(self, value):
        user = self.context['request'].user
        User._meta.get_field('username').run_validators(value)
        if User.objects.exclude(pk=user.pk).filter(username__iexact=value).exists():
            raise serializers.ValidationError(_('This username is already taken.'))
        return value


class AccountDeleteSerializer(CurrentPasswordConfirmMixin, serializers.Serializer):
    """Serializer for self-service account deletion."""

    current_password = serializers.CharField(
        required=False,
        allow_blank=True,
        style={'input_type': 'password'}
    )


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
                'new_password_confirm': _("New passwords didn't match.")
            })
        return attrs
