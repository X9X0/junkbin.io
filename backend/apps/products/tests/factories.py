"""
Factory definitions for products app models.
"""
import factory
import pytest
from django.conf import settings

from apps.products.models import Product, ProductImage, Schematic


class ProductFactory(factory.django.DjangoModelFactory):
    """Factory for creating Product instances."""

    class Meta:
        model = Product
        skip_postgeneration_save = True

    manufacturer = factory.Sequence(lambda n: f'Manufacturer{n}')
    model_number = factory.Sequence(lambda n: f'Model-{n:04d}')
    revision = ''
    region = 'global'
    category = 'router'
    description = factory.Faker('paragraph')
    is_approved = False
    is_featured = False
    component_count = 0
    view_count = 0

    created_by = factory.SubFactory('apps.users.tests.factories.UserFactory')

    class Params:
        approved = factory.Trait(
            is_approved=True,
        )
        featured = factory.Trait(
            is_approved=True,
            is_featured=True,
        )
        with_revision = factory.Trait(
            revision='v1.0',
        )
        us_region = factory.Trait(
            region='us',
        )


class ProductImageFactory(factory.django.DjangoModelFactory):
    """Factory for creating ProductImage instances."""

    class Meta:
        model = ProductImage

    product = factory.SubFactory(ProductFactory)
    image_type = 'overview'
    caption = factory.Faker('sentence')
    display_order = factory.Sequence(lambda n: n)

    # Note: For actual image testing, you'd need to use factory.django.ImageField
    # image = factory.django.ImageField(color='blue')


class SchematicFactory(factory.django.DjangoModelFactory):
    """Factory for creating Schematic instances."""

    class Meta:
        model = Schematic

    product = factory.SubFactory(ProductFactory)
    schematic_type = 'full_schematic'
    title = factory.Sequence(lambda n: f'Schematic {n}')
    description = factory.Faker('paragraph')
    source_type = 'community'
    is_approved = False
    download_count = 0

    uploaded_by = factory.SubFactory('apps.users.tests.factories.UserFactory')

    class Params:
        approved = factory.Trait(
            is_approved=True,
        )
        official = factory.Trait(
            source_type='official',
        )


@pytest.fixture
def product_factory(db):
    """Pytest fixture for ProductFactory."""
    return ProductFactory


@pytest.fixture
def product_image_factory(db):
    """Pytest fixture for ProductImageFactory."""
    return ProductImageFactory


@pytest.fixture
def schematic_factory(db):
    """Pytest fixture for SchematicFactory."""
    return SchematicFactory
