"""
Admin registration for notification and analytics models.
"""
from django.contrib import admin, messages

from .models import NotificationPreference, NotificationLog, SearchQuery


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
