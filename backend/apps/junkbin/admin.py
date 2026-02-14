"""
Junkbin admin configuration for Junkbin.io
"""
from django.contrib import admin

from .models import JunkbinItem


@admin.register(JunkbinItem)
class JunkbinItemAdmin(admin.ModelAdmin):
    list_display = [
        'user', 'item_type', 'content_type', 'object_id',
        'status', 'condition', 'visibility', 'quantity', 'created_at',
    ]
    list_filter = ['item_type', 'status', 'condition', 'visibility', 'content_type']
    search_fields = ['user__username', 'notes']
    readonly_fields = ['id', 'created_at', 'updated_at']
    raw_id_fields = ['user']
