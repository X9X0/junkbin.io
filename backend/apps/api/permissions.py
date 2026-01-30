"""
Custom API permissions for Junkbin.io
"""
from rest_framework import permissions


class IsOwnerOrReadOnly(permissions.BasePermission):
    """
    Object-level permission to only allow owners of an object to edit it.
    Assumes the model instance has a `created_by` attribute.
    """

    def has_object_permission(self, request, view, obj):
        # Read permissions are allowed to any request
        if request.method in permissions.SAFE_METHODS:
            return True

        # Check for created_by field
        if hasattr(obj, 'created_by'):
            return obj.created_by == request.user

        # Check for user field
        if hasattr(obj, 'user'):
            return obj.user == request.user

        return False


class IsModeratorOrAdmin(permissions.BasePermission):
    """
    Permission for moderators and admins only.
    """

    def has_permission(self, request, view):
        return (
            request.user and
            request.user.is_authenticated and
            (
                request.user.is_staff or
                getattr(request.user, 'is_moderator', False)
            )
        )


class IsTrustedOrModerated(permissions.BasePermission):
    """
    Allow trusted users to bypass moderation.
    Used for auto-approval of submissions.
    """

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        # Trusted users, moderators, and staff can bypass
        return (
            request.user.is_staff or
            getattr(request.user, 'is_moderator', False) or
            getattr(request.user, 'is_trusted', False)
        )


class IsVerifiedEmail(permissions.BasePermission):
    """
    Require email verification for certain actions.
    """

    message = 'Email verification required.'

    def has_permission(self, request, view):
        return (
            request.user and
            request.user.is_authenticated and
            request.user.email_verified
        )


class ReadOnly(permissions.BasePermission):
    """
    Read-only permission - allows only GET, HEAD, OPTIONS.
    """

    def has_permission(self, request, view):
        return request.method in permissions.SAFE_METHODS
