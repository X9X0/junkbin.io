"""
Factory definitions for submissions app models.
"""
import factory
import pytest

from apps.submissions.models import Submission, SubmissionComment


class SubmissionFactory(factory.django.DjangoModelFactory):
    """Factory for creating Submission instances."""

    class Meta:
        model = Submission
        skip_postgeneration_save = True

    submission_type = 'new_product'
    submission_level = 'basic'
    status = 'pending'
    changes_summary = factory.Faker('paragraph')
    auto_approved = False

    product = factory.SubFactory('apps.products.tests.factories.ProductFactory')
    submitted_by = factory.SubFactory('apps.users.tests.factories.UserFactory')

    class Params:
        draft = factory.Trait(
            status='draft',
        )
        pending = factory.Trait(
            status='pending',
        )
        in_review = factory.Trait(
            status='in_review',
        )
        approved = factory.Trait(
            status='approved',
        )
        rejected = factory.Trait(
            status='rejected',
        )
        needs_changes = factory.Trait(
            status='needs_changes',
        )
        component_addition = factory.Trait(
            submission_type='component_addition',
        )
        update_existing = factory.Trait(
            submission_type='update_existing',
        )


class SubmissionCommentFactory(factory.django.DjangoModelFactory):
    """Factory for creating SubmissionComment instances."""

    class Meta:
        model = SubmissionComment

    submission = factory.SubFactory(SubmissionFactory)
    author = factory.SubFactory('apps.users.tests.factories.UserFactory')
    content = factory.Faker('paragraph')


@pytest.fixture
def submission_factory(db):
    """Pytest fixture for SubmissionFactory."""
    return SubmissionFactory


@pytest.fixture
def submission_comment_factory(db):
    """Pytest fixture for SubmissionCommentFactory."""
    return SubmissionCommentFactory
