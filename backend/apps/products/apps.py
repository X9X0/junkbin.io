from django.apps import AppConfig


class ProductsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.products'
    verbose_name = 'Product Documentation'

    def ready(self):
        # Pillow has no built-in AVIF codec; importing this registers
        # encode/decode support process-wide (needed before any Image.open()
        # on an .avif upload, including inside ImageKit's thumbnail generation).
        import pillow_avif  # noqa: F401
