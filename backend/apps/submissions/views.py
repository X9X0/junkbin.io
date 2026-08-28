"""
Submission views for Junkbin.io API
"""
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import OrderingFilter
from drf_spectacular.utils import extend_schema, extend_schema_view

from .models import Submission, SubmissionComment
from .serializers import (
    SubmissionListSerializer,
    SubmissionDetailSerializer,
    SubmissionCreateSerializer,
    SubmissionReviewSerializer,
    SubmissionCommentSerializer,
    SubmissionCommentCreateSerializer,
)
from apps.users.permissions import IsModerator
from apps.api.permissions import IsVerifiedEmail
from apps.api.throttling import SubmissionRateThrottle


@extend_schema_view(
    list=extend_schema(description='List submissions'),
    retrieve=extend_schema(description='Get submission details'),
    create=extend_schema(description='Create a new submission'),
)
class SubmissionViewSet(viewsets.ModelViewSet):
    """
    ViewSet for submission operations.
    """

    queryset = Submission.objects.select_related(
        'submitted_by', 'reviewed_by', 'product'
    ).prefetch_related('comments')
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['status', 'submission_type', 'submission_level', 'submitted_by']
    ordering_fields = ['submitted_at', 'reviewed_at']
    ordering = ['-submitted_at']

    def get_serializer_class(self):
        if self.action == 'list':
            return SubmissionListSerializer
        elif self.action == 'create':
            return SubmissionCreateSerializer
        return SubmissionDetailSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user

        # Non-staff/moderators can only see their own submissions
        if not user.is_staff and not getattr(user, 'is_moderator', False):
            queryset = queryset.filter(submitted_by=user)

        return queryset

    def get_permissions(self):
        if self.action in ['create', 'comments']:
            return [permissions.IsAuthenticated(), IsVerifiedEmail()]
        elif self.action in ['review', 'pending']:
            return [IsModerator()]
        return [permissions.IsAuthenticated()]

    def get_throttles(self):
        if self.action == 'create':
            return [SubmissionRateThrottle()]
        return super().get_throttles()

    def perform_create(self, serializer):
        submission = serializer.save()

        if submission.status == Submission.Status.PENDING:
            from django.contrib.auth import get_user_model
            from django.db.models import Q
            from apps.notifications.services import notify_staff
            from apps.notifications.models import Notification
            User = get_user_model()
            moderators = User.objects.filter(Q(is_staff=True) | Q(is_moderator=True))
            notify_staff(
                moderators, Notification.Category.SUBMISSION_PENDING,
                title='New submission pending review',
                body=submission.changes_summary,
                url='/moderation',
                actor=submission.submitted_by,
            )

    @action(detail=True, methods=['post'])
    def review(self, request, pk=None):
        """Review a submission (approve/reject/request changes)."""
        submission = self.get_object()

        serializer = SubmissionReviewSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        action = serializer.validated_data['action']
        notes = serializer.validated_data.get('notes', '')

        if action == 'approve':
            submission.approve(request.user, notes)
        elif action == 'reject':
            submission.reject(request.user, notes)
        elif action == 'request_changes':
            submission.request_changes(request.user, notes)

        return Response(SubmissionDetailSerializer(submission).data)

    @action(detail=False, methods=['get'])
    def pending(self, request):
        """Get pending submissions for moderation queue."""
        submissions = self.get_queryset().filter(
            status=Submission.Status.PENDING
        )

        page = self.paginate_queryset(submissions)
        if page is not None:
            serializer = SubmissionListSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = SubmissionListSerializer(submissions, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def my_submissions(self, request):
        """Get current user's submissions."""
        submissions = Submission.objects.filter(
            submitted_by=request.user
        ).order_by('-submitted_at')

        page = self.paginate_queryset(submissions)
        if page is not None:
            serializer = SubmissionListSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = SubmissionListSerializer(submissions, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get', 'post'])
    def comments(self, request, pk=None):
        """Get or add comments on a submission."""
        submission = self.get_object()

        if request.method == 'GET':
            comments = submission.comments.all()
            serializer = SubmissionCommentSerializer(comments, many=True)
            return Response(serializer.data)

        # POST - add comment
        serializer = SubmissionCommentCreateSerializer(
            data=request.data,
            context={'request': request, 'submission': submission}
        )
        serializer.is_valid(raise_exception=True)
        comment = serializer.save()

        # Notify whichever of submitter/reviewer didn't post this comment
        author = request.user
        other = submission.reviewed_by if author == submission.submitted_by else submission.submitted_by
        if other and other != author:
            from apps.notifications.services import notify
            from apps.notifications.models import Notification
            notify(
                other, Notification.Category.SUBMISSION_COMMENT,
                title=f'New comment on your submission from {author.username}',
                body=comment.content[:200],
                url='/my-submissions',
                actor=author,
            )

        return Response(
            SubmissionCommentSerializer(comment).data,
            status=status.HTTP_201_CREATED
        )

    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Get submission statistics for dashboard."""
        from django.db.models import Count

        stats = Submission.objects.aggregate(
            total=Count('id'),
            pending=Count('id', filter=models.Q(status='pending')),
            approved=Count('id', filter=models.Q(status='approved')),
            rejected=Count('id', filter=models.Q(status='rejected')),
        )

        # Add user-specific stats if authenticated
        if request.user.is_authenticated:
            user_stats = Submission.objects.filter(
                submitted_by=request.user
            ).aggregate(
                user_total=Count('id'),
                user_pending=Count('id', filter=models.Q(status='pending')),
                user_approved=Count('id', filter=models.Q(status='approved')),
            )
            stats.update(user_stats)

        return Response(stats)


# Import for stats action
from django.db import models
