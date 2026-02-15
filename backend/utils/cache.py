"""
Cache utilities for Junkbin.io
"""


def staff_key_prefix(request):
    """Separate cache entries per user context.

    Staff see all items, authenticated users see approved + their own,
    anonymous users see only approved. Cache must be keyed accordingly
    to prevent one user's unapproved items leaking to others.
    """
    if request.user.is_authenticated:
        return f'v1:user:{request.user.pk}'
    return 'v1:anon'
