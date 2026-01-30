"""
User views for Junkbin.io API
"""
from rest_framework import generics, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import get_user_model
from django.db.models import Count, Q
from drf_spectacular.utils import extend_schema, extend_schema_view

from .serializers import (
    UserSerializer,
    UserDetailSerializer,
    UserRegistrationSerializer,
    UserStatsSerializer,
    PasswordChangeSerializer,
    PreferencesSerializer,
)
from .permissions import IsOwnerOrReadOnly

User = get_user_model()


@extend_schema_view(
    list=extend_schema(description='List all users (public profiles)'),
    retrieve=extend_schema(description='Get user profile by ID'),
)
class UserViewSet(ModelViewSet):
    """
    ViewSet for user operations.

    list: List all users (public info only)
    retrieve: Get a specific user's public profile
    """

    queryset = User.objects.filter(is_active=True)
    permission_classes = [permissions.IsAuthenticatedOrReadOnly, IsOwnerOrReadOnly]

    def get_serializer_class(self):
        if self.action == 'retrieve' and self.request.user == self.get_object():
            return UserDetailSerializer
        return UserSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        # Order by reputation by default
        return queryset.order_by('-reputation_score')

    @action(detail=True, methods=['get'])
    def stats(self, request, pk=None):
        """Get user contribution statistics."""
        user = self.get_object()

        # Get contribution counts
        from apps.submissions.models import Submission

        submissions = Submission.objects.filter(submitted_by=user)

        stats = {
            'total_contributions': user.contribution_count,
            'approved_products': submissions.filter(
                submission_type='new_product',
                status='approved'
            ).count(),
            'approved_components': submissions.filter(
                submission_type='component_addition',
                status='approved'
            ).count(),
            'pending_submissions': submissions.filter(status='pending').count(),
            'reports_submitted': user.submitted_reports.count() if hasattr(user, 'submitted_reports') else 0,
            'reports_received': user.report_count,
            'reputation_rank': User.objects.filter(
                reputation_score__gt=user.reputation_score,
                is_active=True
            ).count() + 1,
        }

        serializer = UserStatsSerializer(stats)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def contributions(self, request, pk=None):
        """Get user's contributions (products and components they've added)."""
        user = self.get_object()

        from apps.products.models import Product
        from apps.products.serializers import ProductListSerializer

        products = Product.objects.filter(
            created_by=user
        ).order_by('-created_at')[:20]

        serializer = ProductListSerializer(products, many=True)
        return Response(serializer.data)


class UserRegistrationView(generics.CreateAPIView):
    """Register a new user account."""

    queryset = User.objects.all()
    serializer_class = UserRegistrationSerializer
    permission_classes = [permissions.AllowAny]

    @extend_schema(
        description='Register a new user account',
        responses={201: UserSerializer}
    )
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        # Generate JWT tokens
        refresh = RefreshToken.for_user(user)

        return Response({
            'user': UserSerializer(user).data,
            'tokens': {
                'refresh': str(refresh),
                'access': str(refresh.access_token),
            },
            'message': 'Registration successful. Please verify your email.'
        }, status=status.HTTP_201_CREATED)


class CurrentUserView(APIView):
    """Get or update the current authenticated user."""

    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        description='Get current user profile',
        responses={200: UserDetailSerializer}
    )
    def get(self, request):
        serializer = UserDetailSerializer(request.user)
        return Response(serializer.data)

    @extend_schema(
        description='Update current user profile',
        request=UserDetailSerializer,
        responses={200: UserDetailSerializer}
    )
    def patch(self, request):
        serializer = UserDetailSerializer(
            request.user,
            data=request.data,
            partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class PasswordChangeView(APIView):
    """Change password for authenticated user."""

    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        description='Change user password',
        request=PasswordChangeSerializer,
        responses={200: None}
    )
    def post(self, request):
        serializer = PasswordChangeSerializer(
            data=request.data,
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)

        request.user.set_password(serializer.validated_data['new_password'])
        request.user.save()

        return Response({'message': 'Password changed successfully.'})


class PreferencesView(APIView):
    """Get or update user preferences."""

    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        description='Get user preferences',
        responses={200: PreferencesSerializer}
    )
    def get(self, request):
        serializer = PreferencesSerializer(request.user.preferences)
        return Response(serializer.data)

    @extend_schema(
        description='Update user preferences',
        request=PreferencesSerializer,
        responses={200: PreferencesSerializer}
    )
    def patch(self, request):
        current_prefs = request.user.preferences or {}
        current_prefs.update(request.data)

        serializer = PreferencesSerializer(data=current_prefs)
        serializer.is_valid(raise_exception=True)

        request.user.preferences = serializer.validated_data
        request.user.save(update_fields=['preferences'])

        return Response(serializer.data)
