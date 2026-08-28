"""
Custom DRF permission classes for role-based access control.

These permissions are applied at the view level.
Backend enforcement — never rely on frontend hiding buttons.
"""
from rest_framework.permissions import BasePermission


class IsCreator(BasePermission):
    """
    Allow access only to users with role='creator'.

    Always returns 403 (not 401) for authenticated non-creators,
    to avoid leaking endpoint existence to unauthenticated callers.
    """
    message = 'Only creators can perform this action.'

    def has_permission(self, request, view) -> bool:
        return (
            request.user is not None
            and request.user.is_authenticated
            and request.user.is_creator
        )


class IsOwnerOrReadOnly(BasePermission):
    """
    Object-level permission: allow modification only by the resource owner.
    Read-only access for everyone else.
    """
    message = 'You do not have permission to modify this resource.'

    def has_object_permission(self, request, view, obj) -> bool:
        # Safe methods (GET, HEAD, OPTIONS) are allowed for everyone
        from rest_framework.permissions import SAFE_METHODS
        if request.method in SAFE_METHODS:
            return True
        # For write operations, check ownership
        return getattr(obj, 'creator', None) == request.user
