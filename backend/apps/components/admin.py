"""
Component admin configuration for Junkbin.io
"""
import csv

from django.contrib import admin
from django.http import HttpResponse
from import_export.admin import ImportExportActionModelAdmin

from .models import Component, ProductComponent, ComponentVote
from .resources import ComponentResource, ProductComponentResource


class ProductComponentInline(admin.TabularInline):
    """Inline admin for product-component relationships."""

    model = ProductComponent
    extra = 0
    readonly_fields = ['created_by', 'created_at', 'is_verified', 'verified_by', 'verified_at']
    autocomplete_fields = ['product', 'component']


@admin.register(Component)
class ComponentAdmin(ImportExportActionModelAdmin):
    """Admin for components."""

    resource_classes = [ComponentResource]
    list_display = [
        'manufacturer', 'part_number', 'component_type', 'package_type',
        'typical_function', 'usage_count', 'is_verified', 'created_at'
    ]
    list_filter = [
        'component_type', 'is_verified', 'created_at'
    ]
    search_fields = [
        'part_number', 'manufacturer', 'description', 'typical_function'
    ]
    readonly_fields = [
        'id', 'usage_count', 'created_by', 'created_at', 'updated_at'
    ]
    ordering = ['-usage_count', 'manufacturer', 'part_number']
    autocomplete_fields = ['cross_references']

    fieldsets = (
        (None, {'fields': (
            'id', 'part_number', 'manufacturer', 'manufacturer_aliases'
        )}),
        ('Classification', {'fields': (
            'component_type', 'package_type', 'typical_function'
        )}),
        ('Description', {'fields': (
            'description', 'specifications'
        )}),
        ('External Links', {'fields': (
            'datasheet_url', 'octopart_url'
        )}),
        ('Cross References', {'fields': (
            'alternative_part_numbers', 'cross_references'
        )}),
        ('Status', {'fields': (
            'is_verified', 'usage_count'
        )}),
        ('Metadata', {'fields': (
            'created_by', 'created_at', 'updated_at'
        )}),
    )

    inlines = [ProductComponentInline]

    actions = ['verify_components', 'export_as_csv']

    @admin.action(description='Verify selected components')
    def verify_components(self, request, queryset):
        updated = queryset.update(is_verified=True)
        self.message_user(request, f'{updated} components verified.')

    @admin.action(description='Export selected as simple CSV')
    def export_as_csv(self, request, queryset):
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="components.csv"'

        writer = csv.writer(response)
        writer.writerow([
            'Manufacturer', 'Part Number', 'Type', 'Package',
            'Typical Function', 'Description', 'Datasheet URL',
            'Usage Count', 'Verified', 'Created At'
        ])

        for comp in queryset:
            writer.writerow([
                comp.manufacturer, comp.part_number,
                comp.component_type, comp.package_type,
                comp.typical_function, comp.description,
                comp.datasheet_url, comp.usage_count,
                comp.is_verified, comp.created_at.isoformat()
            ])

        return response


class ComponentVoteInline(admin.TabularInline):
    """Inline admin for component votes."""

    model = ComponentVote
    extra = 0
    readonly_fields = ['id', 'user', 'vote_type', 'weight', 'created_at', 'updated_at']
    raw_id_fields = ['user']


@admin.register(ProductComponent)
class ProductComponentAdmin(ImportExportActionModelAdmin):
    """Admin for product-component relationships."""

    resource_classes = [ProductComponentResource]
    list_display = [
        'product', 'component', 'reference_designator', 'quantity',
        'board_name', 'submission_level', 'is_verified', 'vote_score',
        'needs_review', 'created_at'
    ]
    list_filter = [
        'submission_level', 'is_verified', 'needs_review', 'created_at'
    ]
    search_fields = [
        'product__manufacturer', 'product__model_number',
        'component__part_number', 'component__manufacturer',
        'reference_designator', 'board_name'
    ]
    readonly_fields = [
        'id', 'created_by', 'created_at', 'updated_at',
        'verified_by', 'verified_at',
        'vote_score', 'confirm_count', 'dispute_count',
    ]
    ordering = ['-created_at']
    autocomplete_fields = ['product', 'component', 'image_reference']

    fieldsets = (
        (None, {'fields': (
            'id', 'product', 'component'
        )}),
        ('Location', {'fields': (
            'reference_designator', 'quantity',
            'location_description', 'board_name'
        )}),
        ('Details', {'fields': (
            'notes', 'image_reference', 'submission_level'
        )}),
        ('Verification', {'fields': (
            'is_verified', 'verified_by', 'verified_at'
        )}),
        ('Voting', {'fields': (
            'vote_score', 'confirm_count', 'dispute_count', 'needs_review'
        )}),
        ('Metadata', {'fields': (
            'created_by', 'created_at', 'updated_at'
        )}),
    )

    inlines = [ComponentVoteInline]

    actions = ['verify_mappings']

    @admin.action(description='Verify selected component mappings')
    def verify_mappings(self, request, queryset):
        from django.utils import timezone
        updated = queryset.update(
            is_verified=True,
            verified_by=request.user,
            verified_at=timezone.now()
        )
        self.message_user(request, f'{updated} mappings verified.')


@admin.register(ComponentVote)
class ComponentVoteAdmin(admin.ModelAdmin):
    """Admin for component votes."""

    list_display = [
        'user', 'product_component', 'vote_type', 'weight', 'created_at'
    ]
    list_filter = ['vote_type', 'created_at']
    search_fields = [
        'user__username',
        'product_component__component__part_number',
        'product_component__product__model_number',
    ]
    readonly_fields = [
        'id', 'product_component', 'user', 'vote_type',
        'weight', 'created_at', 'updated_at'
    ]
    raw_id_fields = ['user', 'product_component']
