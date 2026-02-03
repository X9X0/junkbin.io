"""
User views for Junkbin.io API
"""
from rest_framework import generics, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet
from rest_framework.throttling import ScopedRateThrottle
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.db.models import Count, Q
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from drf_spectacular.utils import extend_schema, extend_schema_view

from .serializers import (
    UserSerializer,
    UserDetailSerializer,
    UserRegistrationSerializer,
    UserStatsSerializer,
    PasswordChangeSerializer,
    PreferencesSerializer,
    PasswordResetRequestSerializer,
    PasswordResetConfirmSerializer,
)
from .permissions import IsOwnerOrReadOnly
from utils.email import send_password_reset_email, send_verification_email

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
    # No authentication required for registration, so no CSRF needed
    authentication_classes = []

    @extend_schema(
        description='Register a new user account',
        responses={201: UserSerializer}
    )
    def create(self, request, *args, **kwargs):
        from django.conf import settings

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        # Send verification email
        try:
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            token = default_token_generator.make_token(user)
            send_verification_email(user, token, uid)
        except Exception:
            pass  # Don't fail registration if email fails

        # Generate JWT tokens
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)
        refresh_token = str(refresh)

        response = Response({
            'user': UserSerializer(user).data,
            'tokens': {
                'refresh': refresh_token,
                'access': access_token,
            },
            'message': 'Registration successful. Please verify your email.'
        }, status=status.HTTP_201_CREATED)

        # Set HttpOnly cookies for tokens
        jwt_settings = settings.SIMPLE_JWT
        response.set_cookie(
            key=jwt_settings.get('AUTH_COOKIE', 'access_token'),
            value=access_token,
            httponly=jwt_settings.get('AUTH_COOKIE_HTTP_ONLY', True),
            secure=jwt_settings.get('AUTH_COOKIE_SECURE', True),
            samesite=jwt_settings.get('AUTH_COOKIE_SAMESITE', 'Lax'),
            path=jwt_settings.get('AUTH_COOKIE_PATH', '/'),
            max_age=int(jwt_settings['ACCESS_TOKEN_LIFETIME'].total_seconds()),
        )
        response.set_cookie(
            key=jwt_settings.get('AUTH_COOKIE_REFRESH', 'refresh_token'),
            value=refresh_token,
            httponly=jwt_settings.get('AUTH_COOKIE_HTTP_ONLY', True),
            secure=jwt_settings.get('AUTH_COOKIE_SECURE', True),
            samesite=jwt_settings.get('AUTH_COOKIE_SAMESITE', 'Lax'),
            path=jwt_settings.get('AUTH_COOKIE_PATH', '/'),
            max_age=int(jwt_settings['REFRESH_TOKEN_LIFETIME'].total_seconds()),
        )

        return response


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


class EmailVerificationView(APIView):
    """Verify user email address."""

    permission_classes = [permissions.AllowAny]
    authentication_classes = []

    @extend_schema(
        description='Verify email address with token',
        responses={200: None}
    )
    def post(self, request):
        uid = request.data.get('uid')
        token = request.data.get('token')

        if not uid or not token:
            return Response(
                {'error': 'Missing uid or token'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            user_id = force_str(urlsafe_base64_decode(uid))
            user = User.objects.get(pk=user_id)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            return Response(
                {'error': 'Invalid verification link'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not default_token_generator.check_token(user, token):
            return Response(
                {'error': 'Invalid or expired verification link'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if user.email_verified:
            return Response({'message': 'Email already verified'})

        from django.utils import timezone
        user.email_verified = True
        user.email_verified_at = timezone.now()
        user.save(update_fields=['email_verified', 'email_verified_at'])

        return Response({'message': 'Email verified successfully'})


class PasswordResetRequestView(APIView):
    """Request a password reset email."""

    permission_classes = [permissions.AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'auth'

    @extend_schema(
        description='Request a password reset email',
        request=PasswordResetRequestSerializer,
        responses={200: None}
    )
    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data['email']

        try:
            user = User.objects.get(email=email, is_active=True)
            # Generate token and uid
            token = default_token_generator.make_token(user)
            uid = urlsafe_base64_encode(force_bytes(user.pk))

            # Send reset email
            send_password_reset_email(user, token, uid)
        except User.DoesNotExist:
            # Don't reveal whether email exists - always return success
            pass

        return Response({
            'message': 'If an account with this email exists, a password reset link has been sent.'
        })


class PasswordResetConfirmView(APIView):
    """Confirm password reset with token."""

    permission_classes = [permissions.AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'auth'

    @extend_schema(
        description='Confirm password reset with token',
        request=PasswordResetConfirmSerializer,
        responses={200: None}
    )
    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        uid = serializer.validated_data['uid']
        token = serializer.validated_data['token']
        new_password = serializer.validated_data['new_password']

        try:
            # Decode uid to get user
            user_id = force_str(urlsafe_base64_decode(uid))
            user = User.objects.get(pk=user_id)

            # Verify token
            if not default_token_generator.check_token(user, token):
                return Response(
                    {'error': 'Invalid or expired reset link.'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Set new password
            user.set_password(new_password)
            user.save()

            return Response({'message': 'Password has been reset successfully.'})

        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            return Response(
                {'error': 'Invalid reset link.'},
                status=status.HTTP_400_BAD_REQUEST
            )
