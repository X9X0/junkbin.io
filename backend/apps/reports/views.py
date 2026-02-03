"""
Report views for Junkbin.io API
"""
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import OrderingFilter
from drf_spectacular.utils import extend_schema, extend_schema_view

from .models import Report, UserReview
from .serializers import (
    ReportListSerializer,
    ReportDetailSerializer,
    ReportCreateSerializer,
    ReportResolveSerializer,
    UserReviewListSerializer,
    UserReviewDetailSerializer,
    UserReviewCompleteSerializer,
)
from apps.users.permissions import IsModerator
from apps.api.permissions import IsVerifiedEmail


@extend_schema_view(
    list=extend_schema(description='List reports'),
    retrieve=extend_schema(description='Get report details'),
    create=extend_schema(description='Create a new report'),
)
class ReportViewSet(viewsets.ModelViewSet):
    """
    ViewSet for report operations.
    """

    queryset = Report.objects.select_related(
        'reporter', 'reported_user', 'resolved_by', 'content_type'
    )
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['status', 'reason', 'reported_user', 'counted_as_strike']
    ordering_fields = ['created_at', 'resolved_at']
    ordering = ['-created_at']

    def get_serializer_class(self):
        if self.action == 'list':
            return ReportListSerializer
        elif self.action == 'create':
            return ReportCreateSerializer
        return ReportDetailSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user

        # Non-moderators can only see their own reports
        if not user.is_staff and not getattr(user, 'is_moderator', False):
            queryset = queryset.filter(reporter=user)

        return queryset

    def get_permissions(self):
        if self.action in ['create']:
            return [permissions.IsAuthenticated(), IsVerifiedEmail()]
        elif self.action in ['resolve', 'pending']:
            return [IsModerator()]
        elif self.action in ['destroy']:
            return [permissions.IsAdminUser()]
        return [permissions.IsAuthenticated()]

    @action(detail=True, methods=['post'])
    def resolve(self, request, pk=None):
        """Resolve a report."""
        report = self.get_object()

        serializer = ReportResolveSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        action = serializer.validated_data['action']
        notes = serializer.validated_data.get('notes', '')

        if action == 'valid':
            report.resolve_as_valid(request.user, notes)
        elif action == 'invalid':
            report.resolve_as_invalid(request.user, notes)
        elif action == 'dismiss':
            report.dismiss(request.user, notes)

        return Response(ReportDetailSerializer(report).data)

    @action(detail=False, methods=['get'])
    def pending(self, request):
        """Get pending reports for moderation."""
        reports = self.get_queryset().filter(
            status=Report.Status.PENDING
        )

        page = self.paginate_queryset(reports)
        if page is not None:
            serializer = ReportListSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = ReportListSerializer(reports, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def my_reports(self, request):
        """Get current user's submitted reports."""
        reports = Report.objects.filter(
            reporter=request.user
        ).order_by('-created_at')

        page = self.paginate_queryset(reports)
        if page is not None:
            serializer = ReportListSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = ReportListSerializer(reports, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Get report statistics."""
        from django.db.models import Count

        stats = Report.objects.aggregate(
            total=Count('id'),
            pending=Count('id', filter=models.Q(status='pending')),
            resolved_valid=Count('id', filter=models.Q(status='resolved_valid')),
            resolved_invalid=Count('id', filter=models.Q(status='resolved_invalid')),
        )

        return Response(stats)


@extend_schema_view(
    list=extend_schema(description='List user reviews'),
    retrieve=extend_schema(description='Get user review details'),
)
class UserReviewViewSet(viewsets.ModelViewSet):
    """
    ViewSet for user review operations (moderators only).
    """

    queryset = UserReview.objects.select_related(
        'user', 'reviewer', 'triggered_by'
    ).prefetch_related('related_reports')
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['status', 'review_type', 'user']
    ordering_fields = ['created_at', 'reviewed_at']
    ordering = ['-created_at']
    permission_classes = [IsModerator]

    def get_serializer_class(self):
        if self.action == 'list':
            return UserReviewListSerializer
        return UserReviewDetailSerializer

    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        """Complete a user review."""
        review = self.get_object()

        serializer = UserReviewCompleteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        review.complete_review(
            reviewer=request.user,
            status=serializer.validated_data['status'],
            notes=serializer.validated_data.get('notes', ''),
            action_taken=serializer.validated_data.get('action_taken', '')
        )

        return Response(UserReviewDetailSerializer(review).data)

    @action(detail=False, methods=['get'])
    def pending(self, request):
        """Get pending user reviews."""
        reviews = self.get_queryset().filter(
            status=UserReview.Status.PENDING
        )

        page = self.paginate_queryset(reviews)
        if page is not None:
            serializer = UserReviewListSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = UserReviewListSerializer(reviews, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def start_review(self, request, pk=None):
        """Mark a review as in progress."""
        review = self.get_object()

        if review.status != UserReview.Status.PENDING:
            return Response(
                {'detail': 'Review is not in pending status.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        review.status = UserReview.Status.IN_PROGRESS
        review.save(update_fields=['status'])

        return Response(UserReviewDetailSerializer(review).data)


# Import for stats
from django.db import models
