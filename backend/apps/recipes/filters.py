"""
Recipe filters for Junkbin.io API
"""
import django_filters
from django.db.models import Q
from django.contrib.postgres.search import SearchQuery, SearchRank

from .models import Recipe


class RecipeFilter(django_filters.FilterSet):
    """
    Filter for recipes with full-text search and standard filters.
    """

    q = django_filters.CharFilter(method='filter_search')
    category = django_filters.CharFilter(lookup_expr='exact')
    difficulty = django_filters.CharFilter(lookup_expr='exact')
    is_approved = django_filters.BooleanFilter()
    is_featured = django_filters.BooleanFilter()
    created_by = django_filters.UUIDFilter(field_name='created_by__id')

    ordering = django_filters.OrderingFilter(
        fields=(
            ('created_at', 'created_at'),
            ('view_count', 'view_count'),
            ('component_count', 'component_count'),
            ('name', 'name'),
        )
    )

    class Meta:
        model = Recipe
        fields = [
            'q', 'category', 'difficulty',
            'is_approved', 'is_featured', 'created_by',
        ]

    def filter_search(self, queryset, name, value):
        """Full-text search with icontains fallback."""
        if not value:
            return queryset

        if len(value) <= 2:
            return queryset.filter(
                Q(name__icontains=value) |
                Q(category__icontains=value)
            )

        query = SearchQuery(value, search_type='plain')
        ranked = queryset.filter(search_vector=query).annotate(
            rank=SearchRank('search_vector', query)
        )

        if ranked.exists():
            return ranked.order_by('-rank')

        return queryset.filter(
            Q(name__icontains=value) |
            Q(description__icontains=value) |
            Q(category__icontains=value)
        )
