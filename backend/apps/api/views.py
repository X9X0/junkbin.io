"""
API views for Junkbin.io

Root API view and global search functionality.
"""
import time

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions, status
from rest_framework.reverse import reverse
from django.db.models import Q
from django.contrib.postgres.search import SearchQuery, SearchRank
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from drf_spectacular.utils import extend_schema, OpenApiParameter
from .throttling import SearchRateThrottle
from .metrics import search_counter, search_latency

from utils.cache import staff_key_prefix

from django.contrib.auth import get_user_model
from apps.products.models import Product
from apps.components.models import Component
from apps.products.serializers import ProductListSerializer
from apps.components.serializers import ComponentListSerializer
from apps.users.serializers import UserSerializer


class APIRootView(APIView):
    """
    API Root - Entry point for the Junkbin.io API

    Welcome to the Junkbin.io API - a community-driven database for
    documenting electronic components found in consumer electronics.

    "NO USER SERVICEABLE PARTS INSIDE" - We took that personally.
    """

    permission_classes = [permissions.AllowAny]

    @extend_schema(
        description='API root with links to all endpoints',
        responses={200: dict}
    )
    def get(self, request, format=None):
        return Response({
            'message': 'Welcome to Junkbin.io API',
            'version': '1.0.0',
            'tagline': 'NO USER SERVICEABLE PARTS INSIDE - We took that personally.',
            'endpoints': {
                # Authentication
                'auth': {
                    'token': reverse('token-obtain-pair', request=request, format=format),
                    'token_refresh': reverse('token-refresh', request=request, format=format),
                    'register': reverse('register', request=request, format=format),
                    'me': reverse('current-user', request=request, format=format),
                },
                # Resources
                'users': reverse('user-list', request=request, format=format),
                'products': reverse('product-list', request=request, format=format),
                'components': reverse('component-list', request=request, format=format),
                'submissions': reverse('submission-list', request=request, format=format),
                'reports': reverse('report-list', request=request, format=format),
                # Utilities
                'search': reverse('search', request=request, format=format),
                'health': reverse('health-check', request=request, format=format),
            },
            'documentation': {
                'swagger': reverse('swagger-ui', request=request, format=format),
                'redoc': reverse('redoc', request=request, format=format),
            }
        })


class SearchView(APIView):
    """
    Global search across products and components.
    """

    permission_classes = [permissions.AllowAny]
    throttle_classes = [SearchRateThrottle]

    @extend_schema(
        description='Search products and components',
        parameters=[
            OpenApiParameter(
                name='q',
                description='Search query',
                required=True,
                type=str
            ),
            OpenApiParameter(
                name='type',
                description='Filter by type (products, components, users, or all)',
                required=False,
                type=str,
                enum=['products', 'components', 'users', 'all']
            ),
            OpenApiParameter(
                name='limit',
                description='Maximum results per type',
                required=False,
                type=int
            ),
        ],
        responses={200: dict}
    )
    @method_decorator(cache_page(60 * 5, key_prefix=staff_key_prefix))
    def get(self, request):
        query = request.query_params.get('q', '').strip()
        search_type = request.query_params.get('type', 'all')
        limit = min(int(request.query_params.get('limit', 10)), 50)

        if not query:
            return Response(
                {'detail': 'Search query is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        start = time.monotonic()
        results = {}

        # Search products
        if search_type in ['all', 'products']:
            if len(query) > 2:
                search_q = SearchQuery(query, search_type='plain')
                products = list(Product.objects.filter(
                    search_vector=search_q, is_approved=True
                ).annotate(
                    rank=SearchRank('search_vector', search_q)
                ).order_by('-rank', '-view_count')[:limit])

                # Fall back to icontains if FTS returns nothing
                if not products:
                    products = list(Product.objects.filter(
                        Q(manufacturer__icontains=query) |
                        Q(model_number__icontains=query) |
                        Q(description__icontains=query) |
                        Q(fcc_id__icontains=query),
                        is_approved=True
                    ).order_by('-view_count')[:limit])
            else:
                products = list(Product.objects.filter(
                    Q(manufacturer__icontains=query) |
                    Q(model_number__icontains=query) |
                    Q(fcc_id__icontains=query),
                    is_approved=True
                ).order_by('-view_count')[:limit])

            # Also surface products whose teardown notes, schematic notes
            # (e.g. "this manual also covers the SN23x"), or comments
            # mention the query, even when the product's own fields don't.
            # Appended after the primary matches above since a direct
            # manufacturer/model match should outrank an incidental mention.
            remaining = limit - len(products)
            if remaining > 0:
                seen_ids = {p.id for p in products}
                note_matches = Product.objects.filter(
                    Q(teardown_notes__icontains=query) |
                    Q(schematics__repair_relevance__icontains=query) |
                    Q(schematics__description__icontains=query) |
                    Q(comments__content__icontains=query),
                    is_approved=True
                ).exclude(id__in=seen_ids).distinct().order_by('-view_count')[:remaining]
                products = products + list(note_matches)

            results['products'] = {
                'count': len(products),
                'results': ProductListSerializer(
                    products,
                    many=True,
                    context={'request': request}
                ).data
            }

        # Search components
        if search_type in ['all', 'components']:
            if len(query) > 2:
                search_q = SearchQuery(query, search_type='plain')
                components = Component.objects.filter(
                    search_vector=search_q
                ).annotate(
                    rank=SearchRank('search_vector', search_q)
                ).order_by('-rank', '-usage_count')[:limit]

                # Fall back to icontains if FTS returns nothing
                if not components.exists():
                    components = Component.objects.filter(
                        Q(part_number__icontains=query) |
                        Q(manufacturer__icontains=query) |
                        Q(description__icontains=query) |
                        Q(typical_function__icontains=query)
                    ).order_by('-usage_count')[:limit]
            else:
                components = Component.objects.filter(
                    Q(part_number__icontains=query) |
                    Q(manufacturer__icontains=query)
                ).order_by('-usage_count')[:limit]

            results['components'] = {
                'count': len(components),
                'results': ComponentListSerializer(
                    components,
                    many=True,
                    context={'request': request}
                ).data
            }

        # Search users
        if search_type in ['all', 'users']:
            User = get_user_model()
            user_results = User.objects.filter(
                Q(username__icontains=query) |
                Q(first_name__icontains=query) |
                Q(last_name__icontains=query),
                is_active=True,
            ).order_by('-reputation_score')[:limit]

            results['users'] = {
                'count': len(user_results),
                'results': UserSerializer(user_results, many=True).data,
            }

        # Log search query for analytics
        total_count = sum(
            r.get('count', 0) for r in results.values()
        )
        try:
            from .models import SearchQuery as SearchQueryLog
            SearchQueryLog.objects.create(
                query=query,
                user=request.user if request.user.is_authenticated else None,
                result_count=total_count,
                search_type=search_type,
                ip_address=request.META.get('REMOTE_ADDR'),
            )
        except Exception:
            pass  # Don't let logging failures break search
        search_latency.observe(time.monotonic() - start)
        search_counter.labels(has_results=str(total_count > 0)).inc()

        return Response({
            'query': query,
            'results': results
        })


class AnalyticsView(APIView):
    """
    Staff-only analytics dashboard endpoint.
    Returns aggregated metrics for the admin analytics page.
    """

    permission_classes = [permissions.IsAdminUser]

    @extend_schema(
        description='Get analytics dashboard data (staff only)',
        parameters=[
            OpenApiParameter(
                name='days',
                description='Number of days to look back',
                required=False,
                type=int,
            ),
        ],
        responses={200: dict},
    )
    def get(self, request):
        from datetime import timedelta
        from django.utils import timezone
        from django.db.models import Count, Q
        from django.db.models.functions import TruncDate
        from apps.users.models import UserActivity
        from apps.products.models import Product, Schematic
        from apps.components.models import Component, ComponentViewStats
        from apps.recipes.models import Recipe
        from .models import SearchQuery as SearchQueryLog

        days = int(request.query_params.get('days', 30))
        since = timezone.now() - timedelta(days=days)

        # Daily active users
        dau = list(
            UserActivity.objects.filter(created_at__gte=since)
            .annotate(date=TruncDate('created_at'))
            .values('date')
            .annotate(count=Count('user', distinct=True))
            .order_by('date')
        )
        for item in dau:
            item['date'] = item['date'].isoformat()

        # Search analytics
        total_searches = SearchQueryLog.objects.filter(created_at__gte=since).count()
        zero_result = SearchQueryLog.objects.filter(
            created_at__gte=since, result_count=0,
        ).count()
        top_queries = list(
            SearchQueryLog.objects.filter(created_at__gte=since)
            .values('query')
            .annotate(count=Count('id'))
            .order_by('-count')[:20]
        )

        # Trending components
        from django.db.models import Sum as DjSum
        trending = list(
            ComponentViewStats.objects.filter(date__gte=since.date())
            .values('component_id', 'component__part_number', 'component__manufacturer')
            .annotate(total_views=DjSum('view_count'))
            .order_by('-total_views')[:10]
        )

        # Content stats
        content_stats = {
            'products': Product.objects.filter(is_approved=True).count(),
            'components': Component.objects.count(),
            'schematics': Schematic.objects.filter(is_approved=True).count(),
            'recipes': Recipe.objects.filter(is_approved=True).count(),
        }

        # Activity breakdown by type
        activity_breakdown = list(
            UserActivity.objects.filter(created_at__gte=since)
            .values('activity_type')
            .annotate(count=Count('id'))
            .order_by('-count')
        )

        return Response({
            'dau': dau,
            'search_analytics': {
                'total': total_searches,
                'zero_result_pct': round(
                    (zero_result / total_searches * 100) if total_searches > 0 else 0, 1
                ),
                'top_queries': top_queries,
            },
            'trending_components': trending,
            'content_stats': content_stats,
            'activity_breakdown': activity_breakdown,
        })


class StatsView(APIView):
    """
    Public statistics endpoint for the landing page.
    Returns real counts from the database.
    """

    permission_classes = [permissions.AllowAny]

    @extend_schema(
        description='Get database statistics',
        responses={200: dict}
    )
    @method_decorator(cache_page(60 * 15))
    def get(self, request):
        from apps.products.models import Product, Schematic
        from apps.components.models import Component
        from django.contrib.auth import get_user_model

        User = get_user_model()

        return Response({
            'products': Product.objects.filter(is_approved=True).count(),
            'components': Component.objects.count(),
            'schematics': Schematic.objects.filter(is_approved=True).count(),
            'contributors': User.objects.filter(contribution_count__gt=0).count(),
        })


class HealthCheckView(APIView):
    """
    Health check endpoint for monitoring.
    """

    permission_classes = [permissions.AllowAny]
    throttle_classes = []  # No rate limiting for health checks

    @extend_schema(
        description='Health check endpoint',
        responses={200: dict}
    )
    def get(self, request):
        import logging
        logger = logging.getLogger(__name__)

        # Basic health check
        health = {
            'status': 'healthy',
            'services': {}
        }

        # Check database
        try:
            from django.db import connection
            with connection.cursor() as cursor:
                cursor.execute('SELECT 1')
            health['services']['database'] = 'ok'
        except Exception as e:
            health['status'] = 'degraded'
            health['services']['database'] = 'error'
            # Log the actual error for debugging, but don't expose to clients
            logger.error(f'Health check database error: {str(e)}')

        # Check cache
        try:
            from django.core.cache import cache
            cache.set('health_check', 'ok', 10)
            if cache.get('health_check') == 'ok':
                health['services']['cache'] = 'ok'
            else:
                health['services']['cache'] = 'error'
                logger.warning('Health check cache not responding correctly')
        except Exception as e:
            health['services']['cache'] = 'error'
            logger.error(f'Health check cache error: {str(e)}')

        status_code = 200 if health['status'] == 'healthy' else 503
        return Response(health, status=status_code)
