"""
Unit tests for users app models.
"""
import pytest
from django.conf import settings
from unittest.mock import patch


class TestUserReputationSystem:
    """Tests for user reputation methods."""

    def test_increment_contribution_adds_points(self, user_factory):
        """increment_contribution adds 10 reputation points."""
        user = user_factory(reputation_score=0, contribution_count=0)
        initial_reputation = user.reputation_score
        initial_contributions = user.contribution_count

        user.increment_contribution()

        user.refresh_from_db()
        assert user.reputation_score == initial_reputation + 10
        assert user.contribution_count == initial_contributions + 1

    def test_increment_contribution_updates_timestamp(self, user_factory):
        """increment_contribution updates last_contribution_at."""
        user = user_factory()
        assert user.last_contribution_at is None

        user.increment_contribution()

        user.refresh_from_db()
        assert user.last_contribution_at is not None

    def test_increment_report_count_deducts_points(self, user_factory):
        """increment_report_count deducts 5 reputation points."""
        user = user_factory(reputation_score=50, report_count=0)

        user.increment_report_count()

        user.refresh_from_db()
        assert user.reputation_score == 45
        assert user.report_count == 1

    def test_reputation_floor_at_zero(self, user_factory):
        """Reputation score cannot go below zero."""
        user = user_factory(reputation_score=3, report_count=0)

        user.increment_report_count()

        user.refresh_from_db()
        assert user.reputation_score == 0  # Floor at 0, not -2

    def test_multiple_contributions_accumulate(self, user_factory):
        """Multiple contributions accumulate properly."""
        user = user_factory(reputation_score=0, contribution_count=0)

        for _ in range(5):
            user.increment_contribution()

        user.refresh_from_db()
        assert user.reputation_score == 50
        assert user.contribution_count == 5


class TestTrustedUserPromotion:
    """Tests for automatic trusted user promotion."""

    def test_auto_promotion_at_threshold(self, user_factory):
        """User is promoted to trusted at 50 contributions and 100 reputation."""
        user = user_factory(
            contribution_count=49,
            reputation_score=90,
            is_trusted=False
        )

        user.increment_contribution()

        user.refresh_from_db()
        # contribution_count=50, reputation_score=100 after increment
        assert user.is_trusted is True

    def test_no_promotion_below_contribution_threshold(self, user_factory):
        """User is not promoted if below contribution threshold (25)."""
        user = user_factory(
            contribution_count=23,  # after increment: 24, still < 25
            reputation_score=100,
            is_trusted=False
        )

        user.increment_contribution()

        user.refresh_from_db()
        assert user.is_trusted is False

    def test_no_promotion_below_reputation_threshold(self, user_factory):
        """User is not promoted if below reputation threshold (50)."""
        user = user_factory(
            contribution_count=24,  # after increment: 25, meets contribution threshold
            reputation_score=30,    # after increment: +10 = 40, still < 50
            is_trusted=False
        )

        user.increment_contribution()

        user.refresh_from_db()
        # contribution_count=25 but reputation_score=40 (still below 50)
        assert user.is_trusted is False

    def test_already_trusted_stays_trusted(self, user_factory):
        """Already trusted user remains trusted after contribution."""
        user = user_factory(is_trusted=True)

        user.increment_contribution()

        user.refresh_from_db()
        assert user.is_trusted is True


class TestCanSubmitWithoutReview:
    """Tests for can_submit_without_review property."""

    def test_trusted_user_bypasses_review(self, user_factory):
        """Trusted users can submit without review."""
        user = user_factory(is_trusted=True, is_staff=False, is_moderator=False)
        assert user.can_submit_without_review is True

    def test_staff_bypasses_review(self, user_factory):
        """Staff users can submit without review."""
        user = user_factory(is_trusted=False, is_staff=True, is_moderator=False)
        assert user.can_submit_without_review is True

    def test_moderator_bypasses_review(self, user_factory):
        """Moderator users can submit without review."""
        user = user_factory(is_trusted=False, is_staff=False, is_moderator=True)
        assert user.can_submit_without_review is True

    def test_regular_user_requires_review(self, user_factory):
        """Regular users require review."""
        user = user_factory(is_trusted=False, is_staff=False, is_moderator=False)
        assert user.can_submit_without_review is False

    def test_combined_roles_bypass_review(self, user_factory):
        """Users with multiple roles can submit without review."""
        user = user_factory(is_trusted=True, is_staff=True, is_moderator=True)
        assert user.can_submit_without_review is True


class TestUserDisplayName:
    """Tests for user display_name property."""

    def test_display_name_with_full_name(self, user_factory):
        """display_name returns full name when available."""
        user = user_factory(first_name='John', last_name='Doe')
        assert user.display_name == 'John Doe'

    def test_display_name_falls_back_to_username(self, user_factory):
        """display_name returns username when no full name."""
        user = user_factory(first_name='', last_name='', username='testuser')
        assert user.display_name == 'testuser'


class TestUserStr:
    """Tests for user string representation."""

    def test_str_returns_username(self, user_factory):
        """String representation returns username."""
        user = user_factory(username='myuser')
        assert str(user) == 'myuser'
