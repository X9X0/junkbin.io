"""
Component filters for Junkbin.io API
"""
import django_filters
from django.db.models import Q

from .models import Component, ProductComponent


class ComponentFilter(django_filters.FilterSet):
    """
    Filter for components with various search options.
    """

    # Text search across multiple fields
    q = django_filters.CharFilter(method='filter_search')

    # Exact and partial matches
    part_number = django_filters.CharFilter(lookup_expr='icontains')
    manufacturer = django_filters.CharFilter(lookup_expr='icontains')
    component_type = django_filters.CharFilter(lookup_expr='exact')
    package_type = django_filters.CharFilter(lookup_expr='icontains')
    typical_function = django_filters.CharFilter(lookup_expr='icontains')

    # Verification status
    is_verified = django_filters.BooleanFilter()

    # Has datasheet
    has_datasheet = django_filters.BooleanFilter(method='filter_has_datasheet')

    # Created by user
    created_by = django_filters.UUIDFilter(field_name='created_by__id')

    # Minimum usage count
    min_usage = django_filters.NumberFilter(
        field_name='usage_count',
        lookup_expr='gte'
    )

    # Ordering
    ordering = django_filters.OrderingFilter(
        fields=(
            ('created_at', 'created_at'),
            ('manufacturer', 'manufacturer'),
            ('part_number', 'part_number'),
            ('usage_count', 'usage_count'),
        )
    )

    class Meta:
        model = Component
        fields = [
            'q', 'part_number', 'manufacturer', 'component_type',
            'package_type', 'typical_function', 'is_verified',
            'has_datasheet', 'min_usage'
        ]

    def filter_search(self, queryset, name, value):
        """
        Full-text search across multiple fields.
        """
        if not value:
            return queryset

        return queryset.filter(
            Q(part_number__icontains=value) |
            Q(manufacturer__icontains=value) |
            Q(description__icontains=value) |
            Q(typical_function__icontains=value)
        )

    def filter_has_datasheet(self, queryset, name, value):
        """
        Filter components that have a datasheet URL.
        """
        if value:
            return queryset.exclude(datasheet_url='')
        return queryset.filter(datasheet_url='')


class ProductComponentFilter(django_filters.FilterSet):
    """
    Filter for product-component relationships.
    """

    product = django_filters.UUIDFilter(field_name='product__id')
    component = django_filters.UUIDFilter(field_name='component__id')
    submission_level = django_filters.CharFilter(lookup_expr='exact')
    is_verified = django_filters.BooleanFilter()
    board_name = django_filters.CharFilter(lookup_expr='icontains')

    class Meta:
        model = ProductComponent
        fields = ['product', 'component', 'submission_level', 'is_verified', 'board_name']
