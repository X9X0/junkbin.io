"""
Custom permissions for users app.
"""
from rest_framework import permissions


class IsOwnerOrReadOnly(permissions.BasePermission):
    """
    Object-level permission to only allow owners to edit their own profile.
    """

    def has_object_permission(self, request, view, obj):
        # Read permissions are allowed to any request
        if request.method in permissions.SAFE_METHODS:
            return True

        # Write permissions only allowed to the owner
        return obj == request.user


class IsModerator(permissions.BasePermission):
    """
    Permission check for moderator status.
    """

    def has_permission(self, request, view):
        return (
            request.user and
            request.user.is_authenticated and
            (request.user.is_moderator or request.user.is_staff)
        )


class IsTrustedUser(permissions.BasePermission):
    """
    Permission check for trusted user status.
    """

    def has_permission(self, request, view):
        return (
            request.user and
            request.user.is_authenticated and
            request.user.is_trusted
        )
