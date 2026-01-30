"""
Pagination classes for Junkbin.io API
"""
from rest_framework.pagination import PageNumberPagination, CursorPagination


class StandardResultsSetPagination(PageNumberPagination):
    """
    Standard pagination for most endpoints.

    - Default: 20 items per page
    - Max: 100 items per page
    - Includes count and navigation links
    """

    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100

    def get_paginated_response(self, data):
        response = super().get_paginated_response(data)
        response.data['page'] = self.page.number
        response.data['total_pages'] = self.page.paginator.num_pages
        return response


class LargeResultsSetPagination(PageNumberPagination):
    """
    Larger pagination for bulk data endpoints.

    - Default: 50 items per page
    - Max: 500 items per page
    """

    page_size = 50
    page_size_query_param = 'page_size'
    max_page_size = 500


class SmallResultsSetPagination(PageNumberPagination):
    """
    Smaller pagination for embedded lists.

    - Default: 10 items per page
    - Max: 50 items per page
    """

    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 50


class TimelineCursorPagination(CursorPagination):
    """
    Cursor-based pagination for timeline/feed endpoints.

    More efficient for large datasets with frequent updates.
    """

    page_size = 20
    ordering = '-created_at'
    cursor_query_param = 'cursor'
