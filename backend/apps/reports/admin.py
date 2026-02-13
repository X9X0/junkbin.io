"""
Report admin configuration for Junkbin.io
"""
from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html

from .models import Report, UserReview
from apps.users.models import AdminAuditLog


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    """Admin for reports."""

    list_display = [
        'id', 'reason', 'status', 'reporter', 'reported_user',
        'content_type', 'counted_as_strike', 'created_at'
    ]
    list_filter = [
        'status', 'reason', 'counted_as_strike', 'created_at'
    ]
    search_fields = [
        'reporter__username', 'reported_user__username',
        'description', 'resolution_notes'
    ]
    readonly_fields = [
        'id', 'reporter', 'created_at', 'resolved_at'
    ]
    ordering = ['-created_at']
    date_hierarchy = 'created_at'

    fieldsets = (
        (None, {'fields': (
            'id', 'content_type', 'object_id'
        )}),
        ('Report Details', {'fields': (
            'reason', 'description', 'reporter', 'reported_user'
        )}),
        ('Status', {'fields': (
            'status', 'counted_as_strike'
        )}),
        ('Resolution', {'fields': (
            'resolved_by', 'resolved_at', 'resolution_notes'
        )}),
        ('Timestamps', {'fields': ('created_at',)}),
    )

    actions = [
        'resolve_as_valid', 'resolve_as_invalid', 'dismiss_reports'
    ]

    @admin.action(description='Resolve as valid (apply strike)')
    def resolve_as_valid(self, request, queryset):
        count = 0
        for report in queryset.filter(status='pending'):
            report.resolve_as_valid(request.user, 'Bulk resolved via admin')
            count += 1
        self.message_user(request, f'{count} reports resolved as valid.')

    @admin.action(description='Resolve as invalid')
    def resolve_as_invalid(self, request, queryset):
        count = 0
        for report in queryset.filter(status='pending'):
            report.resolve_as_invalid(request.user, 'Bulk resolved via admin')
            count += 1
        self.message_user(request, f'{count} reports resolved as invalid.')

    @admin.action(description='Dismiss reports')
    def dismiss_reports(self, request, queryset):
        count = 0
        for report in queryset.filter(status='pending'):
            report.dismiss(request.user, 'Bulk dismissed via admin')
            count += 1
        self.message_user(request, f'{count} reports dismissed.')


class RelatedReportsInline(admin.TabularInline):
    """Inline for related reports in user reviews."""

    model = UserReview.related_reports.through
    extra = 0
    readonly_fields = ['report']

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(UserReview)
class UserReviewAdmin(admin.ModelAdmin):
    """Admin for user reviews."""

    list_display = [
        'id', 'user', 'review_type', 'status',
        'trigger_report_count', 'created_at', 'reviewed_at', 'reviewer'
    ]
    list_filter = [
        'status', 'review_type', 'created_at'
    ]
    search_fields = [
        'user__username', 'notes', 'action_taken'
    ]
    readonly_fields = [
        'id', 'user', 'review_type', 'triggered_by',
        'trigger_report_count', 'created_at', 'contribution_review_link'
    ]
    ordering = ['-created_at']
    date_hierarchy = 'created_at'

    fieldsets = (
        (None, {'fields': (
            'id', 'user', 'contribution_review_link', 'review_type', 'triggered_by', 'trigger_report_count'
        )}),
        ('Status', {'fields': ('status',)}),
        ('Review', {'fields': (
            'reviewer', 'reviewed_at', 'notes', 'action_taken'
        )}),
        ('Timestamps', {'fields': ('created_at',)}),
    )

    def contribution_review_link(self, obj):
        url = reverse('admin-user-contributions', args=[obj.user_id])
        return format_html('<a href="{}">Review All Contributions</a>', url)
    contribution_review_link.short_description = 'Contribution Review'

    actions = ['clear_users', 'issue_warnings', 'suspend_users']

    @admin.action(description='Clear selected reviews')
    def clear_users(self, request, queryset):
        count = 0
        for review in queryset.filter(status='pending'):
            review.complete_review(
                request.user,
                UserReview.Status.CLEARED,
                'Bulk cleared via admin'
            )
            AdminAuditLog.log_action(
                request,
                AdminAuditLog.ActionType.OTHER,
                review.user,
                {'action': 'user_review_cleared', 'review_id': str(review.id)}
            )
            count += 1
        self.message_user(request, f'{count} users cleared.')

    @admin.action(description='Issue warnings')
    def issue_warnings(self, request, queryset):
        count = 0
        for review in queryset.filter(status='pending'):
            review.complete_review(
                request.user,
                UserReview.Status.WARNING_ISSUED,
                'Warning issued via admin'
            )
            AdminAuditLog.log_action(
                request,
                AdminAuditLog.ActionType.OTHER,
                review.user,
                {'action': 'warning_issued', 'review_id': str(review.id)}
            )
            count += 1
        self.message_user(request, f'{count} warnings issued.')

    @admin.action(description='SUSPEND users (deactivates accounts)')
    def suspend_users(self, request, queryset):
        count = 0
        for review in queryset.filter(status='pending'):
            review.complete_review(
                request.user,
                UserReview.Status.SUSPENDED,
                'Suspended via admin bulk action'
            )
            # Log this critical action
            AdminAuditLog.log_action(
                request,
                AdminAuditLog.ActionType.USER_SUSPENDED,
                review.user,
                {
                    'review_id': str(review.id),
                    'review_type': review.review_type,
                    'trigger_report_count': review.trigger_report_count,
                }
            )
            count += 1
        self.message_user(
            request,
            f'{count} users suspended. This action has been logged.',
            level='warning'
        )
