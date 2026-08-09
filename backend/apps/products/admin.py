"""
Product admin configuration for Junkbin.io
"""
import csv

from django.contrib import admin
from django.http import HttpResponse
from django.utils.html import format_html

from .models import Product, ProductImage, ProductComment, Schematic, Firmware, ComponentSuggestion


class ProductImageInline(admin.TabularInline):
    """Inline admin for product images."""

    model = ProductImage
    extra = 1
    readonly_fields = ['thumbnail_preview', 'uploaded_at', 'uploaded_by']
    fields = [
        'thumbnail_preview', 'image', 'image_type',
        'caption', 'display_order', 'uploaded_by', 'uploaded_at'
    ]

    def thumbnail_preview(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" style="max-height: 100px; max-width: 100px;" />',
                obj.image.url
            )
        return '-'
    thumbnail_preview.short_description = 'Preview'


class SchematicInline(admin.TabularInline):
    """Inline admin for schematics."""

    model = Schematic
    extra = 0
    readonly_fields = ['uploaded_by', 'uploaded_at', 'download_count']
    fields = [
        'title', 'schematic_type', 'file', 'source_type',
        'is_approved', 'download_count', 'uploaded_by', 'uploaded_at'
    ]


class FirmwareInline(admin.TabularInline):
    """Inline admin for firmware."""

    model = Firmware
    extra = 0
    readonly_fields = ['uploaded_by', 'uploaded_at', 'download_count']
    fields = [
        'title', 'version', 'file', 'source_type',
        'is_approved', 'download_count', 'uploaded_by', 'uploaded_at'
    ]


class ProductCommentInline(admin.TabularInline):
    """Inline admin for product comments."""

    model = ProductComment
    extra = 0
    readonly_fields = ['author', 'created_at']
    fields = ['author', 'content', 'created_at']


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    """Admin for products."""

    list_display = [
        'manufacturer', 'model_number', 'revision', 'region',
        'category', 'fcc_id', 'component_count', 'is_approved', 'is_featured',
        'created_by', 'created_at'
    ]
    list_filter = [
        'is_approved', 'is_featured', 'category', 'region',
        'created_at'
    ]
    search_fields = [
        'manufacturer', 'model_number', 'fcc_id',
        'description', 'part_number'
    ]
    readonly_fields = [
        'id', 'slug', 'component_count', 'view_count',
        'created_by', 'created_at', 'updated_at'
    ]
    ordering = ['-created_at']
    date_hierarchy = 'created_at'

    fieldsets = (
        (None, {'fields': (
            'id', 'slug', 'manufacturer', 'model_number', 'revision'
        )}),
        ('Classification', {'fields': (
            'category', 'subcategory', 'region', 'year_manufactured'
        )}),
        ('Identifiers', {
            'fields': ('fcc_id', 'ic_id', 'part_number'),
            'description': 'FCC ID can be looked up at fcc.gov/oet/ea/fccid'
        }),
        ('Description', {'fields': (
            'description', 'teardown_notes'
        )}),
        ('Status', {'fields': (
            'is_approved', 'is_featured'
        )}),
        ('Statistics', {'fields': (
            'component_count', 'view_count'
        )}),
        ('Metadata', {'fields': (
            'created_by', 'created_at', 'updated_at'
        )}),
    )

    inlines = [ProductImageInline, SchematicInline, FirmwareInline, ProductCommentInline]

    actions = ['approve_products', 'unapprove_products', 'feature_products', 'export_as_csv']

    @admin.action(description='Approve selected products')
    def approve_products(self, request, queryset):
        updated = queryset.update(is_approved=True)
        self.message_user(request, f'{updated} products approved.')

    @admin.action(description='Unapprove selected products')
    def unapprove_products(self, request, queryset):
        updated = queryset.update(is_approved=False)
        self.message_user(request, f'{updated} products unapproved.')

    @admin.action(description='Feature selected products')
    def feature_products(self, request, queryset):
        updated = queryset.update(is_featured=True)
        self.message_user(request, f'{updated} products featured.')

    @admin.action(description='Export selected products as CSV')
    def export_as_csv(self, request, queryset):
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="products.csv"'

        writer = csv.writer(response)
        writer.writerow([
            'Manufacturer', 'Model Number', 'Revision', 'Region',
            'Category', 'Subcategory', 'Year', 'FCC ID',
            'Component Count', 'Approved', 'Featured', 'Created At'
        ])

        for product in queryset:
            writer.writerow([
                product.manufacturer, product.model_number,
                product.revision, product.region,
                product.category, product.subcategory,
                product.year_manufactured or '', product.fcc_id,
                product.component_count, product.is_approved,
                product.is_featured, product.created_at.isoformat()
            ])

        return response


@admin.register(ProductImage)
class ProductImageAdmin(admin.ModelAdmin):
    """Admin for product images."""

    list_display = [
        'product', 'image_type', 'caption', 'display_order',
        'uploaded_by', 'uploaded_at'
    ]
    list_filter = ['image_type', 'uploaded_at']
    search_fields = ['product__manufacturer', 'product__model_number', 'caption']
    readonly_fields = [
        'id', 'image_preview', 'width', 'height',
        'file_size', 'uploaded_by', 'uploaded_at'
    ]
    ordering = ['-uploaded_at']

    fieldsets = (
        (None, {'fields': ('id', 'product', 'image', 'image_preview')}),
        ('Details', {'fields': (
            'image_type', 'caption', 'display_order'
        )}),
        ('Technical', {'fields': (
            'width', 'height', 'file_size'
        )}),
        ('Metadata', {'fields': (
            'uploaded_by', 'uploaded_at'
        )}),
    )

    def image_preview(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" style="max-height: 300px; max-width: 300px;" />',
                obj.image.url
            )
        return '-'
    image_preview.short_description = 'Preview'


@admin.register(Schematic)
class SchematicAdmin(admin.ModelAdmin):
    """
    Admin for schematics and service documentation.

    Right to Repair: This section manages technical documentation
    that enables independent device repair.
    """

    list_display = [
        'title', 'product', 'schematic_type', 'source_type',
        'file_type', 'download_count', 'is_approved',
        'uploaded_by', 'uploaded_at'
    ]
    list_filter = [
        'schematic_type', 'source_type', 'is_approved',
        'file_type', 'uploaded_at'
    ]
    search_fields = [
        'title', 'description', 'product__manufacturer',
        'product__model_number', 'source_notes'
    ]
    readonly_fields = [
        'id', 'file_type', 'file_size', 'download_count',
        'uploaded_by', 'uploaded_at', 'updated_at'
    ]
    ordering = ['-uploaded_at']
    date_hierarchy = 'uploaded_at'
    autocomplete_fields = ['product']

    fieldsets = (
        (None, {'fields': (
            'id', 'product', 'title', 'schematic_type'
        )}),
        ('File', {'fields': (
            'file', 'file_type', 'file_size', 'version', 'page_count'
        )}),
        ('Description', {'fields': (
            'description', 'repair_relevance'
        )}),
        ('Source & Attribution', {
            'fields': (
                'source_type', 'source_url', 'source_notes'
            ),
            'description': 'Properly attribute sources to respect copyright while supporting Right to Repair.'
        }),
        ('Status', {'fields': (
            'is_approved', 'download_count'
        )}),
        ('Metadata', {'fields': (
            'uploaded_by', 'uploaded_at', 'updated_at'
        )}),
    )

    actions = ['approve_schematics', 'unapprove_schematics']

    @admin.action(description='Approve selected schematics')
    def approve_schematics(self, request, queryset):
        updated = queryset.update(is_approved=True)
        self.message_user(request, f'{updated} schematics approved.')

    @admin.action(description='Unapprove selected schematics')
    def unapprove_schematics(self, request, queryset):
        updated = queryset.update(is_approved=False)
        self.message_user(request, f'{updated} schematics unapproved.')


@admin.register(Firmware)
class FirmwareAdmin(admin.ModelAdmin):
    """
    Admin for recovered firmware binaries.

    Right to Repair: preserved firmware images let owners re-flash
    devices bricked by a failed update or a swapped flash chip.
    """

    list_display = [
        'title', 'product', 'version', 'source_type',
        'file_type', 'download_count', 'is_approved',
        'uploaded_by', 'uploaded_at'
    ]
    list_filter = [
        'source_type', 'is_approved', 'file_type', 'uploaded_at'
    ]
    search_fields = [
        'title', 'description', 'product__manufacturer',
        'product__model_number', 'chip_architecture', 'source_notes'
    ]
    readonly_fields = [
        'id', 'file_type', 'file_size', 'download_count',
        'uploaded_by', 'uploaded_at', 'updated_at'
    ]
    ordering = ['-uploaded_at']
    date_hierarchy = 'uploaded_at'
    autocomplete_fields = ['product']

    fieldsets = (
        (None, {'fields': (
            'id', 'product', 'title', 'version', 'chip_architecture'
        )}),
        ('File', {'fields': (
            'file', 'file_type', 'file_size'
        )}),
        ('Description', {'fields': (
            'description',
        )}),
        ('Source & Attribution', {
            'fields': (
                'source_type', 'source_url', 'source_notes'
            ),
            'description': 'Properly attribute sources to respect copyright while supporting Right to Repair.'
        }),
        ('Status', {'fields': (
            'is_approved', 'download_count'
        )}),
        ('Metadata', {'fields': (
            'uploaded_by', 'uploaded_at', 'updated_at'
        )}),
    )

    actions = ['approve_firmware', 'unapprove_firmware']

    @admin.action(description='Approve selected firmware')
    def approve_firmware(self, request, queryset):
        updated = queryset.update(is_approved=True)
        self.message_user(request, f'{updated} firmware files approved.')

    @admin.action(description='Unapprove selected firmware')
    def unapprove_firmware(self, request, queryset):
        updated = queryset.update(is_approved=False)
        self.message_user(request, f'{updated} firmware files unapproved.')


@admin.register(ComponentSuggestion)
class ComponentSuggestionAdmin(admin.ModelAdmin):
    """
    Read-mostly oversight for machine-extracted component suggestions.

    Real review (approve → creates Component + ProductComponent, or
    reject) happens through the moderation dashboard, since approving
    requires the conversion logic in ComponentSuggestionViewSet.approve -
    this admin view is for browsing/spot-deleting the queue.
    """

    list_display = [
        'part_number', 'manufacturer', 'reference_designator', 'product',
        'source_type', 'confidence', 'uploaded_by', 'uploaded_at'
    ]
    list_filter = ['source_type', 'confidence', 'uploaded_at']
    search_fields = [
        'part_number', 'manufacturer', 'reference_designator',
        'product__manufacturer', 'product__model_number', 'extraction_context'
    ]
    readonly_fields = ['id', 'uploaded_by', 'uploaded_at', 'matched_component']
    ordering = ['-uploaded_at']
    date_hierarchy = 'uploaded_at'
    autocomplete_fields = ['product']


@admin.register(ProductComment)
class ProductCommentAdmin(admin.ModelAdmin):
    """Admin for product comments."""

    list_display = ['product', 'author', 'content_preview', 'created_at']
    list_filter = ['created_at']
    search_fields = ['author__username', 'content', 'product__manufacturer', 'product__model_number']
    readonly_fields = ['id', 'created_at', 'updated_at']
    ordering = ['-created_at']

    def content_preview(self, obj):
        return obj.content[:80] + '...' if len(obj.content) > 80 else obj.content
    content_preview.short_description = 'Content'
