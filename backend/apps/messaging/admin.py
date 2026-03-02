"""
Messaging admin configuration for Junkbin.io
"""
from django.contrib import admin

from .models import Conversation, Message, MessageAttachment, UserBlock


class MessageAttachmentInline(admin.TabularInline):
    model = MessageAttachment
    extra = 0
    readonly_fields = ['id', 'original_filename', 'file_type', 'file_size', 'uploaded_at']
    can_delete = True


class MessageInline(admin.TabularInline):
    model = Message
    extra = 0
    readonly_fields = ['id', 'sender', 'content', 'is_read', 'created_at']
    can_delete = True


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ['id', 'participant_1', 'participant_2', 'created_at', 'updated_at']
    list_filter = ['created_at']
    search_fields = ['participant_1__username', 'participant_2__username']
    readonly_fields = ['id', 'created_at', 'updated_at']
    raw_id_fields = ['participant_1', 'participant_2']
    inlines = [MessageInline]


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ['id', 'conversation', 'sender', 'content_preview', 'is_read', 'created_at']
    list_filter = ['is_read', 'created_at']
    search_fields = ['sender__username', 'content']
    readonly_fields = ['id', 'conversation', 'sender', 'created_at']
    raw_id_fields = ['conversation', 'sender']
    inlines = [MessageAttachmentInline]

    def content_preview(self, obj):
        return obj.content[:80] + '...' if len(obj.content) > 80 else obj.content
    content_preview.short_description = 'Content'


@admin.register(UserBlock)
class UserBlockAdmin(admin.ModelAdmin):
    list_display = ['id', 'blocker', 'blocked_user', 'created_at']
    search_fields = ['blocker__username', 'blocked_user__username']
    readonly_fields = ['id', 'created_at']
    raw_id_fields = ['blocker', 'blocked_user']
