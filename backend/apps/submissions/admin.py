"""
Submission admin configuration for Junkbin.io
"""
from django.contrib import admin
from django.utils import timezone

from .models import Submission, SubmissionComment


class SubmissionCommentInline(admin.TabularInline):
    """Inline admin for submission comments."""

    model = SubmissionComment
    extra = 0
    readonly_fields = ['author', 'created_at']


@admin.register(Submission)
class SubmissionAdmin(admin.ModelAdmin):
    """Admin for submissions."""

    list_display = [
        'id', 'submission_type', 'submission_level', 'status',
        'product', 'submitted_by', 'submitted_at',
        'reviewed_by', 'reviewed_at', 'auto_approved'
    ]
    list_filter = [
        'status', 'submission_type', 'submission_level',
        'auto_approved', 'submitted_at'
    ]
    search_fields = [
        'submitted_by__username', 'product__manufacturer',
        'product__model_number', 'changes_summary'
    ]
    readonly_fields = [
        'id', 'submitted_by', 'submitted_at',
        'reviewed_at', 'auto_approved'
    ]
    ordering = ['-submitted_at']
    date_hierarchy = 'submitted_at'

    fieldsets = (
        (None, {'fields': (
            'id', 'submission_type', 'submission_level', 'status'
        )}),
        ('Content', {'fields': (
            'product', 'changes_summary', 'changes_data'
        )}),
        ('Submission Info', {'fields': (
            'submitted_by', 'submitted_at', 'auto_approved'
        )}),
        ('Review Info', {'fields': (
            'reviewed_by', 'reviewed_at', 'review_notes'
        )}),
    )

    inlines = [SubmissionCommentInline]

    actions = ['approve_submissions', 'reject_submissions']

    @admin.action(description='Approve selected submissions')
    def approve_submissions(self, request, queryset):
        count = 0
        for submission in queryset.filter(status='pending'):
            submission.approve(request.user, 'Bulk approved via admin')
            count += 1
        self.message_user(request, f'{count} submissions approved.')

    @admin.action(description='Reject selected submissions')
    def reject_submissions(self, request, queryset):
        count = 0
        for submission in queryset.filter(status='pending'):
            submission.reject(request.user, 'Bulk rejected via admin')
            count += 1
        self.message_user(request, f'{count} submissions rejected.')


@admin.register(SubmissionComment)
class SubmissionCommentAdmin(admin.ModelAdmin):
    """Admin for submission comments."""

    list_display = ['submission', 'author', 'content_preview', 'created_at']
    list_filter = ['created_at']
    search_fields = ['author__username', 'content']
    readonly_fields = ['id', 'created_at', 'updated_at']
    ordering = ['-created_at']

    def content_preview(self, obj):
        return obj.content[:50] + '...' if len(obj.content) > 50 else obj.content
    content_preview.short_description = 'Content'
