"""
Component views for Junkbin.io API
"""
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from drf_spectacular.utils import extend_schema, extend_schema_view

from .models import Component, ProductComponent
from .serializers import (
    ComponentListSerializer,
    ComponentDetailSerializer,
    ComponentCreateSerializer,
    ProductComponentSerializer,
    ProductComponentCreateSerializer,
    CrossReferenceResultSerializer,
)
from .filters import ComponentFilter, ProductComponentFilter
from apps.api.permissions import IsOwnerOrReadOnly, IsVerifiedEmail


@extend_schema_view(
    list=extend_schema(description='List all components'),
    retrieve=extend_schema(description='Get detailed component information'),
    create=extend_schema(description='Create a new component entry'),
)
class ComponentViewSet(viewsets.ModelViewSet):
    """
    ViewSet for component CRUD operations.
    """

    queryset = Component.objects.select_related('created_by')
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = ComponentFilter
    search_fields = ['part_number', 'manufacturer', 'description', 'typical_function']
    ordering_fields = ['created_at', 'manufacturer', 'part_number', 'usage_count']
    ordering = ['-usage_count', 'manufacturer', 'part_number']

    def get_serializer_class(self):
        if self.action == 'list':
            return ComponentListSerializer
        elif self.action in ['create', 'update', 'partial_update']:
            return ComponentCreateSerializer
        return ComponentDetailSerializer

    def get_permissions(self):
        if self.action in ['create', 'add_cross_reference']:
            return [permissions.IsAuthenticated(), IsVerifiedEmail()]
        elif self.action in ['update', 'partial_update']:
            # Require authentication AND ownership (or staff/moderator)
            return [permissions.IsAuthenticated(), IsOwnerOrReadOnly()]
        elif self.action == 'destroy':
            return [permissions.IsAdminUser()]
        return [permissions.AllowAny()]

    @action(detail=True, methods=['get'])
    def products(self, request, pk=None):
        """Get all products containing this component."""
        component = self.get_object()

        from apps.products.models import Product
        from apps.products.serializers import ProductListSerializer

        products = Product.objects.filter(
            product_components__component=component,
            is_approved=True
        ).distinct()

        # Pagination
        page = self.paginate_queryset(products)
        if page is not None:
            serializer = ProductListSerializer(
                page,
                many=True,
                context={'request': request}
            )
            return self.get_paginated_response(serializer.data)

        serializer = ProductListSerializer(
            products,
            many=True,
            context={'request': request}
        )
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def add_cross_reference(self, request, pk=None):
        """Add a cross-reference to another component."""
        component = self.get_object()
        other_id = request.data.get('component_id')

        if not other_id:
            return Response(
                {'detail': 'component_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            other_component = Component.objects.get(pk=other_id)
        except Component.DoesNotExist:
            return Response(
                {'detail': 'Component not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        if component == other_component:
            return Response(
                {'detail': 'Cannot cross-reference a component with itself'},
                status=status.HTTP_400_BAD_REQUEST
            )

        component.cross_references.add(other_component)
        return Response({'detail': 'Cross-reference added'})

    @action(detail=False, methods=['get'])
    def types(self, request):
        """Get list of component types with counts."""
        from django.db.models import Count
        from django.conf import settings

        types = (
            Component.objects
            .values('component_type')
            .annotate(count=Count('id'))
            .order_by('-count')
        )

        # Add display names
        type_dict = dict(settings.COMPONENT_TYPES)
        result = [
            {
                'value': t['component_type'],
                'label': type_dict.get(t['component_type'], t['component_type']),
                'count': t['count']
            }
            for t in types
        ]

        return Response(result)

    @action(detail=False, methods=['get'])
    def manufacturers(self, request):
        """Get list of component manufacturers with counts."""
        from django.db.models import Count

        manufacturers = (
            Component.objects
            .values('manufacturer')
            .annotate(count=Count('id'))
            .order_by('-count')[:50]
        )

        return Response(list(manufacturers))

    @action(detail=False, methods=['get'])
    def cross_reference(self, request):
        """
        Search for products containing a specific part number.

        This is the main feature: "Find products containing part X"
        """
        part_number = request.query_params.get('part')
        if not part_number:
            return Response(
                {'detail': 'part query parameter is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Find matching components
        components = Component.objects.filter(
            models.Q(part_number__icontains=part_number) |
            models.Q(alternative_part_numbers__contains=[part_number])
        )

        results = []
        for component in components:
            from apps.products.models import Product
            from apps.products.serializers import ProductListSerializer

            products = Product.objects.filter(
                product_components__component=component,
                is_approved=True
            ).distinct()[:10]

            results.append({
                'component': ComponentListSerializer(component).data,
                'products': ProductListSerializer(
                    products,
                    many=True,
                    context={'request': request}
                ).data,
                'total_products': Product.objects.filter(
                    product_components__component=component,
                    is_approved=True
                ).count()
            })

        return Response(results)


class ProductComponentViewSet(viewsets.ModelViewSet):
    """
    ViewSet for product-component relationships.
    """

    queryset = ProductComponent.objects.select_related(
        'product', 'component', 'created_by'
    )
    filter_backends = [DjangoFilterBackend]
    filterset_class = ProductComponentFilter

    def get_serializer_class(self):
        if self.action in ['create']:
            return ProductComponentCreateSerializer
        return ProductComponentSerializer

    def get_permissions(self):
        if self.action == 'create':
            return [permissions.IsAuthenticated(), IsVerifiedEmail()]
        elif self.action in ['update', 'partial_update']:
            # Require authentication AND ownership (or staff/moderator)
            return [permissions.IsAuthenticated(), IsOwnerOrReadOnly()]
        elif self.action == 'destroy':
            return [permissions.IsAdminUser()]
        return [permissions.AllowAny()]

    @action(detail=True, methods=['post'])
    def verify(self, request, pk=None):
        """Mark this product-component mapping as verified."""
        from django.utils import timezone

        pc = self.get_object()

        # Only moderators/staff can verify
        if not request.user.is_moderator and not request.user.is_staff:
            return Response(
                {'detail': 'Only moderators can verify mappings'},
                status=status.HTTP_403_FORBIDDEN
            )

        pc.is_verified = True
        pc.verified_by = request.user
        pc.verified_at = timezone.now()
        pc.save()

        return Response({'detail': 'Mapping verified'})


# Import models for cross_reference action
from django.db import models
