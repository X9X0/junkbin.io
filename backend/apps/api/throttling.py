"""
Throttling classes for Junkbin.io API
"""
from rest_framework.throttling import UserRateThrottle, AnonRateThrottle


class BurstRateThrottle(UserRateThrottle):
    """
    Throttle for burst requests (e.g., rapid searches).

    Allows short bursts but limits sustained high-frequency access.
    """

    scope = 'burst'


class SustainedRateThrottle(UserRateThrottle):
    """
    Throttle for sustained request rate.

    For regular API usage throughout the day.
    """

    scope = 'sustained'


class SubmissionRateThrottle(UserRateThrottle):
    """
    Throttle for content submissions.

    Prevents spam submissions. Staff and moderators are exempt.
    """

    scope = 'submission'

    def allow_request(self, request, view):
        user = request.user
        if user and user.is_authenticated and (
            user.is_staff or getattr(user, 'is_moderator', False)
        ):
            return True
        return super().allow_request(request, view)


class UploadRateThrottle(UserRateThrottle):
    """
    Throttle for file uploads (images, schematics, firmware).

    Kept separate from SubmissionRateThrottle: a single legitimate product
    submission commonly includes several photos, each a separate request,
    which would otherwise burn through the same budget as spam-prevention
    for new product/comment creation. Staff and moderators are exempt.
    """

    scope = 'upload'

    def allow_request(self, request, view):
        user = request.user
        if user and user.is_authenticated and (
            user.is_staff or getattr(user, 'is_moderator', False)
        ):
            return True
        return super().allow_request(request, view)


class ReportRateThrottle(UserRateThrottle):
    """
    Throttle for report submissions.

    Prevents report spam/abuse.
    """

    scope = 'report'


class AuthRateThrottle(AnonRateThrottle):
    """
    Throttle for authentication endpoints.

    Prevents brute force attacks.
    """

    scope = 'auth'


class SearchRateThrottle(UserRateThrottle):
    """
    Throttle for search requests.

    Search can be expensive, so we limit it more strictly.
    """

    scope = 'search'


class MessageRateThrottle(UserRateThrottle):
    """
    Throttle for sending messages.

    Prevents message spam.
    """

    scope = 'messaging'


class LookupRateThrottle(UserRateThrottle):
    """
    Throttle for external API lookups (Nexar/Octopart).

    External APIs have strict rate limits, so we limit lookups.
    """

    scope = 'lookup'


class BgRemovalRateThrottle(UserRateThrottle):
    """
    Throttle for background-removal preview requests.

    Each one is a real CPU inference pass (a few seconds), not a cheap DB
    query - limited more like an upload than a lookup. Staff and
    moderators are exempt, matching UploadRateThrottle.
    """

    scope = 'bg_removal'

    def allow_request(self, request, view):
        user = request.user
        if user and user.is_authenticated and (
            user.is_staff or getattr(user, 'is_moderator', False)
        ):
            return True
        return super().allow_request(request, view)
