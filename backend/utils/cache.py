"""
Cache utilities for Junkbin.io
"""
from django.core.cache import cache

PAGE_CACHE_PATTERN = '*views.decorators.cache.cache_*'


def staff_key_prefix(request):
    """Separate cache entries per user context.

    Staff see all items, authenticated users see approved + their own,
    anonymous users see only approved. Cache must be keyed accordingly
    to prevent one user's unapproved items leaking to others.
    """
    if request.user.is_authenticated:
        return f'v1:user:{request.user.pk}'
    return 'v1:anon'


def clear_page_cache():
    """Drop every cached cache_page response (lists, counts, categories) so bulk
    changes made with queryset.update() - which no signal sees - show at once.
    Sessions, throttles and lockouts in the same cache are left alone.
    Returns the number of entries removed (None when the backend can't tell)."""
    try:
        client = cache._cache.get_client()
    except AttributeError:          # not Redis (tests, local dev): no way to select keys
        cache.clear()
        return None
    keys = list(client.scan_iter(match=PAGE_CACHE_PATTERN, count=1000))
    if keys:
        client.delete(*keys)
    return len(keys)
