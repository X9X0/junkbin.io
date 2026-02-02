"""
API views for Junkbin.io

Root API view and global search functionality.
"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions, status
from rest_framework.reverse import reverse
from django.db.models import Q
from drf_spectacular.utils import extend_schema, OpenApiParameter

from apps.products.models import Product
from apps.components.models import Component
from apps.products.serializers import ProductListSerializer
from apps.components.serializers import ComponentListSerializer


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
                description='Filter by type (products, components, or all)',
                required=False,
                type=str,
                enum=['products', 'components', 'all']
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
    def get(self, request):
        query = request.query_params.get('q', '').strip()
        search_type = request.query_params.get('type', 'all')
        limit = min(int(request.query_params.get('limit', 10)), 50)

        if not query:
            return Response(
                {'detail': 'Search query is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        results = {}

        # Search products
        if search_type in ['all', 'products']:
            products = Product.objects.filter(
                Q(manufacturer__icontains=query) |
                Q(model_number__icontains=query) |
                Q(description__icontains=query) |
                Q(fcc_id__icontains=query),
                is_approved=True
            ).order_by('-view_count')[:limit]

            results['products'] = {
                'count': products.count(),
                'results': ProductListSerializer(
                    products,
                    many=True,
                    context={'request': request}
                ).data
            }

        # Search components
        if search_type in ['all', 'components']:
            components = Component.objects.filter(
                Q(part_number__icontains=query) |
                Q(manufacturer__icontains=query) |
                Q(description__icontains=query) |
                Q(typical_function__icontains=query)
            ).order_by('-usage_count')[:limit]

            results['components'] = {
                'count': components.count(),
                'results': ComponentListSerializer(
                    components,
                    many=True,
                    context={'request': request}
                ).data
            }

        return Response({
            'query': query,
            'results': results
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
