import csv

from django.contrib import admin
from django.http import HttpResponse

from .models import Subscriber


@admin.register(Subscriber)
class SubscriberAdmin(admin.ModelAdmin):
    list_display = ['email', 'source', 'is_active', 'created_at']
    list_filter = ['source', 'is_active', 'created_at']
    search_fields = ['email']
    readonly_fields = ['id', 'ip_address', 'user_agent', 'created_at', 'updated_at']
    date_hierarchy = 'created_at'
    actions = ['export_as_csv']

    @admin.action(description='Export selected subscribers as CSV')
    def export_as_csv(self, request, queryset):
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="subscribers.csv"'

        writer = csv.writer(response)
        writer.writerow(['Email', 'Source', 'Active', 'Created At'])

        for subscriber in queryset:
            writer.writerow([
                subscriber.email,
                subscriber.source,
                subscriber.is_active,
                subscriber.created_at.isoformat(),
            ])

        return response
