"""
Factory definitions for components app models.
"""
import factory
import pytest

from apps.components.models import Component, ProductComponent


class ComponentFactory(factory.django.DjangoModelFactory):
    """Factory for creating Component instances."""

    class Meta:
        model = Component
        skip_postgeneration_save = True

    part_number = factory.Sequence(lambda n: f'PART{n:05d}')
    manufacturer = factory.Sequence(lambda n: f'ComponentMfr{n}')
    component_type = 'ic'
    package_type = 'SOIC-8'
    description = factory.Faker('sentence')
    typical_function = 'General purpose IC'
    is_verified = False
    usage_count = 0

    created_by = factory.SubFactory('apps.users.tests.factories.UserFactory')

    class Params:
        verified = factory.Trait(
            is_verified=True,
        )
        regulator = factory.Trait(
            component_type='regulator',
            typical_function='Voltage Regulator',
        )
        mcu = factory.Trait(
            component_type='mcu',
            typical_function='Microcontroller',
        )
        capacitor = factory.Trait(
            component_type='capacitor',
            package_type='0805',
        )


class ProductComponentFactory(factory.django.DjangoModelFactory):
    """Factory for creating ProductComponent instances."""

    class Meta:
        model = ProductComponent

    product = factory.SubFactory('apps.products.tests.factories.ProductFactory')
    component = factory.SubFactory(ComponentFactory)
    reference_designator = factory.Sequence(lambda n: f'U{n}')
    quantity = 1
    location_description = factory.Faker('sentence')
    submission_level = 'basic'
    is_verified = False

    created_by = factory.SubFactory('apps.users.tests.factories.UserFactory')

    class Params:
        verified = factory.Trait(
            is_verified=True,
        )
        advanced = factory.Trait(
            submission_level='advanced',
        )


@pytest.fixture
def component_factory(db):
    """Pytest fixture for ComponentFactory."""
    return ComponentFactory


@pytest.fixture
def product_component_factory(db):
    """Pytest fixture for ProductComponentFactory."""
    return ProductComponentFactory
