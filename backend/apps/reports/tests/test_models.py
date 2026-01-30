"""
Unit tests for reports app models.
"""
import pytest
from django.utils import timezone
from apps.reports.models import Report, UserReview


class TestReportResolution:
    """Tests for Report resolution methods."""

    def test_resolve_as_valid_sets_status(self, report_factory, user_factory):
        """resolve_as_valid sets status to RESOLVED_VALID."""
        report = report_factory(status='pending')
        resolver = user_factory()

        report.resolve_as_valid(resolver, notes='Valid report')

        report.refresh_from_db()
        assert report.status == Report.Status.RESOLVED_VALID
        assert report.resolution_notes == 'Valid report'
        assert report.resolved_by == resolver
        assert report.resolved_at is not None

    def test_resolve_as_valid_marks_strike(self, report_factory, user_factory):
        """resolve_as_valid marks counted_as_strike as True."""
        report = report_factory(status='pending', counted_as_strike=False)
        resolver = user_factory()

        report.resolve_as_valid(resolver)

        report.refresh_from_db()
        assert report.counted_as_strike is True

    def test_resolve_as_valid_increments_user_report_count(self, report_factory, user_factory):
        """resolve_as_valid increments reported user's report_count."""
        reported_user = user_factory(report_count=0, reputation_score=50)
        report = report_factory(status='pending', reported_user=reported_user)
        resolver = user_factory()

        report.resolve_as_valid(resolver)

        reported_user.refresh_from_db()
        assert reported_user.report_count == 1
        assert reported_user.reputation_score == 45  # -5 points

    def test_resolve_as_invalid_sets_status(self, report_factory, user_factory):
        """resolve_as_invalid sets status to RESOLVED_INVALID."""
        report = report_factory(status='pending')
        resolver = user_factory()

        report.resolve_as_invalid(resolver, notes='False report')

        report.refresh_from_db()
        assert report.status == Report.Status.RESOLVED_INVALID
        assert report.resolution_notes == 'False report'
        assert report.resolved_by == resolver
        assert report.resolved_at is not None

    def test_resolve_as_invalid_no_strike(self, report_factory, user_factory):
        """resolve_as_invalid does not count as strike."""
        report = report_factory(status='pending', counted_as_strike=False)
        resolver = user_factory()

        report.resolve_as_invalid(resolver)

        report.refresh_from_db()
        assert report.counted_as_strike is False

    def test_resolve_as_invalid_no_user_impact(self, report_factory, user_factory):
        """resolve_as_invalid does not affect reported user."""
        reported_user = user_factory(report_count=0, reputation_score=50)
        report = report_factory(status='pending', reported_user=reported_user)
        resolver = user_factory()

        report.resolve_as_invalid(resolver)

        reported_user.refresh_from_db()
        assert reported_user.report_count == 0
        assert reported_user.reputation_score == 50

    def test_dismiss_sets_status(self, report_factory, user_factory):
        """dismiss sets status to DISMISSED."""
        report = report_factory(status='pending')
        resolver = user_factory()

        report.dismiss(resolver, notes='Not actionable')

        report.refresh_from_db()
        assert report.status == Report.Status.DISMISSED
        assert report.resolution_notes == 'Not actionable'
        assert report.resolved_by == resolver


class TestUserReviewCompletion:
    """Tests for UserReview completion and account actions."""

    def test_complete_review_cleared(self, user_review_factory, user_factory):
        """Completing review as cleared makes no account changes."""
        user = user_factory(is_active=True, is_trusted=True)
        review = user_review_factory(user=user, status='pending')
        reviewer = user_factory(is_moderator=True)

        review.complete_review(
            reviewer=reviewer,
            status=UserReview.Status.CLEARED,
            notes='No violations found'
        )

        review.refresh_from_db()
        user.refresh_from_db()

        assert review.status == UserReview.Status.CLEARED
        assert review.reviewer == reviewer
        assert review.reviewed_at is not None
        assert user.is_active is True
        assert user.is_trusted is True

    def test_complete_review_suspended(self, user_review_factory, user_factory):
        """Completing review as suspended deactivates user account."""
        user = user_factory(is_active=True, is_trusted=True)
        review = user_review_factory(user=user, status='pending')
        reviewer = user_factory(is_moderator=True)

        review.complete_review(
            reviewer=reviewer,
            status=UserReview.Status.SUSPENDED,
            notes='Repeated violations',
            action_taken='Account suspended'
        )

        review.refresh_from_db()
        user.refresh_from_db()

        assert review.status == UserReview.Status.SUSPENDED
        assert review.action_taken == 'Account suspended'
        assert user.is_active is False

    def test_complete_review_restricted(self, user_review_factory, user_factory):
        """Completing review as restricted removes trusted status."""
        user = user_factory(is_active=True, is_trusted=True)
        review = user_review_factory(user=user, status='pending')
        reviewer = user_factory(is_moderator=True)

        review.complete_review(
            reviewer=reviewer,
            status=UserReview.Status.RESTRICTED,
            notes='Needs monitoring'
        )

        review.refresh_from_db()
        user.refresh_from_db()

        assert review.status == UserReview.Status.RESTRICTED
        assert user.is_active is True  # Still active
        assert user.is_trusted is False  # Trusted status removed

    def test_complete_review_warning_issued(self, user_review_factory, user_factory):
        """Completing review with warning makes no account changes."""
        user = user_factory(is_active=True, is_trusted=True)
        review = user_review_factory(user=user, status='pending')
        reviewer = user_factory(is_moderator=True)

        review.complete_review(
            reviewer=reviewer,
            status=UserReview.Status.WARNING_ISSUED,
            notes='First warning'
        )

        review.refresh_from_db()
        user.refresh_from_db()

        assert review.status == UserReview.Status.WARNING_ISSUED
        assert user.is_active is True
        assert user.is_trusted is True


class TestReportStr:
    """Tests for Report string representation."""

    def test_str_representation(self, report_factory, user_factory):
        """Report string shows reporter and reason."""
        reporter = user_factory(username='reporter1')
        report = report_factory(reporter=reporter, reason='spam')

        assert 'reporter1' in str(report)
        assert 'Spam' in str(report)


class TestUserReviewStr:
    """Tests for UserReview string representation."""

    def test_str_representation(self, user_review_factory, user_factory):
        """UserReview string shows user and status."""
        user = user_factory(username='baduser')
        review = user_review_factory(user=user, status='pending')

        assert 'baduser' in str(review)
        assert 'Pending' in str(review)
