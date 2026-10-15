"""Tests for admin-selectable product preview images."""
import pytest
from django.db import IntegrityError, transaction

from apps.products.models import ProductImage
from apps.products.serializers import ProductDetailSerializer


@pytest.mark.django_db
class TestPrimaryImageSelection:
    """Product.primary_image precedence and the single-primary guarantee."""

    def test_falls_back_to_first_overview_when_none_chosen(
            self, product_factory, product_image_factory):
        product = product_factory()
        first = product_image_factory(
            product=product, image_type='overview', display_order=0)
        product_image_factory(
            product=product, image_type='overview', display_order=1)

        assert product.primary_image == first

    def test_falls_back_to_any_image_when_no_overview(
            self, product_factory, product_image_factory):
        product = product_factory()
        detail = product_image_factory(product=product, image_type='detail')

        assert product.primary_image == detail

    def test_explicit_choice_wins_over_ordering(
            self, product_factory, product_image_factory):
        product = product_factory()
        product_image_factory(
            product=product, image_type='overview', display_order=0)
        chosen = product_image_factory(
            product=product, image_type='overview', display_order=5)

        chosen.make_primary()

        assert product.primary_image == chosen

    def test_explicit_choice_wins_over_image_type(
            self, product_factory, product_image_factory):
        """An admin may prefer a detail shot as the preview."""
        product = product_factory()
        product_image_factory(product=product, image_type='overview')
        detail = product_image_factory(product=product, image_type='detail')

        detail.make_primary()

        assert product.primary_image == detail

    def test_choosing_a_new_primary_clears_the_previous_one(
            self, product_factory, product_image_factory):
        product = product_factory()
        first = product_image_factory(product=product)
        second = product_image_factory(product=product)

        first.make_primary()
        second.make_primary()

        first.refresh_from_db()
        assert not first.is_primary
        assert product.primary_image == second
        assert ProductImage.objects.filter(
            product=product, is_primary=True).count() == 1

    def test_primary_is_scoped_per_product(
            self, product_factory, product_image_factory):
        """Two different products may each have their own preview image."""
        one, two = product_factory(), product_factory()
        first = product_image_factory(product=one)
        second = product_image_factory(product=two)

        first.make_primary()
        second.make_primary()

        assert one.primary_image == first
        assert two.primary_image == second

    def test_database_rejects_two_primaries_on_one_product(
            self, product_factory, product_image_factory):
        """The partial unique constraint holds even when save() is bypassed."""
        product = product_factory()
        first = product_image_factory(product=product)
        second = product_image_factory(product=product)
        first.make_primary()

        with pytest.raises(IntegrityError):
            with transaction.atomic():
                # .update() skips save(), so only the constraint can catch this
                ProductImage.objects.filter(pk=second.pk).update(is_primary=True)

    def test_clearing_the_flag_restores_the_fallback(
            self, product_factory, product_image_factory):
        product = product_factory()
        first = product_image_factory(
            product=product, image_type='overview', display_order=0)
        later = product_image_factory(
            product=product, image_type='overview', display_order=9)

        later.make_primary()
        assert product.primary_image == later

        later.is_primary = False
        later.save(update_fields=['is_primary'])

        assert product.primary_image == first


@pytest.mark.django_db
class TestDetailGalleryOrder:
    """The detail page gallery opens on the chosen preview image."""

    def _gallery_ids(self, product):
        return [img['id'] for img in ProductDetailSerializer(product).data['images']]

    def test_primary_image_comes_first(
            self, product_factory, product_image_factory):
        product = product_factory(is_approved=True)
        first = product_image_factory(
            product=product, display_order=0, is_approved=True)
        second = product_image_factory(
            product=product, display_order=1, is_approved=True)
        chosen = product_image_factory(
            product=product, display_order=2, is_approved=True)

        chosen.make_primary()

        assert self._gallery_ids(product) == [
            str(chosen.pk), str(first.pk), str(second.pk)]

    def test_display_order_kept_without_a_primary(
            self, product_factory, product_image_factory):
        product = product_factory(is_approved=True)
        first = product_image_factory(
            product=product, display_order=0, is_approved=True)
        second = product_image_factory(
            product=product, display_order=1, is_approved=True)

        assert self._gallery_ids(product) == [str(first.pk), str(second.pk)]
