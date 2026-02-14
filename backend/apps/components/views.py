"""
Component views for Junkbin.io API
"""
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from drf_spectacular.utils import extend_schema, extend_schema_view

from utils.cache import staff_key_prefix

from .models import Component, ProductComponent, ComponentVote
from .serializers import (
    ComponentListSerializer,
    ComponentDetailSerializer,
    ComponentCreateSerializer,
    ProductComponentSerializer,
    ProductComponentCreateSerializer,
    CrossReferenceResultSerializer,
    ComponentVoteSerializer,
    ComponentVoteDetailSerializer,
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

    @method_decorator(cache_page(60 * 5, key_prefix=staff_key_prefix))
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

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

    @method_decorator(cache_page(60 * 60))
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

    @method_decorator(cache_page(60 * 60))
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
        from django.db.models import Count, Prefetch
        from apps.products.models import Product
        from apps.products.serializers import ProductListSerializer

        part_number = request.query_params.get('part')
        if not part_number:
            return Response(
                {'detail': 'part query parameter is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Find matching components with prefetched approved products and count
        approved_products = Product.objects.filter(
            is_approved=True
        ).distinct()

        components = Component.objects.filter(
            models.Q(part_number__icontains=part_number) |
            models.Q(alternative_part_numbers__contains=[part_number])
        ).prefetch_related(
            Prefetch(
                'product_components__product',
                queryset=approved_products,
            )
        ).annotate(
            total_approved_products=Count(
                'product_components__product',
                filter=models.Q(product_components__product__is_approved=True),
                distinct=True,
            )
        )

        results = []
        for component in components:
            # Get products from prefetched data (no extra queries)
            products = []
            seen = set()
            for pc in component.product_components.all():
                p = pc.product
                if p.is_approved and p.pk not in seen:
                    products.append(p)
                    seen.add(p.pk)
                if len(products) >= 10:
                    break

            results.append({
                'component': ComponentListSerializer(component).data,
                'products': ProductListSerializer(
                    products,
                    many=True,
                    context={'request': request}
                ).data,
                'total_products': component.total_approved_products,
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
            return [permissions.IsAuthenticated(), IsOwnerOrReadOnly()]
        elif self.action == 'destroy':
            return [permissions.IsAdminUser()]
        elif self.action in ['vote', 'remove_vote']:
            return [permissions.IsAuthenticated(), IsVerifiedEmail()]
        return [permissions.AllowAny()]

    @action(detail=True, methods=['post'])
    def verify(self, request, pk=None):
        """Mark this product-component mapping as verified (moderator override)."""
        from django.utils import timezone
        from apps.users.models import AdminAuditLog

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
        pc.needs_review = False
        pc.save(update_fields=[
            'is_verified', 'verified_by', 'verified_at', 'needs_review'
        ])

        AdminAuditLog.log_action(
            request=request,
            action_type='component_verified',
            target=pc,
            details={'method': 'moderator_override'},
        )

        return Response({'detail': 'Mapping verified'})

    @action(detail=True, methods=['post'], url_path='vote')
    def vote(self, request, pk=None):
        """Cast or change a vote on this product-component mapping."""
        from django.conf import settings as app_settings

        pc = self.get_object()

        # Block voting on own mappings
        if pc.created_by == request.user:
            return Response(
                {'detail': 'You cannot vote on your own mapping.'},
                status=status.HTTP_403_FORBIDDEN
            )

        serializer = ComponentVoteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        vote_type = serializer.validated_data['vote_type']
        weight = 1
        if request.user.is_trusted or request.user.is_moderator:
            weight = app_settings.TRUSTED_USER_VOTE_WEIGHT

        ComponentVote.objects.update_or_create(
            product_component=pc,
            user=request.user,
            defaults={
                'vote_type': vote_type,
                'weight': weight,
            }
        )

        pc.recalculate_votes()
        pc.refresh_from_db()

        return Response(ProductComponentSerializer(
            pc, context={'request': request}
        ).data)

    @vote.mapping.delete
    def remove_vote(self, request, pk=None):
        """Remove own vote from this product-component mapping."""
        pc = self.get_object()

        deleted, _ = ComponentVote.objects.filter(
            product_component=pc,
            user=request.user
        ).delete()

        if not deleted:
            return Response(
                {'detail': 'No vote to remove.'},
                status=status.HTTP_404_NOT_FOUND
            )

        pc.recalculate_votes()
        pc.refresh_from_db()

        return Response(ProductComponentSerializer(
            pc, context={'request': request}
        ).data)

    @action(detail=True, methods=['get'])
    def votes(self, request, pk=None):
        """List all votes for this product-component mapping."""
        pc = self.get_object()
        votes = pc.votes.select_related('user').order_by('-created_at')

        page = self.paginate_queryset(votes)
        if page is not None:
            serializer = ComponentVoteDetailSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = ComponentVoteDetailSerializer(votes, many=True)
        return Response(serializer.data)


# Import models for cross_reference action
from django.db import models
