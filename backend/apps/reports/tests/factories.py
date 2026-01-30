"""
Factory definitions for reports app models.
"""
import factory
import pytest
from django.contrib.contenttypes.models import ContentType

from apps.reports.models import Report, UserReview


class ReportFactory(factory.django.DjangoModelFactory):
    """Factory for creating Report instances."""

    class Meta:
        model = Report
        skip_postgeneration_save = True

    reason = 'incorrect_info'
    description = factory.Faker('paragraph')
    status = 'pending'
    counted_as_strike = False

    reporter = factory.SubFactory('apps.users.tests.factories.UserFactory')
    reported_user = factory.SubFactory('apps.users.tests.factories.UserFactory')

    # For generic foreign key - default to Product
    content_type = factory.LazyAttribute(
        lambda o: ContentType.objects.get(app_label='products', model='product')
    )
    object_id = factory.LazyAttribute(
        lambda o: factory.SubFactory('apps.products.tests.factories.ProductFactory').get_factory().create().id
    )

    class Params:
        spam = factory.Trait(
            reason='spam',
        )
        duplicate = factory.Trait(
            reason='duplicate',
        )
        inappropriate = factory.Trait(
            reason='inappropriate',
        )
        pending = factory.Trait(
            status='pending',
        )
        investigating = factory.Trait(
            status='investigating',
        )
        resolved_valid = factory.Trait(
            status='resolved_valid',
            counted_as_strike=True,
        )
        resolved_invalid = factory.Trait(
            status='resolved_invalid',
            counted_as_strike=False,
        )


class UserReviewFactory(factory.django.DjangoModelFactory):
    """Factory for creating UserReview instances."""

    class Meta:
        model = UserReview
        skip_postgeneration_save = True

    review_type = 'automatic'
    status = 'pending'
    trigger_report_count = 3
    notes = ''
    action_taken = ''

    user = factory.SubFactory('apps.users.tests.factories.UserFactory')

    class Params:
        manual = factory.Trait(
            review_type='manual',
        )
        in_progress = factory.Trait(
            status='in_progress',
        )
        cleared = factory.Trait(
            status='cleared',
        )
        warning_issued = factory.Trait(
            status='warning_issued',
        )
        restricted = factory.Trait(
            status='restricted',
        )
        suspended = factory.Trait(
            status='suspended',
        )


@pytest.fixture
def report_factory(db):
    """Pytest fixture for ReportFactory."""
    return ReportFactory


@pytest.fixture
def user_review_factory(db):
    """Pytest fixture for UserReviewFactory."""
    return UserReviewFactory
