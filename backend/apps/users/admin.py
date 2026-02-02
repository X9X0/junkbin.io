"""
User admin configuration for Junkbin.io
"""
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _

from .models import User, UserActivity, AdminAuditLog


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Custom User admin with extended fields."""

    list_display = [
        'username', 'email', 'is_trusted', 'is_moderator',
        'reputation_score', 'contribution_count', 'report_count',
        'email_verified', 'is_active', 'created_at'
    ]
    list_filter = [
        'is_trusted', 'is_moderator', 'is_staff', 'is_superuser',
        'is_active', 'email_verified', 'oauth_provider'
    ]
    search_fields = ['username', 'email', 'first_name', 'last_name']
    ordering = ['-created_at']
    readonly_fields = [
        'id', 'created_at', 'updated_at', 'email_verified_at',
        'last_contribution_at', 'last_login'
    ]

    fieldsets = (
        (None, {'fields': ('id', 'username', 'password')}),
        (_('Personal info'), {'fields': (
            'first_name', 'last_name', 'email', 'bio',
            'avatar', 'location', 'website'
        )}),
        (_('Authentication'), {'fields': (
            'oauth_provider', 'email_verified', 'email_verified_at'
        )}),
        (_('Reputation'), {'fields': (
            'reputation_score', 'contribution_count',
            'report_count', 'review_count', 'last_contribution_at'
        )}),
        (_('Permissions'), {'fields': (
            'is_active', 'is_staff', 'is_superuser',
            'is_trusted', 'is_moderator', 'groups', 'user_permissions'
        )}),
        (_('Preferences'), {'fields': ('preferences',)}),
        (_('Important dates'), {'fields': (
            'last_login', 'date_joined', 'created_at', 'updated_at'
        )}),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': (
                'username', 'email', 'password1', 'password2',
                'is_staff', 'is_trusted', 'is_moderator'
            ),
        }),
    )

    actions = ['make_trusted', 'revoke_trusted', 'make_moderator', 'revoke_moderator']

    @admin.action(description='Grant trusted status to selected users')
    def make_trusted(self, request, queryset):
        for user in queryset:
            if not user.is_trusted:
                user.is_trusted = True
                user.save(update_fields=['is_trusted'])
                AdminAuditLog.log_action(
                    request,
                    AdminAuditLog.ActionType.USER_TRUSTED,
                    user,
                    {'previous_value': False}
                )
        self.message_user(request, f'{queryset.count()} users granted trusted status.')

    @admin.action(description='Revoke trusted status from selected users')
    def revoke_trusted(self, request, queryset):
        for user in queryset:
            if user.is_trusted:
                user.is_trusted = False
                user.save(update_fields=['is_trusted'])
                AdminAuditLog.log_action(
                    request,
                    AdminAuditLog.ActionType.USER_UNTRUSTED,
                    user,
                    {'previous_value': True}
                )
        self.message_user(request, f'Trusted status revoked from {queryset.count()} users.')

    @admin.action(description='Make selected users moderators')
    def make_moderator(self, request, queryset):
        for user in queryset:
            if not user.is_moderator:
                user.is_moderator = True
                user.save(update_fields=['is_moderator'])
                AdminAuditLog.log_action(
                    request,
                    AdminAuditLog.ActionType.USER_MODERATOR,
                    user,
                    {'previous_value': False}
                )
        self.message_user(request, f'{queryset.count()} users granted moderator status.')

    @admin.action(description='Revoke moderator status from selected users')
    def revoke_moderator(self, request, queryset):
        for user in queryset:
            if user.is_moderator:
                user.is_moderator = False
                user.save(update_fields=['is_moderator'])
                AdminAuditLog.log_action(
                    request,
                    AdminAuditLog.ActionType.USER_UNMODERATOR,
                    user,
                    {'previous_value': True}
                )
        self.message_user(request, f'Moderator status revoked from {queryset.count()} users.')


@admin.register(UserActivity)
class UserActivityAdmin(admin.ModelAdmin):
    """Admin for user activity logs."""

    list_display = ['user', 'activity_type', 'ip_address', 'created_at']
    list_filter = ['activity_type', 'created_at']
    search_fields = ['user__username', 'user__email']
    readonly_fields = ['id', 'user', 'activity_type', 'details', 'ip_address', 'user_agent', 'created_at']
    ordering = ['-created_at']

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(AdminAuditLog)
class AdminAuditLogAdmin(admin.ModelAdmin):
    """Admin for viewing admin action audit logs."""

    list_display = ['created_at', 'admin_user', 'action_type', 'target_model', 'target_repr']
    list_filter = ['action_type', 'target_model', 'created_at']
    search_fields = ['admin_user__username', 'target_repr', 'target_id']
    readonly_fields = [
        'id', 'admin_user', 'action_type', 'target_model', 'target_id',
        'target_repr', 'details', 'ip_address', 'created_at'
    ]
    ordering = ['-created_at']
    date_hierarchy = 'created_at'

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        # Only superusers can delete audit logs
        return request.user.is_superuser
