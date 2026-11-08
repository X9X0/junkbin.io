"""
Product filters for Junkbin.io API
"""
import django_filters
from django.db.models import Exists, OuterRef, Q
from rest_framework.filters import OrderingFilter
from django.contrib.postgres.search import SearchQuery, SearchRank

from .models import Product


def has_photo(model):
    """Exists() for 'has an approved photo of its own' on a Product or Component queryset."""
    related = model._meta.get_field('images')
    return Exists(related.related_model.objects.filter(**{related.remote_field.name: OuterRef('pk')}, is_approved=True))


class PhotoFirstOrderingFilter(OrderingFilter):
    """
    'Newest first' lists what has a photo before what has none, each newest first, so the
    first pages of the catalogue aren't rows of empty placeholders. Nothing is hidden: an
    item without a photo is still in the list, the count and its category, and moves up
    once a photo of it is approved.
    """

    def filter_queryset(self, request, queryset, view):
        if request.query_params.get(self.ordering_param) == MIX and queryset.model is Product:
            return category_mix(queryset)
        ordering = self.get_ordering(request, queryset, view)
        if ordering and ordering[0] == '-created_at':
            return queryset.annotate(has_photo=has_photo(queryset.model)).order_by('-has_photo', *ordering)
        return super().filter_queryset(request, queryset, view)


MIX = 'mix'


def category_mix(queryset):
    """?ordering=mix - newest first, but taking turns between categories: the newest product with a
    photo from each category, then the second newest of each, and so on; products without a photo
    follow in the same pattern. One busy category (thousands of imported laptop boards) can't fill
    the first pages, so the catalogue shows the range of what's here."""
    from django.db.models import F, Window
    from django.db.models.functions import RowNumber
    return (queryset.annotate(has_photo=has_photo(Product))
            .annotate(turn=Window(RowNumber(), partition_by=[F('has_photo'), F('category')],
                                  order_by=F('created_at').desc()))
            .order_by('-has_photo', 'turn', '-created_at'))


class MixOrderingFilter(django_filters.OrderingFilter):
    """Accepts ?ordering=mix (the category mix, done by PhotoFirstOrderingFilter) besides the fields."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.extra['choices'] = [*self.extra['choices'], (MIX, 'Category mix')]

    def filter(self, qs, value):
        if value and MIX in value:
            return qs
        return super().filter(qs, value)


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

    # Ordering ('mix' is applied by PhotoFirstOrderingFilter)
    ordering = MixOrderingFilter(
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
        Full-text search using PostgreSQL search vectors with icontains fallback.
        """
        if not value:
            return queryset

        # Short queries (1-2 chars) don't work well with FTS — use icontains
        if len(value) <= 2:
            return queryset.filter(
                Q(manufacturer__icontains=value) |
                Q(model_number__icontains=value) |
                Q(fcc_id__icontains=value)
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
            Q(manufacturer__icontains=value) |
            Q(model_number__icontains=value) |
            Q(description__icontains=value) |
            Q(fcc_id__icontains=value)
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
