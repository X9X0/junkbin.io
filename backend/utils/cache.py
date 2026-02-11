"""
Cache utilities for Junkbin.io
"""


def staff_key_prefix(request):
    """Separate cache entries for staff (who see unapproved items) vs public."""
    staff = '1' if request.user.is_authenticated and request.user.is_staff else '0'
    return f'v1:staff:{staff}'
