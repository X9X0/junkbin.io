from django.contrib import admin
from .models import WebhookEndpoint, WebhookDelivery


@admin.register(WebhookEndpoint)
class WebhookEndpointAdmin(admin.ModelAdmin):
    list_display = ['name', 'platform', 'is_active', 'event_list', 'created_at']
    list_filter = ['platform', 'is_active']
    search_fields = ['name']
    readonly_fields = ['id', 'created_at', 'updated_at']

    def event_list(self, obj):
        return ', '.join(obj.events) if obj.events else '-'
    event_list.short_description = 'Subscribed events'


@admin.register(WebhookDelivery)
class WebhookDeliveryAdmin(admin.ModelAdmin):
    list_display = ['event_type', 'endpoint', 'success', 'status_code', 'attempted_at']
    list_filter = ['success', 'event_type', 'endpoint']
    readonly_fields = [
        'id', 'endpoint', 'event_type', 'payload',
        'status_code', 'response_body', 'success', 'attempted_at',
    ]
    ordering = ['-attempted_at']

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
