"""
Management command to rebuild search vectors for all products and components.
"""
from django.core.management.base import BaseCommand
from django.contrib.postgres.search import SearchVector


class Command(BaseCommand):
    help = 'Rebuild full-text search vectors for all products and components.'

    def handle(self, *args, **options):
        from apps.products.models import Product
        from apps.components.models import Component

        product_count = Product.objects.update(
            search_vector=(
                SearchVector('manufacturer', weight='A') +
                SearchVector('model_number', weight='A') +
                SearchVector('fcc_id', weight='B') +
                SearchVector('description', weight='C') +
                SearchVector('teardown_notes', weight='D')
            )
        )
        self.stdout.write(self.style.SUCCESS(
            f'Updated search vectors for {product_count} products'
        ))

        component_count = Component.objects.update(
            search_vector=(
                SearchVector('part_number', weight='A') +
                SearchVector('manufacturer', weight='A') +
                SearchVector('typical_function', weight='B') +
                SearchVector('description', weight='C')
            )
        )
        self.stdout.write(self.style.SUCCESS(
            f'Updated search vectors for {component_count} components'
        ))
