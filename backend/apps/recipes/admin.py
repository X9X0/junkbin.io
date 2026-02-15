"""
Recipe admin configuration for Junkbin.io
"""
from django.contrib import admin

from .models import Recipe, RecipeComponent


class RecipeComponentInline(admin.TabularInline):
    """Inline admin for recipe BOM items."""

    model = RecipeComponent
    extra = 1
    autocomplete_fields = ['component']
    fields = ['component', 'quantity', 'notes', 'is_optional']


@admin.register(Recipe)
class RecipeAdmin(admin.ModelAdmin):
    """Admin for recipes."""

    list_display = [
        'name', 'category', 'difficulty', 'component_count',
        'is_approved', 'is_featured', 'created_by', 'created_at',
    ]
    list_filter = [
        'is_approved', 'is_featured', 'category', 'difficulty', 'created_at',
    ]
    search_fields = ['name', 'description']
    readonly_fields = [
        'id', 'slug', 'component_count', 'view_count',
        'build_count', 'created_by', 'created_at', 'updated_at',
    ]
    ordering = ['-created_at']
    date_hierarchy = 'created_at'

    fieldsets = (
        (None, {'fields': (
            'id', 'slug', 'name', 'description',
        )}),
        ('Classification', {'fields': (
            'category', 'difficulty', 'estimated_time',
        )}),
        ('Links & Media', {'fields': (
            'external_url', 'image',
        )}),
        ('Status', {'fields': (
            'is_approved', 'is_featured',
        )}),
        ('Statistics', {'fields': (
            'component_count', 'view_count', 'build_count',
        )}),
        ('Metadata', {'fields': (
            'created_by', 'created_at', 'updated_at',
        )}),
    )

    inlines = [RecipeComponentInline]

    actions = ['approve_recipes', 'unapprove_recipes']

    @admin.action(description='Approve selected recipes')
    def approve_recipes(self, request, queryset):
        updated = queryset.update(is_approved=True)
        self.message_user(request, f'{updated} recipes approved.')

    @admin.action(description='Unapprove selected recipes')
    def unapprove_recipes(self, request, queryset):
        updated = queryset.update(is_approved=False)
        self.message_user(request, f'{updated} recipes unapproved.')
