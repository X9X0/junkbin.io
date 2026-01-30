"""
Component admin configuration for Junkbin.io
"""
from django.contrib import admin

from .models import Component, ProductComponent


class ProductComponentInline(admin.TabularInline):
    """Inline admin for product-component relationships."""

    model = ProductComponent
    extra = 0
    readonly_fields = ['created_by', 'created_at', 'is_verified', 'verified_by', 'verified_at']
    autocomplete_fields = ['product', 'component']


@admin.register(Component)
class ComponentAdmin(admin.ModelAdmin):
    """Admin for components."""

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

    actions = ['verify_components']

    @admin.action(description='Verify selected components')
    def verify_components(self, request, queryset):
        updated = queryset.update(is_verified=True)
        self.message_user(request, f'{updated} components verified.')


@admin.register(ProductComponent)
class ProductComponentAdmin(admin.ModelAdmin):
    """Admin for product-component relationships."""

    list_display = [
        'product', 'component', 'reference_designator', 'quantity',
        'board_name', 'submission_level', 'is_verified', 'created_at'
    ]
    list_filter = [
        'submission_level', 'is_verified', 'created_at'
    ]
    search_fields = [
        'product__manufacturer', 'product__model_number',
        'component__part_number', 'component__manufacturer',
        'reference_designator', 'board_name'
    ]
    readonly_fields = [
        'id', 'created_by', 'created_at', 'updated_at',
        'verified_by', 'verified_at'
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
        ('Metadata', {'fields': (
            'created_by', 'created_at', 'updated_at'
        )}),
    )

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
