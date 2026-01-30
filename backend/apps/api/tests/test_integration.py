"""
Integration tests for Junkbin.io API workflows.
"""
import pytest
from django.conf import settings
from apps.submissions.models import Submission
from apps.reports.models import Report, UserReview


@pytest.mark.integration
class TestSubmissionWorkflowWithTrustedUser:
    """Integration tests for submission workflow with trusted user auto-approval."""

    def test_trusted_user_submission_auto_approval(
        self, user_factory, product_factory, submission_factory
    ):
        """Trusted user submissions can be auto-approved."""
        trusted_user = user_factory(is_trusted=True)
        product = product_factory(created_by=trusted_user, is_approved=False)

        submission = submission_factory(
            submitted_by=trusted_user,
            product=product,
            status='pending',
            auto_approved=True
        )

        # In a real scenario, the view would check can_submit_without_review
        # and auto-approve. Here we verify the property works.
        assert trusted_user.can_submit_without_review is True

        # Simulate auto-approval by calling approve without reviewer
        submission.approve(reviewer=trusted_user, notes='Auto-approved for trusted user')

        submission.refresh_from_db()
        product.refresh_from_db()

        assert submission.status == Submission.Status.APPROVED
        assert submission.auto_approved is True
        assert product.is_approved is True

    def test_regular_user_requires_moderation(self, user_factory, product_factory, submission_factory):
        """Regular user submissions require moderation review."""
        regular_user = user_factory(is_trusted=False, is_staff=False, is_moderator=False)
        product = product_factory(created_by=regular_user, is_approved=False)

        submission = submission_factory(
            submitted_by=regular_user,
            product=product,
            status='pending'
        )

        assert regular_user.can_submit_without_review is False
        assert submission.status == Submission.Status.PENDING
        assert product.is_approved is False


@pytest.mark.integration
class TestReputationFlow:
    """Integration tests for reputation gain through contributions."""

    def test_submit_approve_reputation_gain(
        self, user_factory, product_factory, submission_factory
    ):
        """Full flow: submit -> approve -> gain reputation."""
        submitter = user_factory(
            contribution_count=0,
            reputation_score=0,
            is_trusted=False
        )
        moderator = user_factory(is_moderator=True)
        product = product_factory(created_by=submitter, is_approved=False)

        submission = submission_factory(
            submitted_by=submitter,
            product=product,
            status='pending'
        )

        # Initial state
        assert submitter.contribution_count == 0
        assert submitter.reputation_score == 0
        assert submitter.is_trusted is False

        # Moderator approves
        submission.approve(moderator, notes='Great contribution!')

        # Verify reputation gain
        submitter.refresh_from_db()
        assert submitter.contribution_count == 1
        assert submitter.reputation_score == 10

    def test_multiple_approvals_lead_to_trusted_status(
        self, user_factory, product_factory, submission_factory
    ):
        """Multiple approved submissions can lead to trusted status."""
        submitter = user_factory(
            contribution_count=49,
            reputation_score=90,
            is_trusted=False
        )
        moderator = user_factory(is_moderator=True)

        # One more approval should push them over the threshold
        product = product_factory(created_by=submitter, is_approved=False)
        submission = submission_factory(
            submitted_by=submitter,
            product=product,
            status='pending'
        )

        assert submitter.is_trusted is False

        submission.approve(moderator)

        submitter.refresh_from_db()
        # contribution_count = 50, reputation_score = 100
        assert submitter.contribution_count == 50
        assert submitter.reputation_score == 100
        assert submitter.is_trusted is True


@pytest.mark.integration
class TestThreeStrikeSystem:
    """Integration tests for the 3-strike moderation system."""

    def test_three_strikes_triggers_review(
        self, user_factory, product_factory, report_factory
    ):
        """Three valid reports trigger automatic user review."""
        offending_user = user_factory(report_count=0, review_count=0)
        reporter = user_factory()
        moderator = user_factory(is_moderator=True)
        product = product_factory(created_by=offending_user)

        # Resolve 3 valid reports
        for i in range(3):
            report = report_factory(
                reporter=reporter,
                reported_user=offending_user,
                object_id=product.id,
                status='pending'
            )
            report.resolve_as_valid(moderator, notes=f'Valid report #{i+1}')

        offending_user.refresh_from_db()

        # Verify strikes accumulated
        assert offending_user.report_count == 3
        assert offending_user.reputation_score <= 0  # Lost at least 15 points

        # Verify UserReview was created
        reviews = UserReview.objects.filter(user=offending_user)
        assert reviews.count() == 1
        assert reviews.first().review_type == UserReview.ReviewType.AUTOMATIC

    def test_six_strikes_triggers_second_review(
        self, user_factory, product_factory, report_factory
    ):
        """Six valid reports trigger a second automatic user review."""
        offending_user = user_factory(report_count=0, review_count=0, reputation_score=100)
        reporter = user_factory()
        moderator = user_factory(is_moderator=True)
        product = product_factory(created_by=offending_user)

        # Resolve 6 valid reports
        for i in range(6):
            report = report_factory(
                reporter=reporter,
                reported_user=offending_user,
                object_id=product.id,
                status='pending'
            )
            report.resolve_as_valid(moderator)

        offending_user.refresh_from_db()

        # Verify strikes accumulated
        assert offending_user.report_count == 6

        # Verify two UserReviews were created (at 3 and 6 strikes)
        reviews = UserReview.objects.filter(user=offending_user)
        assert reviews.count() == 2

    def test_review_suspension_deactivates_account(
        self, user_factory, user_review_factory
    ):
        """User review resulting in suspension deactivates the account."""
        offending_user = user_factory(is_active=True, is_trusted=True)
        moderator = user_factory(is_moderator=True)

        review = user_review_factory(user=offending_user, status='pending')

        # Complete review with suspension
        review.complete_review(
            reviewer=moderator,
            status=UserReview.Status.SUSPENDED,
            notes='Repeated violations',
            action_taken='Account suspended'
        )

        offending_user.refresh_from_db()
        assert offending_user.is_active is False

    def test_review_restriction_removes_trusted_status(
        self, user_factory, user_review_factory
    ):
        """User review resulting in restriction removes trusted status."""
        trusted_user = user_factory(is_active=True, is_trusted=True)
        moderator = user_factory(is_moderator=True)

        review = user_review_factory(user=trusted_user, status='pending')

        # Complete review with restriction
        review.complete_review(
            reviewer=moderator,
            status=UserReview.Status.RESTRICTED,
            notes='Quality concerns'
        )

        trusted_user.refresh_from_db()
        assert trusted_user.is_active is True  # Still active
        assert trusted_user.is_trusted is False  # Lost trusted status


@pytest.mark.integration
class TestProductComponentFlow:
    """Integration tests for product-component relationships."""

    def test_add_component_updates_counts(
        self, user_factory, product_factory, component_factory, product_component_factory
    ):
        """Adding components updates both product and component counts."""
        user = user_factory()
        product = product_factory(created_by=user, component_count=0)
        component1 = component_factory(usage_count=0)
        component2 = component_factory(usage_count=0)

        # Add components to product
        pc1 = product_component_factory(
            product=product,
            component=component1,
            created_by=user
        )
        pc2 = product_component_factory(
            product=product,
            component=component2,
            created_by=user
        )

        product.refresh_from_db()
        component1.refresh_from_db()
        component2.refresh_from_db()

        assert product.component_count == 2
        assert component1.usage_count == 1
        assert component2.usage_count == 1

    def test_remove_component_updates_counts(
        self, user_factory, product_factory, component_factory, product_component_factory
    ):
        """Removing components updates both product and component counts."""
        user = user_factory()
        product = product_factory(created_by=user, component_count=0)
        component = component_factory(usage_count=0)

        pc = product_component_factory(
            product=product,
            component=component,
            created_by=user
        )

        product.refresh_from_db()
        component.refresh_from_db()
        assert product.component_count == 1
        assert component.usage_count == 1

        # Remove the component
        pc.delete()

        product.refresh_from_db()
        component.refresh_from_db()
        assert product.component_count == 0
        assert component.usage_count == 0

    def test_shared_component_multiple_products(
        self, user_factory, product_factory, component_factory, product_component_factory
    ):
        """Same component can be linked to multiple products."""
        user = user_factory()
        product1 = product_factory(created_by=user, component_count=0)
        product2 = product_factory(created_by=user, component_count=0)
        shared_component = component_factory(usage_count=0)

        # Add same component to both products
        product_component_factory(product=product1, component=shared_component)
        product_component_factory(product=product2, component=shared_component)

        shared_component.refresh_from_db()
        product1.refresh_from_db()
        product2.refresh_from_db()

        assert shared_component.usage_count == 2
        assert product1.component_count == 1
        assert product2.component_count == 1
