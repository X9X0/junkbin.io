from django.contrib import admin

from .models import Notification, PushSubscription


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ['recipient', 'category', 'title', 'is_read', 'created_at']
    list_filter = ['category', 'is_read', 'created_at']
    search_fields = ['recipient__username', 'title', 'body']
    readonly_fields = ['id', 'created_at']
    raw_id_fields = ['recipient', 'actor']


@admin.register(PushSubscription)
class PushSubscriptionAdmin(admin.ModelAdmin):
    list_display = ['user', 'endpoint', 'user_agent', 'created_at']
    search_fields = ['user__username', 'endpoint']
    readonly_fields = ['id', 'created_at']
    raw_id_fields = ['user']
