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

from django.conf import settings
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt

from .serializers import (
    UserSerializer,
    UserDetailSerializer,
    UserRegistrationSerializer,
    UserStatsSerializer,
    PasswordChangeSerializer,
    UsernameChangeSerializer,
    AccountDeleteSerializer,
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

    # Read-only: profile edits go through CurrentUserView/UsernameChangeView,
    # deletion through AccountDeleteView. ModelViewSet's default update/
    # destroy would otherwise let IsOwnerOrReadOnly permit an unconfirmed
    # PATCH or hard DELETE straight through this router.
    http_method_names = ['get', 'head', 'options']

    queryset = User.objects.filter(is_active=True)
    permission_classes = [permissions.IsAuthenticatedOrReadOnly, IsOwnerOrReadOnly]
    search_fields = ['username', 'first_name', 'last_name']
    ordering_fields = ['reputation_score', 'contribution_count', 'created_at']
    ordering = ['-reputation_score']

    def get_serializer_class(self):
        if self.action == 'retrieve':
            obj = self.get_object()
            if self.request.user == obj:
                return UserDetailSerializer
        return UserSerializer

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
        from apps.components.models import Component
        from apps.components.serializers import ComponentListSerializer

        products = Product.objects.filter(
            created_by=user
        ).order_by('-created_at')[:20]

        components = Component.objects.filter(
            created_by=user
        ).order_by('-created_at')[:20]

        return Response({
            'products': ProductListSerializer(
                products, many=True, context={'request': request}
            ).data,
            'components': ComponentListSerializer(
                components, many=True, context={'request': request}
            ).data,
        })


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
            send_verification_email(user)
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
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'auth'

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


class UsernameChangeView(APIView):
    """Change username for authenticated user."""

    permission_classes = [permissions.IsAuthenticated]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'auth'

    @extend_schema(
        description='Change current user username',
        request=UsernameChangeSerializer,
        responses={200: UserDetailSerializer}
    )
    def post(self, request):
        serializer = UsernameChangeSerializer(
            data=request.data,
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)

        request.user.username = serializer.validated_data['new_username']
        request.user.save(update_fields=['username'])

        return Response(UserDetailSerializer(request.user).data)


class AccountDeleteView(APIView):
    """Deactivate and scrub the authenticated user's own account."""

    permission_classes = [permissions.IsAuthenticated]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'auth'

    @extend_schema(
        description='Delete (deactivate) the current user account',
        request=AccountDeleteSerializer,
        responses={200: None}
    )
    def post(self, request):
        serializer = AccountDeleteSerializer(
            data=request.data,
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)

        user = request.user
        user.deactivate_account()

        # Log out everywhere: blacklist every outstanding token for this
        # user, not just the current session's.
        from rest_framework_simplejwt.token_blacklist.models import OutstandingToken, BlacklistedToken
        for token in OutstandingToken.objects.filter(user=user):
            BlacklistedToken.objects.get_or_create(token=token)

        from apps.api.urls import clear_token_cookies

        response = Response({'message': 'Your account has been deleted.'})
        return clear_token_cookies(response)


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
        from utils.email import verify_email_token

        token = request.data.get('token')

        if not token:
            return Response(
                {'error': 'Missing token'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Verify the signed token
        data = verify_email_token(token)
        if not data:
            return Response(
                {'error': 'Invalid or expired verification link'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            user = User.objects.get(pk=data['user_id'])
        except User.DoesNotExist:
            return Response(
                {'error': 'User not found'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Verify email matches
        if user.email != data['email']:
            return Response(
                {'error': 'Email mismatch'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if user.email_verified:
            return Response({'message': 'Email already verified'})

        from django.utils import timezone
        user.email_verified = True
        user.email_verified_at = timezone.now()
        user.save(update_fields=['email_verified', 'email_verified_at'])

        return Response({'message': 'Email verified successfully'})


class ResendVerificationView(APIView):
    """Resend verification email to user."""

    permission_classes = [permissions.AllowAny]
    authentication_classes = []
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'auth'

    @extend_schema(
        description='Resend verification email',
        responses={200: None}
    )
    def post(self, request):
        email = request.data.get('email')

        if not email:
            return Response(
                {'error': 'Email is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            # Don't reveal if email exists
            return Response({'message': 'If an account exists with this email, a verification link has been sent.'})

        if user.email_verified:
            return Response({'message': 'Email is already verified.'})

        try:
            send_verification_email(user)
        except Exception:
            return Response(
                {'error': 'Failed to send verification email. Please try again later.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        return Response({'message': 'If an account exists with this email, a verification link has been sent.'})


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


@method_decorator(csrf_exempt, name='dispatch')
class GoogleAuthView(APIView):
    """Authenticate or register a user via Google OAuth ID token."""

    permission_classes = [permissions.AllowAny]
    authentication_classes = []
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'auth'

    def post(self, request):
        from google.oauth2 import id_token
        from google.auth.transport import requests as google_requests

        credential = request.data.get('credential')
        if not credential:
            return Response(
                {'error': 'Missing credential'},
                status=status.HTTP_400_BAD_REQUEST
            )

        client_id = getattr(settings, 'OAUTH_GOOGLE_CLIENT_ID', None)
        if not client_id:
            return Response(
                {'error': 'Google OAuth is not configured'},
                status=status.HTTP_503_SERVICE_UNAVAILABLE
            )

        # Verify the Google ID token
        try:
            idinfo = id_token.verify_oauth2_token(
                credential,
                google_requests.Request(),
                client_id,
            )
        except ValueError:
            return Response(
                {'error': 'Invalid Google token'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Reject unverified emails
        if not idinfo.get('email_verified'):
            return Response(
                {'error': 'Google email is not verified'},
                status=status.HTTP_400_BAD_REQUEST
            )

        email = idinfo['email'].lower()
        created = False

        try:
            user = User.objects.get(email__iexact=email)

            # Existing user from a different OAuth provider
            if user.oauth_provider and user.oauth_provider != 'google':
                return Response(
                    {'error': f'This email is linked to a {user.oauth_provider} account.'},
                    status=status.HTTP_409_CONFLICT
                )

            # Existing email/password user — link Google
            if not user.oauth_provider:
                user.oauth_provider = 'google'
                user.email_verified = True
                user.save(update_fields=['oauth_provider', 'email_verified'])

        except User.DoesNotExist:
            # Generate a unique username from email prefix
            base_username = email.split('@')[0]
            # Keep only alphanumeric and underscores
            base_username = ''.join(
                c if c.isalnum() or c == '_' else '' for c in base_username
            )
            if not base_username:
                base_username = 'user'
            base_username = base_username[:20]

            username = base_username
            suffix = 1
            while User.objects.filter(username__iexact=username).exists():
                username = f'{base_username}{suffix}'
                suffix += 1

            user = User.objects.create_user(
                username=username,
                email=email,
                password=None,
                oauth_provider='google',
                email_verified=True,
            )
            created = True

        # Issue JWT tokens
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)
        refresh_token = str(refresh)

        from apps.api.urls import set_token_cookies

        response_data = {
            'user': UserSerializer(user).data,
            'created': created,
        }
        response = Response(
            response_data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )
        set_token_cookies(response, access_token, refresh_token)
        return response


class GitHubAuthView(APIView):
    """Authenticate or register a user via GitHub OAuth authorization code."""

    permission_classes = [permissions.AllowAny]
    authentication_classes = []
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'auth'

    def post(self, request):
        import requests as http_requests

        code = request.data.get('code')
        if not code:
            return Response(
                {'error': 'Missing code'},
                status=status.HTTP_400_BAD_REQUEST
            )

        client_id = getattr(settings, 'OAUTH_GITHUB_CLIENT_ID', None)
        client_secret = getattr(settings, 'OAUTH_GITHUB_CLIENT_SECRET', None)
        if not client_id or not client_secret:
            return Response(
                {'error': 'GitHub OAuth is not configured'},
                status=status.HTTP_503_SERVICE_UNAVAILABLE
            )

        # Exchange code for access_token
        try:
            token_resp = http_requests.post(
                'https://github.com/login/oauth/access_token',
                json={'client_id': client_id, 'client_secret': client_secret, 'code': code},
                headers={'Accept': 'application/json'},
                timeout=10,
            )
            token_data = token_resp.json()
        except Exception:
            return Response(
                {'error': 'Failed to contact GitHub'},
                status=status.HTTP_502_BAD_GATEWAY
            )

        access_token = token_data.get('access_token')
        if not access_token:
            return Response(
                {'error': 'GitHub authentication failed'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Get GitHub user profile
        try:
            user_resp = http_requests.get(
                'https://api.github.com/user',
                headers={
                    'Authorization': f'Bearer {access_token}',
                    'Accept': 'application/vnd.github+json',
                },
                timeout=10,
            )
            github_user = user_resp.json()
        except Exception:
            return Response(
                {'error': 'Failed to get GitHub user info'},
                status=status.HTTP_502_BAD_GATEWAY
            )

        # Resolve email — may be private, so also check /user/emails
        email = github_user.get('email')
        if not email:
            try:
                emails_resp = http_requests.get(
                    'https://api.github.com/user/emails',
                    headers={'Authorization': f'Bearer {access_token}'},
                    timeout=10,
                )
                primary = next(
                    (e for e in emails_resp.json() if e.get('primary') and e.get('verified')),
                    None
                )
                if primary:
                    email = primary['email']
            except Exception:
                pass

        if not email:
            return Response(
                {'error': 'No verified email on GitHub account. Please make your email public or verify it on GitHub.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        email = email.lower()
        github_login = github_user.get('login', '')
        created = False

        try:
            user = User.objects.get(email__iexact=email)
            if user.oauth_provider and user.oauth_provider != 'github':
                return Response(
                    {'error': f'This email is linked to a {user.oauth_provider} account.'},
                    status=status.HTTP_409_CONFLICT
                )
            if not user.oauth_provider:
                user.oauth_provider = 'github'
                user.email_verified = True
                user.save(update_fields=['oauth_provider', 'email_verified'])
        except User.DoesNotExist:
            base_username = ''.join(
                c if c.isalnum() or c == '_' else '' for c in github_login
            )[:20] or 'user'
            username = base_username
            suffix = 1
            while User.objects.filter(username__iexact=username).exists():
                username = f'{base_username}{suffix}'
                suffix += 1

            user = User.objects.create_user(
                username=username,
                email=email,
                password=None,
                oauth_provider='github',
                email_verified=True,
            )
            created = True

        refresh = RefreshToken.for_user(user)
        access_token_str = str(refresh.access_token)
        refresh_token_str = str(refresh)

        from apps.api.urls import set_token_cookies

        response_data = {
            'user': UserSerializer(user).data,
            'created': created,
        }
        response = Response(
            response_data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )
        set_token_cookies(response, access_token_str, refresh_token_str)
        return response
