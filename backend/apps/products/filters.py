"""
Product filters for Junkbin.io API
"""
import django_filters
from django.db.models import Q

from .models import Product


class ProductFilter(django_filters.FilterSet):
    """
    Filter for products with various search options.
    """

    # Text search across multiple fields
    q = django_filters.CharFilter(method='filter_search')

    # Exact and partial matches
    manufacturer = django_filters.CharFilter(lookup_expr='icontains')
    model_number = django_filters.CharFilter(lookup_expr='icontains')
    category = django_filters.CharFilter(lookup_expr='exact')
    region = django_filters.CharFilter(lookup_expr='exact')

    # Year range
    year_min = django_filters.NumberFilter(
        field_name='year_manufactured',
        lookup_expr='gte'
    )
    year_max = django_filters.NumberFilter(
        field_name='year_manufactured',
        lookup_expr='lte'
    )

    # FCC ID search
    fcc_id = django_filters.CharFilter(lookup_expr='icontains')

    # Component filter (products containing a specific component)
    has_component = django_filters.UUIDFilter(method='filter_has_component')

    # Status filters
    is_approved = django_filters.BooleanFilter()
    is_featured = django_filters.BooleanFilter()

    # Created by user
    created_by = django_filters.UUIDFilter(field_name='created_by__id')

    # Date range
    created_after = django_filters.DateFilter(
        field_name='created_at',
        lookup_expr='gte'
    )
    created_before = django_filters.DateFilter(
        field_name='created_at',
        lookup_expr='lte'
    )

    # Ordering
    ordering = django_filters.OrderingFilter(
        fields=(
            ('created_at', 'created_at'),
            ('manufacturer', 'manufacturer'),
            ('component_count', 'component_count'),
            ('view_count', 'view_count'),
        )
    )

    class Meta:
        model = Product
        fields = [
            'q', 'manufacturer', 'model_number', 'category', 'region',
            'year_min', 'year_max', 'fcc_id', 'has_component',
            'is_approved', 'is_featured', 'created_by'
        ]

    def filter_search(self, queryset, name, value):
        """
        Full-text search across multiple fields.
        """
        if not value:
            return queryset

        return queryset.filter(
            Q(manufacturer__icontains=value) |
            Q(model_number__icontains=value) |
            Q(description__icontains=value) |
            Q(fcc_id__icontains=value) |
            Q(part_number__icontains=value)
        )

    def filter_has_component(self, queryset, name, value):
        """
        Filter products that contain a specific component.
        """
        if not value:
            return queryset

        return queryset.filter(
            product_components__component_id=value
        ).distinct()
