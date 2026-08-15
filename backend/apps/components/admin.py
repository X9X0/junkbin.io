"""
Component admin configuration for Junkbin.io
"""
import csv

from django.contrib import admin
from django.http import HttpResponse, HttpResponseRedirect
from django.urls import reverse
from django.utils.html import format_html
from import_export.admin import ImportExportActionModelAdmin

from apps.products.models import Product

from .models import Component, ComponentImage, ComponentTypeImage, ComponentDatasheet, ProductComponent, ComponentVote, ComponentViewStats
from .resources import ComponentResource, ProductComponentResource


class ComponentProductFilter(admin.SimpleListFilter):
    """Filter the component list down to components used in one product's BOM.

    Component is the shared parts catalog (linked to products through the
    ProductComponent junction), so there's no direct FK to filter on -
    this goes through that reverse relation instead.
    """

    title = 'product (BOM)'
    parameter_name = 'product'

    def lookups(self, request, model_admin):
        products = Product.objects.order_by('manufacturer', 'model_number').values_list(
            'id', 'manufacturer', 'model_number'
        )
        return [(str(pid), f'{manufacturer} {model_number}') for pid, manufacturer, model_number in products]

    def queryset(self, request, queryset):
        if not self.value():
            return queryset
        return queryset.filter(product_components__product_id=self.value()).distinct()


class ComponentDatasheetInline(admin.TabularInline):
    """Inline admin for component datasheets."""

    model = ComponentDatasheet
    extra = 0
    readonly_fields = ['file_type', 'file_size', 'download_count', 'uploaded_by', 'uploaded_at']
    fields = [
        'title', 'version', 'file', 'source_type', 'source_url',
        'is_approved', 'file_type', 'file_size', 'download_count',
        'uploaded_by', 'uploaded_at',
    ]


class ComponentImageInline(admin.TabularInline):
    """Inline admin for component images."""

    model = ComponentImage
    extra = 1
    readonly_fields = ['thumbnail_preview', 'uploaded_at', 'uploaded_by']
    fields = [
        'thumbnail_preview', 'image', 'image_type',
        'caption', 'display_order', 'is_approved', 'uploaded_by', 'uploaded_at'
    ]

    def thumbnail_preview(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" style="max-height: 100px; max-width: 100px;" />',
                obj.image.url
            )
        return '-'
    thumbnail_preview.short_description = 'Preview'


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
        ComponentProductFilter, 'component_type', 'is_verified', 'created_at'
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

    inlines = [ComponentDatasheetInline, ComponentImageInline, ProductComponentInline]

    actions = ['verify_components', 'export_as_csv', 'bulk_edit_field']

    @admin.action(description='Verify selected components')
    def verify_components(self, request, queryset):
        updated = queryset.update(is_verified=True)
        self.message_user(request, f'{updated} components verified.')

    @admin.action(description='Bulk edit a field on selected components')
    def bulk_edit_field(self, request, queryset):
        # Selection can be larger than a URL comfortably carries (a full BOM
        # can be 500+ components), so hand it to the confirmation page via
        # the session rather than a querystring.
        request.session['bulk_edit_component_ids'] = list(
            str(pk) for pk in queryset.values_list('pk', flat=True)
        )
        return HttpResponseRedirect(reverse('admin-component-bulk-edit'))

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


@admin.register(ComponentViewStats)
class ComponentViewStatsAdmin(admin.ModelAdmin):
    list_display = ('component', 'date', 'view_count')
    list_filter = ('date',)
    search_fields = ('component__part_number', 'component__manufacturer')
    readonly_fields = ('component', 'date', 'view_count')
    ordering = ('-date', '-view_count')
    date_hierarchy = 'date'

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(ComponentImage)
class ComponentImageAdmin(admin.ModelAdmin):
    """Admin for component images."""

    list_display = [
        'component', 'image_type', 'caption', 'is_approved',
        'uploaded_by', 'uploaded_at'
    ]
    list_filter = ['image_type', 'is_approved', 'uploaded_at']
    search_fields = ['component__part_number', 'component__manufacturer', 'caption']
    readonly_fields = [
        'id', 'image_preview', 'width', 'height',
        'file_size', 'uploaded_by', 'uploaded_at'
    ]
    ordering = ['-uploaded_at']

    fieldsets = (
        (None, {'fields': ('id', 'component', 'image', 'image_preview')}),
        ('Details', {'fields': (
            'image_type', 'caption', 'display_order'
        )}),
        ('Technical', {'fields': (
            'width', 'height', 'file_size'
        )}),
        ('Status', {'fields': ('is_approved',)}),
        ('Metadata', {'fields': (
            'uploaded_by', 'uploaded_at'
        )}),
    )

    actions = ['approve_images']

    def image_preview(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" style="max-height: 300px; max-width: 300px;" />',
                obj.image.url
            )
        return '-'
    image_preview.short_description = 'Preview'

    @admin.action(description='Approve selected images')
    def approve_images(self, request, queryset):
        updated = queryset.update(is_approved=True)
        self.message_user(request, f'{updated} images approved.')


@admin.register(ComponentDatasheet)
class ComponentDatasheetAdmin(admin.ModelAdmin):
    """Admin for component datasheets."""

    list_display = [
        'title', 'component', 'version', 'source_type', 'file_type',
        'file_size_display', 'is_approved', 'download_count',
        'uploaded_by', 'uploaded_at',
    ]
    list_filter = ['source_type', 'file_type', 'is_approved', 'uploaded_at']
    search_fields = [
        'title', 'component__part_number', 'component__manufacturer',
        'source_url', 'source_notes',
    ]
    readonly_fields = [
        'file_type', 'file_size', 'download_count', 'uploaded_by', 'uploaded_at',
    ]
    ordering = ['-uploaded_at']
    autocomplete_fields = ['component']
    raw_id_fields = ['uploaded_by']

    fieldsets = (
        (None, {'fields': ('component', 'file', 'title', 'version')}),
        ('Source', {'fields': ('source_type', 'source_url', 'source_notes')}),
        ('Technical', {'fields': ('file_type', 'file_size')}),
        ('Status', {'fields': ('is_approved', 'download_count')}),
        ('Metadata', {'fields': ('uploaded_by', 'uploaded_at')}),
    )

    actions = ['approve_datasheets']

    @admin.action(description='Approve selected datasheets')
    def approve_datasheets(self, request, queryset):
        updated = queryset.update(is_approved=True)
        self.message_user(request, f'{updated} datasheets approved.')

    def file_size_display(self, obj):
        if obj.file_size:
            if obj.file_size >= 1024 * 1024:
                return f'{obj.file_size / (1024 * 1024):.1f} MB'
            return f'{obj.file_size / 1024:.0f} KB'
        return '-'
    file_size_display.short_description = 'Size'
    file_size_display.admin_order_field = 'file_size'


@admin.register(ComponentTypeImage)
class ComponentTypeImageAdmin(admin.ModelAdmin):
    """
    Admin for default component type images.

    Upload one image per component_type + package_type combo.
    Leave package_type blank for a type-wide default.
    """

    list_display = ['component_type', 'package_type', 'image_preview']
    list_filter = ['component_type']
    search_fields = ['component_type', 'package_type']
    readonly_fields = ['id', 'image_preview']

    fieldsets = (
        (None, {'fields': ('id', 'component_type', 'package_type', 'image', 'image_preview')}),
    )

    def image_preview(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" style="max-height: 100px; max-width: 100px;" />',
                obj.image.url
            )
        return '-'
    image_preview.short_description = 'Preview'
