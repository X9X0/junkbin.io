"""
Tests for the backfill_component_values management command.
"""
from io import StringIO

import pytest
from django.core.management import call_command

pytestmark = pytest.mark.django_db


def run_command(product, dry_run=False):
    out = StringIO()
    args = ['--product', str(product.id)]
    if dry_run:
        args.append('--dry-run')
    call_command('backfill_component_values', *args, stdout=out)
    return out.getvalue()


class TestBackfillComponentValues:
    def test_populates_resistance_from_notes(self, product_factory, component_factory, product_component_factory):
        product = product_factory()
        component = component_factory(component_type='resistor', specifications={})
        product_component_factory(
            product=product,
            component=component,
            notes='METAL GLAZE 4.7K 5% | 1/10W',
        )

        run_command(product)

        component.refresh_from_db()
        assert component.specifications['resistance_ohm'] == 4700.0
        assert component.primary_value == '4.7 kΩ'

    def test_does_not_overwrite_existing_value(self, product_factory, component_factory, product_component_factory):
        product = product_factory()
        component = component_factory(component_type='resistor', specifications={'resistance_ohm': 999})
        product_component_factory(
            product=product,
            component=component,
            notes='METAL GLAZE 4.7K 5% | 1/10W',
        )

        run_command(product)

        component.refresh_from_db()
        assert component.specifications['resistance_ohm'] == 999

    def test_dry_run_does_not_save(self, product_factory, component_factory, product_component_factory):
        product = product_factory()
        component = component_factory(component_type='capacitor', specifications={})
        product_component_factory(
            product=product,
            component=component,
            notes='5% CERAMIC CHIP 470PF | 50V',
        )

        run_command(product, dry_run=True)

        component.refresh_from_db()
        assert component.specifications == {}

    def test_unparseable_notes_left_untouched(self, product_factory, component_factory, product_component_factory):
        product = product_factory()
        component = component_factory(component_type='inductor', specifications={})
        product_component_factory(
            product=product,
            component=component,
            notes='TRAP, LC',
        )

        output = run_command(product)

        component.refresh_from_db()
        assert component.specifications == {}
        assert 'TRAP, LC' in output

    def test_populates_description_from_notes(self, product_factory, component_factory, product_component_factory):
        product = product_factory()
        component = component_factory(component_type='resistor', specifications={}, description='')
        product_component_factory(
            product=product,
            component=component,
            notes='METAL GLAZE 4.7K 5% | 1/10W',
        )

        run_command(product)

        component.refresh_from_db()
        assert component.description == 'Metal glaze resistor, ±5% tolerance, 1/10W'

    def test_does_not_overwrite_existing_description(self, product_factory, component_factory, product_component_factory):
        product = product_factory()
        component = component_factory(component_type='resistor', specifications={}, description='Hand-verified note')
        product_component_factory(
            product=product,
            component=component,
            notes='METAL GLAZE 4.7K 5% | 1/10W',
        )

        run_command(product)

        component.refresh_from_db()
        assert component.description == 'Hand-verified note'

    def test_unrecognized_construction_leaves_description_blank(self, product_factory, component_factory, product_component_factory):
        product = product_factory()
        component = component_factory(component_type='resistor', specifications={}, description='')
        product_component_factory(
            product=product,
            component=component,
            notes='SOLID 1M 20% | 1/2W',
        )

        run_command(product)

        component.refresh_from_db()
        assert component.description == ''
        # value is still recovered even when the construction type isn't recognized for description
        assert component.specifications['resistance_ohm'] == 1_000_000.0

    def test_ignores_other_products(self, product_factory, component_factory, product_component_factory):
        product = product_factory()
        other_product = product_factory()
        component = component_factory(component_type='resistor', specifications={})
        product_component_factory(
            product=other_product,
            component=component,
            notes='METAL GLAZE 4.7K 5% | 1/10W',
        )

        run_command(product)

        component.refresh_from_db()
        assert component.specifications == {}
