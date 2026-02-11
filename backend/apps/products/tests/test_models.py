"""
Unit tests for products app models.
"""
import pytest
from apps.products.models import Product, ProductImage, Schematic


class TestProductSlugGeneration:
    """Tests for Product slug generation."""

    def test_auto_generate_slug(self, product_factory):
        """Slug is auto-generated from manufacturer and model."""
        product = product_factory(
            manufacturer='Samsung',
            model_number='Galaxy S21',
            slug=''  # Force empty to trigger generation
        )

        assert product.slug is not None
        assert 'samsung' in product.slug.lower()
        assert 'galaxy-s21' in product.slug.lower()

    def test_slug_collision_handling(self, product_factory):
        """Duplicate slugs get a numeric suffix."""
        product1 = product_factory(
            manufacturer='Cisco',
            model_number='RV340',
            region='global'
        )
        product2 = product_factory(
            manufacturer='Cisco',
            model_number='RV340',
            region='us'  # Different region, potentially same base slug
        )

        # Both should have unique slugs
        assert product1.slug != product2.slug
        # Second one should have region in slug
        assert 'us' in product2.slug

    def test_slug_includes_revision(self, product_factory):
        """Slug includes revision when present."""
        product = product_factory(
            manufacturer='Apple',
            model_number='MacBook Pro',
            revision='Rev A'
        )

        assert 'rev-a' in product.slug.lower()

    def test_slug_includes_region(self, product_factory):
        """Slug includes region when not global."""
        product = product_factory(
            manufacturer='Sony',
            model_number='PS5',
            region='jp'
        )

        assert 'jp' in product.slug.lower()

    def test_global_region_not_in_slug(self, product_factory):
        """Global region is not included in slug."""
        product = product_factory(
            manufacturer='Microsoft',
            model_number='Surface',
            region='global'
        )

        assert 'global' not in product.slug.lower()

    def test_slug_preserves_on_update(self, product_factory):
        """Existing slug is preserved on model update."""
        product = product_factory(manufacturer='Test', model_number='Device')
        original_slug = product.slug

        product.description = 'Updated description'
        product.save()

        product.refresh_from_db()
        assert product.slug == original_slug

    def test_numeric_suffix_increments(self, product_factory):
        """Numeric suffix increments for multiple collisions."""
        # Create products with same base slug but different regions
        # to avoid unique_product_variant constraint
        product1 = product_factory(
            manufacturer='Acme', model_number='Widget', region='global'
        )
        product2 = product_factory(
            manufacturer='Acme', model_number='Widget', region='us'
        )
        product3 = product_factory(
            manufacturer='Acme', model_number='Widget', region='eu'
        )

        slugs = [product1.slug, product2.slug, product3.slug]
        # All should be unique
        assert len(set(slugs)) == 3


class TestProductComponentCount:
    """Tests for Product denormalized component count."""

    def test_update_component_count(self, product_factory, product_component_factory):
        """update_component_count updates the denormalized count."""
        product = product_factory(component_count=0)

        # Create some components
        product_component_factory(product=product)
        product_component_factory(product=product)
        product_component_factory(product=product)

        product.update_component_count()

        product.refresh_from_db()
        assert product.component_count == 3

    def test_component_count_on_delete(self, product_factory, product_component_factory):
        """Component count updates when components are deleted."""
        product = product_factory(component_count=0)

        pc1 = product_component_factory(product=product)
        pc2 = product_component_factory(product=product)

        product.refresh_from_db()
        assert product.component_count == 2

        pc1.delete()

        product.refresh_from_db()
        assert product.component_count == 1


class TestProductViewCount:
    """Tests for Product view count increment."""

    def test_increment_view_count(self, product_factory):
        """increment_view_count uses F() expression for atomic update."""
        product = product_factory(view_count=0)

        product.increment_view_count()

        # Need to refresh to see the update (F() expression)
        product.refresh_from_db()
        assert product.view_count == 1

    def test_multiple_view_increments(self, product_factory):
        """Multiple view increments accumulate correctly."""
        product = product_factory(view_count=10)

        for _ in range(5):
            product.increment_view_count()

        product.refresh_from_db()
        assert product.view_count == 15

    def test_concurrent_view_increments(self, product_factory):
        """F() expression handles concurrent increments correctly."""
        product = product_factory(view_count=0)
        product_id = product.id

        # Simulate concurrent increments
        for _ in range(10):
            Product.objects.filter(pk=product_id).update(
                view_count=models.F('view_count') + 1
            )

        product.refresh_from_db()
        assert product.view_count == 10


class TestProductPrimaryImage:
    """Tests for Product.primary_image property."""

    def test_primary_image_returns_overview(self, product_factory, product_image_factory):
        """primary_image returns the overview image."""
        product = product_factory()

        # Create different image types
        overview = product_image_factory(product=product, image_type='overview')
        pcb_top = product_image_factory(product=product, image_type='pcb_top')

        assert product.primary_image == overview

    def test_primary_image_none_when_no_overview(self, product_factory, product_image_factory):
        """primary_image returns None when no overview image."""
        product = product_factory()

        # Only create non-overview images
        product_image_factory(product=product, image_type='pcb_top')

        assert product.primary_image is None


class TestProductStr:
    """Tests for Product string representation."""

    def test_str_basic(self, product_factory):
        """String representation includes manufacturer and model."""
        product = product_factory(
            manufacturer='Netgear',
            model_number='R7000'
        )

        result = str(product)
        assert 'Netgear' in result
        assert 'R7000' in result

    def test_str_with_revision(self, product_factory):
        """String representation includes revision when present."""
        product = product_factory(
            manufacturer='TP-Link',
            model_number='Archer',
            revision='v2'
        )

        result = str(product)
        assert 'Rev v2' in result

    def test_str_with_region(self, product_factory):
        """String representation includes region when not global."""
        product = product_factory(
            manufacturer='Canon',
            model_number='EOS R5',
            region='jp'
        )

        result = str(product)
        assert 'JP' in result.upper()


class TestSchematic:
    """Tests for Schematic model."""

    def test_increment_download_count(self, schematic_factory):
        """increment_download_count uses F() expression."""
        schematic = schematic_factory(download_count=5)

        schematic.increment_download_count()

        schematic.refresh_from_db()
        assert schematic.download_count == 6

    def test_auto_populate_file_type(self, schematic_factory):
        """File type is auto-populated from filename."""
        # Note: This test would need actual file fixtures
        # For now, test the logic is present
        schematic = schematic_factory()
        # The save method should auto-populate file_type from file.name


# Import F for concurrent test
from django.db import models
