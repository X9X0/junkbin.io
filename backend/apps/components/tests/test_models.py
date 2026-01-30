"""
Unit tests for components app models.
"""
import pytest
from apps.components.models import Component, ProductComponent


class TestComponentUsageCount:
    """Tests for Component denormalized usage count."""

    def test_update_usage_count(self, component_factory, product_component_factory):
        """update_usage_count updates the denormalized count."""
        component = component_factory(usage_count=0)

        # Link component to multiple products
        product_component_factory(component=component)
        product_component_factory(component=component)
        product_component_factory(component=component)

        component.update_usage_count()

        component.refresh_from_db()
        assert component.usage_count == 3

    def test_usage_count_on_link(self, component_factory, product_component_factory, product_factory):
        """Usage count increments when linked to new product."""
        component = component_factory(usage_count=0)
        product = product_factory()

        # Creating a ProductComponent should increment usage_count
        pc = product_component_factory(component=component, product=product)

        component.refresh_from_db()
        assert component.usage_count == 1

    def test_usage_count_on_unlink(self, component_factory, product_component_factory, product_factory):
        """Usage count decrements when unlinked from product."""
        component = component_factory(usage_count=0)
        product = product_factory()

        pc = product_component_factory(component=component, product=product)
        component.refresh_from_db()
        assert component.usage_count == 1

        pc.delete()

        component.refresh_from_db()
        assert component.usage_count == 0


class TestComponentStr:
    """Tests for Component string representation."""

    def test_str_representation(self, component_factory):
        """String representation includes manufacturer and part number."""
        component = component_factory(
            manufacturer='Texas Instruments',
            part_number='LM7805'
        )

        result = str(component)
        assert 'Texas Instruments' in result
        assert 'LM7805' in result


class TestProductComponent:
    """Tests for ProductComponent model."""

    def test_str_with_reference_designator(self, product_component_factory, product_factory, component_factory):
        """String includes reference designator when present."""
        product = product_factory(manufacturer='Acme', model_number='Widget')
        component = component_factory(manufacturer='TI', part_number='LM317')
        pc = product_component_factory(
            product=product,
            component=component,
            reference_designator='U1'
        )

        result = str(pc)
        assert 'U1' in result
        assert 'LM317' in result

    def test_str_without_reference_designator(self, product_component_factory, product_factory, component_factory):
        """String shows product and component without designator."""
        product = product_factory(manufacturer='Test', model_number='Device')
        component = component_factory(manufacturer='Vendor', part_number='PART123')
        pc = product_component_factory(
            product=product,
            component=component,
            reference_designator=''
        )

        result = str(pc)
        assert 'PART123' in result

    def test_updates_counts_on_save(self, product_component_factory, product_factory, component_factory):
        """Creating ProductComponent updates both product and component counts."""
        product = product_factory(component_count=0)
        component = component_factory(usage_count=0)

        pc = product_component_factory(product=product, component=component)

        product.refresh_from_db()
        component.refresh_from_db()

        assert product.component_count == 1
        assert component.usage_count == 1

    def test_updates_counts_on_delete(self, product_component_factory, product_factory, component_factory):
        """Deleting ProductComponent updates both product and component counts."""
        product = product_factory(component_count=0)
        component = component_factory(usage_count=0)

        pc = product_component_factory(product=product, component=component)

        product.refresh_from_db()
        component.refresh_from_db()
        assert product.component_count == 1
        assert component.usage_count == 1

        pc.delete()

        product.refresh_from_db()
        component.refresh_from_db()
        assert product.component_count == 0
        assert component.usage_count == 0


class TestComponentTraits:
    """Tests for component factory traits."""

    def test_verified_trait(self, component_factory):
        """Verified trait sets is_verified to True."""
        component = component_factory(verified=True)
        assert component.is_verified is True

    def test_regulator_trait(self, component_factory):
        """Regulator trait sets correct type and function."""
        component = component_factory(regulator=True)
        assert component.component_type == 'regulator'
        assert 'Regulator' in component.typical_function

    def test_mcu_trait(self, component_factory):
        """MCU trait sets correct type and function."""
        component = component_factory(mcu=True)
        assert component.component_type == 'mcu'
        assert 'Microcontroller' in component.typical_function


class TestProductComponentSubmissionLevel:
    """Tests for ProductComponent submission level."""

    def test_default_submission_level(self, product_component_factory):
        """Default submission level is basic."""
        pc = product_component_factory()
        assert pc.submission_level == 'basic'

    def test_advanced_trait(self, product_component_factory):
        """Advanced trait sets submission level correctly."""
        pc = product_component_factory(advanced=True)
        assert pc.submission_level == 'advanced'
