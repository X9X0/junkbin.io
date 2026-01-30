"""
Unit tests for users app permissions.
"""
import pytest
from unittest.mock import Mock, MagicMock
from rest_framework.test import APIRequestFactory

from apps.users.permissions import IsOwnerOrReadOnly, IsModerator, IsTrustedUser


class TestIsOwnerOrReadOnly:
    """Tests for IsOwnerOrReadOnly permission."""

    @pytest.fixture
    def permission(self):
        return IsOwnerOrReadOnly()

    @pytest.fixture
    def request_factory(self):
        return APIRequestFactory()

    def test_safe_methods_allowed_for_anyone(self, permission, request_factory, user_factory):
        """GET, HEAD, OPTIONS are allowed for any user."""
        user = user_factory()
        other_user = user_factory()

        for method in ['get', 'head', 'options']:
            request = getattr(request_factory, method)('/test/')
            request.user = user
            view = Mock()

            # obj is a different user
            assert permission.has_object_permission(request, view, other_user) is True

    def test_owner_can_modify(self, permission, request_factory, user_factory):
        """Owner can modify their own object."""
        user = user_factory()

        for method in ['put', 'patch', 'delete']:
            request = getattr(request_factory, method)('/test/')
            request.user = user
            view = Mock()

            # obj is the same user
            assert permission.has_object_permission(request, view, user) is True

    def test_non_owner_cannot_modify(self, permission, request_factory, user_factory):
        """Non-owner cannot modify another user's object."""
        user = user_factory()
        other_user = user_factory()

        for method in ['put', 'patch', 'delete']:
            request = getattr(request_factory, method)('/test/')
            request.user = user
            view = Mock()

            # obj is a different user
            assert permission.has_object_permission(request, view, other_user) is False


class TestIsModerator:
    """Tests for IsModerator permission."""

    @pytest.fixture
    def permission(self):
        return IsModerator()

    def test_moderator_has_permission(self, permission, user_factory):
        """Moderator has permission."""
        user = user_factory(is_moderator=True)
        request = Mock()
        request.user = user
        view = Mock()

        assert permission.has_permission(request, view) is True

    def test_staff_has_permission(self, permission, user_factory):
        """Staff has permission."""
        user = user_factory(is_staff=True, is_moderator=False)
        request = Mock()
        request.user = user
        view = Mock()

        assert permission.has_permission(request, view) is True

    def test_regular_user_denied(self, permission, user_factory):
        """Regular user is denied."""
        user = user_factory(is_moderator=False, is_staff=False)
        request = Mock()
        request.user = user
        view = Mock()

        assert permission.has_permission(request, view) is False

    def test_unauthenticated_denied(self, permission):
        """Unauthenticated user is denied."""
        request = Mock()
        request.user = Mock()
        request.user.is_authenticated = False
        view = Mock()

        assert permission.has_permission(request, view) is False

    def test_none_user_denied(self, permission):
        """None user is denied."""
        request = Mock()
        request.user = None
        view = Mock()

        assert permission.has_permission(request, view) is False


class TestIsTrustedUser:
    """Tests for IsTrustedUser permission."""

    @pytest.fixture
    def permission(self):
        return IsTrustedUser()

    def test_trusted_user_has_permission(self, permission, user_factory):
        """Trusted user has permission."""
        user = user_factory(is_trusted=True)
        request = Mock()
        request.user = user
        view = Mock()

        assert permission.has_permission(request, view) is True

    def test_non_trusted_user_denied(self, permission, user_factory):
        """Non-trusted user is denied."""
        user = user_factory(is_trusted=False)
        request = Mock()
        request.user = user
        view = Mock()

        assert permission.has_permission(request, view) is False

    def test_unauthenticated_denied(self, permission):
        """Unauthenticated user is denied."""
        request = Mock()
        request.user = Mock()
        request.user.is_authenticated = False
        view = Mock()

        assert permission.has_permission(request, view) is False

    def test_none_user_denied(self, permission):
        """None user is denied."""
        request = Mock()
        request.user = None
        view = Mock()

        assert permission.has_permission(request, view) is False
