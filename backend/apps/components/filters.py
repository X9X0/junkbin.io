"""
Component filters for Junkbin.io API
"""
import django_filters
from django.db.models import Q
from django.contrib.postgres.search import SearchQuery, SearchRank

from .models import Component, ProductComponent
from .value_search import parse_value_query, spec_key_candidates

import re
from fractions import Fraction


def parse_rating(text, unit):
    """'50V' -> 50.0, '1/4W' -> 0.25, '62.5mW' -> 0.0625, '500mA'/'500MA' -> 0.5, '2kV' -> 2000; a bare
    number is taken in the base unit. None when the text isn't a rating in that unit."""
    m = re.fullmatch(rf'\s*(\d+/\d+|\d*\.?\d+)\s*([mMkK]?)\s*({unit})?\s*', text or '', re.I)
    if not m:
        return None
    number = float(Fraction(m.group(1))) if '/' in m.group(1) else float(m.group(1))
    prefix = m.group(2)
    if prefix and not m.group(3):
        return None                       # '5m' alone: milli-what?
    return number * {'': 1, 'm': 1e-3, 'M': 1e-3, 'k': 1e3, 'K': 1e3}[prefix]   # no mega-volts/watts/amps


class ComponentFilter(django_filters.FilterSet):
    """
    Filter for components with various search options.
    """

    # Text search across multiple fields
    q = django_filters.CharFilter(method='filter_search')

    # Structured value search (e.g. "10k", "4.7uF", "16MHz") against
    # specifications, not free text - see value_search.py.
    value = django_filters.CharFilter(method='filter_value')

    # Ratings a replacement must meet or exceed: "50V", "1/4W", "500mA"
    voltage_min = django_filters.CharFilter(method='filter_rating_min')
    power_min = django_filters.CharFilter(method='filter_rating_min')
    current_min = django_filters.CharFilter(method='filter_rating_min')
    tolerance = django_filters.CharFilter(method='filter_tolerance')
    dielectric = django_filters.CharFilter(method='filter_dielectric')

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
            'q', 'value', 'voltage_min', 'power_min', 'current_min', 'tolerance', 'dielectric',
            'part_number', 'manufacturer', 'component_type',
            'package_type', 'typical_function', 'is_verified',
            'has_datasheet', 'min_usage'
        ]

    RATING_KEYS = {
        'voltage_min': ('V', ('voltage_v', 'vds_v', 'vce_v')),
        'power_min': ('W', ('power_w',)),
        'current_min': ('A', ('current_a', 'iout_a', 'output_a', 'charge_current_a', 'irated_a')),
    }
    DIELECTRIC_ALIASES = {'NPO': 'C0G', 'NP0': 'C0G', 'COG': 'C0G'}

    def filter_value(self, queryset, name, value):
        """
        Structured value search (e.g. "10k", "4.7uF", "16MHz") - matches
        components whose specifications carry that physical quantity within
        a tolerance band, not a substring match against free text. Rejects
        (matches nothing) rather than ignoring text that isn't a value at
        all, since silently no-op'ing an applied filter would be misleading.
        """
        parsed = parse_value_query(value)
        if parsed is None:
            return queryset.none()

        kind, magnitude = parsed
        candidates = spec_key_candidates(kind, magnitude)
        if not candidates:
            return queryset.none()

        q = Q()
        for key, lo, hi in candidates:
            q |= Q(**{f'specifications__{key}__gte': lo, f'specifications__{key}__lte': hi})
        return queryset.filter(q)

    def filter_rating_min(self, queryset, name, value):
        """Components rated at least this much ("50V", "1/4W", "0.25", "500mA"). Like the value
        filter, text that isn't a rating matches nothing rather than being ignored."""
        unit, keys = self.RATING_KEYS[name]
        amount = parse_rating(value, unit)
        if amount is None:
            return queryset.none()
        q = Q()
        for key in keys:
            q |= Q(**{f'specifications__{key}__gte': amount * (1 - 1e-6)})
        return queryset.filter(q)

    def filter_tolerance(self, queryset, name, value):
        """Exact tolerance: '5', '5%', '±5%', '0.25pF', '+80/-20%'."""
        v = value.strip().replace(' ', '').lstrip('±')
        if not v:
            return queryset
        if re.fullmatch(r'\d+(?:\.\d+)?', v):
            v += '%'
        number = re.fullmatch(r'(\d+(?:\.\d+)?)%', v)
        q = Q(specifications__tolerance__iexact=v) | Q(specifications__tolerance__iexact=f'±{v}')
        if number:
            q |= Q(specifications__tolerance_pct=float(number.group(1)))
        return queryset.filter(q)

    def filter_dielectric(self, queryset, name, value):
        v = value.strip().upper()
        return queryset.filter(specifications__dielectric__iexact=self.DIELECTRIC_ALIASES.get(v, v)) if v else queryset

    def filter_search(self, queryset, name, value):
        """
        Full-text search using PostgreSQL search vectors with icontains fallback.
        """
        if not value:
            return queryset

        # Short queries (1-2 chars) don't work well with FTS — use icontains
        if len(value) <= 2:
            return queryset.filter(
                Q(part_number__icontains=value) |
                Q(manufacturer__icontains=value)
            )

        # Use full-text search with relevance ranking
        query = SearchQuery(value, search_type='plain')
        ranked = queryset.filter(search_vector=query).annotate(
            rank=SearchRank('search_vector', query)
        )

        if ranked.exists():
            return ranked.order_by('-rank')

        # Fall back to icontains for partial matches FTS can't find
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
