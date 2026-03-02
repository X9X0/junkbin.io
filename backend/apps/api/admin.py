"""
Admin registration for notification, analytics, and security models.
"""
from django.conf import settings
from django.contrib import admin, messages
from django.utils.html import format_html

from axes.models import AccessAttempt
from axes.admin import AccessAttemptAdmin as _DefaultAccessAttemptAdmin

from .models import NotificationPreference, NotificationLog, SearchQuery


# ---------------------------------------------------------------------------
# Custom AccessAttempt admin — replaces the axes default with:
#   • Lock Status column (shows LOCKED / OK with failure counter)
#   • "Locked" list filter to see only locked accounts at a glance
#   • "Reset lockout" action that is clearly labelled
#   • Locked records sorted to the top by default
# ---------------------------------------------------------------------------

class _LockedFilter(admin.SimpleListFilter):
    title = 'lock status'
    parameter_name = 'locked'

    def lookups(self, request, model_admin):
        limit = getattr(settings, 'AXES_FAILURE_LIMIT', 5)
        return [
            ('yes', f'Locked (≥{limit} failures)'),
            ('no', 'Active (not locked)'),
        ]

    def queryset(self, request, queryset):
        limit = getattr(settings, 'AXES_FAILURE_LIMIT', 5)
        if self.value() == 'yes':
            return queryset.filter(failures_since_start__gte=limit)
        if self.value() == 'no':
            return queryset.filter(failures_since_start__lt=limit)
        return queryset


@admin.action(description='Reset lockout — unlock selected users/IPs')
def _reset_lockout(modeladmin, request, queryset):
    count = queryset.count()
    queryset.delete()
    messages.success(
        request,
        f'Cleared {count} access attempt record(s). Affected users can now log in.',
    )


admin.site.unregister(AccessAttempt)


@admin.register(AccessAttempt)
class AccessAttemptAdmin(admin.ModelAdmin):
    list_display = ('username', 'ip_address', 'lock_status', 'attempt_time', 'user_agent')
    list_filter = (_LockedFilter, 'attempt_time')
    search_fields = ('username', 'ip_address', 'user_agent')
    readonly_fields = (
        'username', 'ip_address', 'user_agent', 'http_accept', 'path_info',
        'get_data', 'post_data', 'failures_since_start', 'attempt_time', 'expiration',
    )
    ordering = ('-failures_since_start', '-attempt_time')
    actions = [_reset_lockout]

    def lock_status(self, obj):
        limit = getattr(settings, 'AXES_FAILURE_LIMIT', 5)
        if obj.failures_since_start >= limit:
            return format_html(
                '<span style="color:#e74c3c;font-weight:bold">'
                '\U0001f512 LOCKED ({}/{})'
                '</span>',
                obj.failures_since_start, limit,
            )
        return format_html(
            '<span style="color:#27ae60">\u2714 {}/{}</span>',
            obj.failures_since_start, limit,
        )
    lock_status.short_description = 'Status'

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.action(description='Send daily digest now')
def send_digest_now(modeladmin, request, queryset):
    from .tasks import send_daily_digest
    send_daily_digest.delay()
    messages.success(request, 'Daily digest task queued.')


@admin.register(NotificationPreference)
class NotificationPreferenceAdmin(admin.ModelAdmin):
    list_display = ('user', 'enabled', 'digest_mode', 'updated_at')
    list_filter = ('enabled', 'digest_mode')
    search_fields = ('user__username', 'user__email')
    actions = [send_digest_now]
    fieldsets = (
        ('User', {'fields': ('user',)}),
        ('General', {'fields': ('enabled', 'digest_mode')}),
        ('System Alerts', {
            'fields': ('system_health', 'system_performance', 'task_failures'),
        }),
        ('Moderation Alerts', {
            'fields': ('new_submission', 'new_report', 'new_user_review'),
        }),
        ('Community & Content', {
            'fields': ('new_member', 'new_subscriber', 'new_content'),
            'classes': ('collapse',),
        }),
    )


@admin.register(NotificationLog)
class NotificationLogAdmin(admin.ModelAdmin):
    list_display = ('category', 'subject', 'recipient_count', 'status', 'sent_at')
    list_filter = ('category', 'status', 'sent_at')
    search_fields = ('subject',)
    readonly_fields = (
        'category', 'subject', 'recipients', 'sent_at',
        'status', 'error_message',
    )
    ordering = ('-sent_at',)

    def recipient_count(self, obj):
        return len(obj.recipients) if obj.recipients else 0
    recipient_count.short_description = 'Recipients'

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(SearchQuery)
class SearchQueryAdmin(admin.ModelAdmin):
    list_display = ('query', 'result_count', 'search_type', 'user', 'created_at')
    list_filter = ('search_type', 'created_at')
    search_fields = ('query',)
    readonly_fields = (
        'id', 'query', 'user', 'result_count', 'search_type',
        'ip_address', 'created_at',
    )
    ordering = ('-created_at',)
    date_hierarchy = 'created_at'

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
