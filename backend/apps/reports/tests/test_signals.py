"""
Unit tests for reports app signals.
"""
import pytest
from django.conf import settings
from apps.reports.models import Report, UserReview


class TestStrikeThresholdSignal:
    """Tests for the check_strike_threshold signal."""

    def test_user_review_created_at_threshold(self, report_factory, user_factory, product_factory):
        """UserReview is created when user reaches 3 strikes."""
        # Create reported user
        reported_user = user_factory(report_count=0, review_count=0)
        resolver = user_factory(is_moderator=True)
        product = product_factory(created_by=reported_user)

        # Create and resolve 3 valid reports
        for i in range(3):
            report = report_factory(
                reported_user=reported_user,
                status='pending',
                object_id=product.id
            )
            report.resolve_as_valid(resolver)

        reported_user.refresh_from_db()
        assert reported_user.report_count == 3

        # Should have created a UserReview
        reviews = UserReview.objects.filter(user=reported_user)
        assert reviews.count() == 1
        assert reviews.first().review_type == UserReview.ReviewType.AUTOMATIC
        assert reviews.first().trigger_report_count == 3

    def test_user_review_created_at_6_strikes(self, report_factory, user_factory, product_factory):
        """UserReview is created when user reaches 6 strikes."""
        reported_user = user_factory(report_count=0, review_count=0)
        resolver = user_factory(is_moderator=True)
        product = product_factory(created_by=reported_user)

        # Create and resolve 6 valid reports
        for i in range(6):
            report = report_factory(
                reported_user=reported_user,
                status='pending',
                object_id=product.id
            )
            report.resolve_as_valid(resolver)

        reported_user.refresh_from_db()
        assert reported_user.report_count == 6

        # Should have created 2 UserReviews (at 3 and 6)
        reviews = UserReview.objects.filter(user=reported_user).order_by('trigger_report_count')
        assert reviews.count() == 2
        assert reviews[0].trigger_report_count == 3
        assert reviews[1].trigger_report_count == 6

    def test_no_duplicate_pending_review(self, report_factory, user_factory, product_factory, user_review_factory):
        """No duplicate UserReview created if one is already pending."""
        reported_user = user_factory(report_count=2, review_count=0)
        resolver = user_factory(is_moderator=True)
        product = product_factory(created_by=reported_user)

        # Create a pending review first
        existing_review = user_review_factory(user=reported_user, status='pending')

        # Resolve another valid report (would be strike #3)
        report = report_factory(
            reported_user=reported_user,
            status='pending',
            object_id=product.id
        )
        report.resolve_as_valid(resolver)

        # Should still only have the one review
        reviews = UserReview.objects.filter(user=reported_user)
        assert reviews.count() == 1
        assert reviews.first().id == existing_review.id

    def test_no_review_for_invalid_reports(self, report_factory, user_factory, product_factory):
        """Invalid reports do not trigger UserReview."""
        reported_user = user_factory(report_count=0, review_count=0)
        resolver = user_factory(is_moderator=True)
        product = product_factory(created_by=reported_user)

        # Create and resolve 3 invalid reports
        for i in range(3):
            report = report_factory(
                reported_user=reported_user,
                status='pending',
                object_id=product.id
            )
            report.resolve_as_invalid(resolver)

        reported_user.refresh_from_db()
        assert reported_user.report_count == 0

        # Should not have created any UserReview
        reviews = UserReview.objects.filter(user=reported_user)
        assert reviews.count() == 0

    def test_review_includes_related_reports(self, report_factory, user_factory, product_factory):
        """Created UserReview includes related reports."""
        reported_user = user_factory(report_count=0, review_count=0)
        resolver = user_factory(is_moderator=True)
        product = product_factory(created_by=reported_user)

        reports = []
        for i in range(3):
            report = report_factory(
                reported_user=reported_user,
                status='pending',
                object_id=product.id
            )
            report.resolve_as_valid(resolver)
            reports.append(report)

        review = UserReview.objects.filter(user=reported_user).first()
        assert review is not None
        assert review.related_reports.count() == 3

    def test_no_review_without_reported_user(self, report_factory, user_factory, product_factory):
        """Reports without reported_user don't trigger review."""
        resolver = user_factory(is_moderator=True)
        product = product_factory()

        # Create report without reported_user
        report = report_factory(
            reported_user=None,
            status='pending',
            object_id=product.id
        )

        # This should not raise an error
        report.counted_as_strike = True
        report.save()

        # No UserReview should be created
        assert UserReview.objects.count() == 0

    def test_review_triggered_by_is_set(self, report_factory, user_factory, product_factory):
        """Created UserReview has triggered_by report set."""
        reported_user = user_factory(report_count=2, review_count=0)
        resolver = user_factory(is_moderator=True)
        product = product_factory(created_by=reported_user)

        # The 3rd strike triggers the review
        third_report = report_factory(
            reported_user=reported_user,
            status='pending',
            object_id=product.id
        )
        third_report.resolve_as_valid(resolver)

        review = UserReview.objects.filter(user=reported_user).first()
        assert review.triggered_by == third_report
