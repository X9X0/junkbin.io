"""
Unit tests for submissions app models.
"""
import pytest
from apps.submissions.models import Submission


class TestSubmissionApproval:
    """Tests for Submission.approve() method."""

    def test_approve_sets_status(self, submission_factory, user_factory):
        """approve() sets status to APPROVED."""
        submission = submission_factory(status='pending')
        reviewer = user_factory(is_moderator=True)

        submission.approve(reviewer, notes='Looks good')

        submission.refresh_from_db()
        assert submission.status == Submission.Status.APPROVED
        assert submission.review_notes == 'Looks good'
        assert submission.reviewed_by == reviewer
        assert submission.reviewed_at is not None

    def test_approve_marks_product_approved(self, submission_factory, user_factory, product_factory):
        """approve() marks related product as approved."""
        product = product_factory(is_approved=False)
        submission = submission_factory(status='pending', product=product)
        reviewer = user_factory(is_moderator=True)

        submission.approve(reviewer)

        product.refresh_from_db()
        assert product.is_approved is True

    def test_approve_increments_user_contribution(self, submission_factory, user_factory):
        """approve() increments submitter's contribution count and reputation."""
        submitter = user_factory(contribution_count=0, reputation_score=0)
        submission = submission_factory(status='pending', submitted_by=submitter)
        reviewer = user_factory(is_moderator=True)

        submission.approve(reviewer)

        submitter.refresh_from_db()
        assert submitter.contribution_count == 1
        assert submitter.reputation_score == 10

    def test_approve_without_product(self, submission_factory, user_factory):
        """approve() works when submission has no product."""
        submission = submission_factory(status='pending', product=None)
        reviewer = user_factory(is_moderator=True)

        # Should not raise an error
        submission.approve(reviewer)

        submission.refresh_from_db()
        assert submission.status == Submission.Status.APPROVED

    def test_approve_without_submitter(self, submission_factory, user_factory):
        """approve() works when submission has no submitter."""
        submission = submission_factory(status='pending', submitted_by=None)
        reviewer = user_factory(is_moderator=True)

        # Should not raise an error
        submission.approve(reviewer)

        submission.refresh_from_db()
        assert submission.status == Submission.Status.APPROVED


class TestSubmissionRejection:
    """Tests for Submission.reject() method."""

    def test_reject_sets_status(self, submission_factory, user_factory):
        """reject() sets status to REJECTED."""
        submission = submission_factory(status='pending')
        reviewer = user_factory(is_moderator=True)

        submission.reject(reviewer, notes='Incomplete information')

        submission.refresh_from_db()
        assert submission.status == Submission.Status.REJECTED
        assert submission.review_notes == 'Incomplete information'
        assert submission.reviewed_by == reviewer
        assert submission.reviewed_at is not None

    def test_reject_no_product_change(self, submission_factory, user_factory, product_factory):
        """reject() does not change product approval status."""
        product = product_factory(is_approved=False)
        submission = submission_factory(status='pending', product=product)
        reviewer = user_factory(is_moderator=True)

        submission.reject(reviewer)

        product.refresh_from_db()
        assert product.is_approved is False  # Unchanged

    def test_reject_no_contribution_increment(self, submission_factory, user_factory):
        """reject() does not increment user contribution."""
        submitter = user_factory(contribution_count=0, reputation_score=0)
        submission = submission_factory(status='pending', submitted_by=submitter)
        reviewer = user_factory(is_moderator=True)

        submission.reject(reviewer)

        submitter.refresh_from_db()
        assert submitter.contribution_count == 0  # Unchanged
        assert submitter.reputation_score == 0  # Unchanged


class TestSubmissionRequestChanges:
    """Tests for Submission.request_changes() method."""

    def test_request_changes_sets_status(self, submission_factory, user_factory):
        """request_changes() sets status to NEEDS_CHANGES."""
        submission = submission_factory(status='in_review')
        reviewer = user_factory(is_moderator=True)

        submission.request_changes(reviewer, notes='Please add FCC ID')

        submission.refresh_from_db()
        assert submission.status == Submission.Status.NEEDS_CHANGES
        assert submission.review_notes == 'Please add FCC ID'
        assert submission.reviewed_by == reviewer


class TestSubmissionStatusTransitions:
    """Tests for submission status transitions."""

    def test_draft_to_pending(self, submission_factory):
        """Submission can transition from DRAFT to PENDING."""
        submission = submission_factory(status='draft')

        submission.status = Submission.Status.PENDING
        submission.save()

        submission.refresh_from_db()
        assert submission.status == Submission.Status.PENDING

    def test_pending_to_in_review(self, submission_factory):
        """Submission can transition from PENDING to IN_REVIEW."""
        submission = submission_factory(status='pending')

        submission.status = Submission.Status.IN_REVIEW
        submission.save()

        submission.refresh_from_db()
        assert submission.status == Submission.Status.IN_REVIEW

    def test_in_review_to_approved(self, submission_factory, user_factory):
        """Submission can transition from IN_REVIEW to APPROVED."""
        submission = submission_factory(status='in_review')
        reviewer = user_factory(is_moderator=True)

        submission.approve(reviewer)

        submission.refresh_from_db()
        assert submission.status == Submission.Status.APPROVED

    def test_in_review_to_rejected(self, submission_factory, user_factory):
        """Submission can transition from IN_REVIEW to REJECTED."""
        submission = submission_factory(status='in_review')
        reviewer = user_factory(is_moderator=True)

        submission.reject(reviewer)

        submission.refresh_from_db()
        assert submission.status == Submission.Status.REJECTED

    def test_in_review_to_needs_changes(self, submission_factory, user_factory):
        """Submission can transition from IN_REVIEW to NEEDS_CHANGES."""
        submission = submission_factory(status='in_review')
        reviewer = user_factory(is_moderator=True)

        submission.request_changes(reviewer, notes='Needs more detail')

        submission.refresh_from_db()
        assert submission.status == Submission.Status.NEEDS_CHANGES

    def test_needs_changes_to_pending(self, submission_factory):
        """Submission can transition from NEEDS_CHANGES back to PENDING."""
        submission = submission_factory(status='needs_changes')

        submission.status = Submission.Status.PENDING
        submission.save()

        submission.refresh_from_db()
        assert submission.status == Submission.Status.PENDING


class TestSubmissionStr:
    """Tests for Submission string representation."""

    def test_str_representation(self, submission_factory, user_factory):
        """Submission string shows type, submitter, and status."""
        submitter = user_factory(username='contributor1')
        submission = submission_factory(
            submission_type='new_product',
            submitted_by=submitter,
            status='pending'
        )

        result = str(submission)
        assert 'New Product' in result
        assert 'contributor1' in result
        assert 'Pending' in result


class TestSubmissionComment:
    """Tests for SubmissionComment model."""

    def test_comment_creation(self, submission_comment_factory, user_factory):
        """SubmissionComment can be created."""
        author = user_factory(username='reviewer1')
        comment = submission_comment_factory(author=author, content='Please clarify')

        assert comment.author == author
        assert comment.content == 'Please clarify'
        assert comment.submission is not None

    def test_comment_str_representation(self, submission_comment_factory, user_factory):
        """SubmissionComment string representation."""
        author = user_factory(username='commenter')
        comment = submission_comment_factory(author=author)

        result = str(comment)
        assert 'commenter' in result
