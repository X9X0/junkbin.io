from django.contrib import admin

from .models import BackgroundRemovalPreview


@admin.register(BackgroundRemovalPreview)
class BackgroundRemovalPreviewAdmin(admin.ModelAdmin):
    list_display = ['id', 'created_by', 'status', 'model_name', 'alpha_matting', 'created_at']
    list_filter = ['status', 'model_name', 'alpha_matting']
    search_fields = ['id', 'created_by__username']
    readonly_fields = ['id', 'created_at', 'updated_at']

    def has_add_permission(self, request):
        return False
