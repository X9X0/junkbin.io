"""
Factory definitions for users app models.
"""
import factory
import pytest
from django.contrib.auth import get_user_model

User = get_user_model()


class UserFactory(factory.django.DjangoModelFactory):
    """Factory for creating User instances."""

    class Meta:
        model = User
        skip_postgeneration_save = True

    username = factory.Sequence(lambda n: f'user{n}')
    email = factory.LazyAttribute(lambda obj: f'{obj.username}@example.com')
    password = factory.PostGenerationMethodCall('set_password', 'testpass123')
    is_active = True
    email_verified = True

    # Default values
    reputation_score = 0
    contribution_count = 0
    report_count = 0
    review_count = 0
    is_trusted = False
    is_moderator = False

    class Params:
        # Traits for different user types
        trusted = factory.Trait(
            is_trusted=True,
            contribution_count=50,
            reputation_score=100,
        )
        moderator = factory.Trait(
            is_moderator=True,
        )
        staff = factory.Trait(
            is_staff=True,
        )
        high_reputation = factory.Trait(
            reputation_score=500,
            contribution_count=100,
        )
        with_strikes = factory.Trait(
            report_count=3,
            review_count=1,
        )


@pytest.fixture
def user_factory(db):
    """Pytest fixture for UserFactory."""
    return UserFactory
