"""
Component views for Junkbin.io API
"""
from datetime import timedelta

from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from django.db.models import Sum, F
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from drf_spectacular.utils import extend_schema, extend_schema_view

from utils.cache import staff_key_prefix
from apps.api.metrics import component_view_counter

from .models import Component, ComponentImage, ComponentDatasheet, ComponentViewStats, ProductComponent, ComponentVote
from .serializers import (
    ComponentListSerializer,
    ComponentDetailSerializer,
    ComponentCreateSerializer,
    ComponentImageSerializer,
    ComponentImageUploadSerializer,
    ComponentDatasheetSerializer,
    ComponentDatasheetUploadSerializer,
    ProductComponentSerializer,
    ProductComponentCreateSerializer,
    CrossReferenceResultSerializer,
    ComponentVoteSerializer,
    ComponentVoteDetailSerializer,
)
from .filters import ComponentFilter, ProductComponentFilter
from apps.api.permissions import IsOwnerOrReadOnly, IsVerifiedEmail
from apps.api.throttling import LookupRateThrottle


@extend_schema_view(
    list=extend_schema(description='List all components'),
    retrieve=extend_schema(description='Get detailed component information'),
    create=extend_schema(description='Create a new component entry'),
)
class ComponentViewSet(viewsets.ModelViewSet):
    """
    ViewSet for component CRUD operations.
    """

    queryset = Component.objects.select_related('created_by').prefetch_related('images')
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
        if self.action in ['create', 'add_cross_reference', 'upload_image', 'upload_datasheet']:
            return [permissions.IsAuthenticated(), IsVerifiedEmail()]
        elif self.action == 'lookup':
            return [permissions.IsAuthenticated()]
        elif self.action in ['update', 'partial_update']:
            # Require authentication AND ownership (or staff/moderator)
            return [permissions.IsAuthenticated(), IsOwnerOrReadOnly()]
        elif self.action == 'destroy':
            return [permissions.IsAdminUser()]
        return [permissions.AllowAny()]

    @method_decorator(cache_page(60 * 5, key_prefix=staff_key_prefix))
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        today = timezone.now().date()
        ComponentViewStats.objects.update_or_create(
            component=instance, date=today,
            defaults={},
        )
        ComponentViewStats.objects.filter(
            component=instance, date=today,
        ).update(view_count=F('view_count') + 1)

        if request.user.is_authenticated:
            from apps.users.models import UserActivity
            UserActivity.objects.create(
                user=request.user,
                activity_type='component_view',
                details={
                    'component_id': str(instance.id),
                    'part_number': instance.part_number,
                },
            )
        component_view_counter.inc()
        return super().retrieve(request, *args, **kwargs)

    @action(
        detail=True,
        methods=['post'],
        parser_classes=[MultiPartParser, FormParser]
    )
    def upload_image(self, request, pk=None):
        """Upload an image for this component."""
        from apps.api.metrics import submission_counter

        component = self.get_object()
        serializer = ComponentImageUploadSerializer(data=request.data)
        if serializer.is_valid():
            image = serializer.save(
                component=component,
                uploaded_by=request.user
            )
            submission_counter.labels(content_type='component_image').inc()

            if request.user.can_submit_without_review:
                image.is_approved = True
                image.save(update_fields=['is_approved'])
                request.user.increment_contribution()

            return Response(
                ComponentImageSerializer(image, context={'request': request}).data,
                status=status.HTTP_201_CREATED
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'], parser_classes=[MultiPartParser, FormParser])
    def upload_datasheet(self, request, pk=None):
        """Upload a datasheet file for this component."""
        component = self.get_object()
        serializer = ComponentDatasheetUploadSerializer(
            data=request.data, context={'request': request}
        )
        if serializer.is_valid():
            datasheet = serializer.save(component=component, uploaded_by=request.user)
            if request.user.can_submit_without_review:
                datasheet.is_approved = True
                datasheet.save(update_fields=['is_approved'])
                request.user.increment_contribution()
            return Response(
                ComponentDatasheetSerializer(datasheet, context={'request': request}).data,
                status=status.HTTP_201_CREATED,
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['get'])
    def images(self, request, pk=None):
        """Get all images for this component."""
        component = self.get_object()
        images = component.images.all()

        if not request.user.is_staff and not getattr(request.user, 'is_moderator', False):
            if request.user.is_authenticated:
                images = images.filter(
                    models.Q(is_approved=True) |
                    models.Q(uploaded_by=request.user)
                )
            else:
                images = images.filter(is_approved=True)

        serializer = ComponentImageSerializer(
            images, many=True, context={'request': request}
        )
        return Response(serializer.data)

    @method_decorator(cache_page(60 * 15))
    @action(detail=False, methods=['get'])
    def trending(self, request):
        """Top 20 most-viewed components in the last 30 days."""
        since = timezone.now().date() - timedelta(days=30)
        trending_ids = (
            ComponentViewStats.objects.filter(date__gte=since)
            .values('component_id')
            .annotate(total_views=Sum('view_count'))
            .order_by('-total_views')[:20]
        )
        component_ids = [t['component_id'] for t in trending_ids]
        views_map = {t['component_id']: t['total_views'] for t in trending_ids}

        components = Component.objects.filter(id__in=component_ids)
        # Preserve ordering by views
        components_by_id = {c.id: c for c in components}
        ordered = [components_by_id[cid] for cid in component_ids if cid in components_by_id]

        serializer = ComponentListSerializer(ordered, many=True)
        data = serializer.data
        for item in data:
            item['total_views'] = views_map.get(
                next((c.id for c in ordered if str(c.id) == item['id']), None), 0
            )
        return Response(data)

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

    @action(
        detail=True,
        methods=['post'],
        permission_classes=[permissions.IsAuthenticated],
        throttle_classes=[LookupRateThrottle],
    )
    def lookup(self, request, pk=None):
        """
        Trigger a Nexar API lookup for this component.

        Fetches pricing, availability, and datasheet data from Nexar
        (aggregating DigiKey, Mouser, and 100+ distributors).
        Result is cached in the component's specifications field.
        """
        from django.utils import timezone
        from .nexar import get_client

        component = self.get_object()
        client = get_client()

        if not client.is_configured:
            return Response(
                {'detail': 'Nexar API credentials not configured. Contact an admin.'},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        try:
            result = client.search_mpn(component.part_number, component.manufacturer)
        except Exception:
            return Response(
                {'detail': 'Nexar API request failed. Try again later.'},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        if not result:
            return Response(
                {'detail': 'No results found for this part number.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Cache in specifications
        specs = component.specifications or {}
        specs['nexar_data'] = {
            **result,
            'last_updated': timezone.now().isoformat(),
        }
        component.specifications = specs

        # Auto-fill datasheet if empty
        if not component.datasheet_url and result.get('datasheet_url'):
            component.datasheet_url = result['datasheet_url']

        if not component.octopart_url and result.get('mpn'):
            component.octopart_url = f"https://octopart.com/search?q={result['mpn']}"

        component.save(update_fields=['specifications', 'datasheet_url', 'octopart_url'])

        return Response(specs['nexar_data'])

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


class ComponentImageModerationViewSet(viewsets.ModelViewSet):
    """
    ViewSet for component image moderation.
    List and approve/reject pending component images (moderator/staff only).
    """

    queryset = ComponentImage.objects.select_related('component', 'uploaded_by')
    serializer_class = ComponentImageSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['is_approved', 'component', 'uploaded_by', 'image_type']
    ordering_fields = ['uploaded_at']
    ordering = ['-uploaded_at']

    def get_permissions(self):
        from apps.api.permissions import IsModeratorOrAdmin
        return [IsModeratorOrAdmin()]

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        """Approve a pending component image."""
        from django.conf import settings
        from apps.users.tasks import notify_contribution_reviewed

        image = self.get_object()
        if image.is_approved:
            return Response({'detail': 'Image is already approved.'}, status=status.HTTP_400_BAD_REQUEST)
        image.is_approved = True
        image.save(update_fields=['is_approved'])
        if image.uploaded_by:
            image.uploaded_by.increment_contribution()
            notify_contribution_reviewed.delay(
                str(image.uploaded_by.pk), 'Component Image', image.caption or f'{image.image_type or "component"} image',
                f'{settings.FRONTEND_URL}/components/{image.component_id}/products', True,
            )
        return Response({'detail': 'Image approved.'})

    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        """Reject and delete a pending component image."""
        from apps.users.tasks import notify_contribution_reviewed

        image = self.get_object()
        if image.is_approved:
            return Response({'detail': 'Cannot reject an already-approved image.'}, status=status.HTTP_400_BAD_REQUEST)
        if image.uploaded_by:
            notify_contribution_reviewed.delay(
                str(image.uploaded_by.pk), 'Component Image', image.caption or f'{image.image_type or "component"} image',
                '', False, request.data.get('notes', ''),
            )
        image.image.delete(save=False)
        image.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class ComponentDatasheetViewSet(viewsets.ModelViewSet):
    """
    ViewSet for component datasheet moderation.
    List and approve/reject pending datasheets (moderator/staff only).
    """

    queryset = ComponentDatasheet.objects.select_related('component', 'uploaded_by')
    serializer_class = ComponentDatasheetSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['is_approved', 'component', 'uploaded_by', 'source_type']
    ordering_fields = ['uploaded_at']
    ordering = ['-uploaded_at']

    def get_permissions(self):
        from apps.api.permissions import IsModeratorOrAdmin
        return [IsModeratorOrAdmin()]

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        """Approve a pending datasheet."""
        from django.conf import settings
        from apps.users.tasks import notify_contribution_reviewed

        datasheet = self.get_object()
        if datasheet.is_approved:
            return Response({'detail': 'Datasheet is already approved.'}, status=status.HTTP_400_BAD_REQUEST)
        datasheet.is_approved = True
        datasheet.save(update_fields=['is_approved'])
        if datasheet.uploaded_by:
            datasheet.uploaded_by.increment_contribution()
            notify_contribution_reviewed.delay(
                str(datasheet.uploaded_by.pk), 'Datasheet', datasheet.title,
                f'{settings.FRONTEND_URL}/components/{datasheet.component_id}/products', True,
            )
        return Response({'detail': 'Datasheet approved.'})

    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        """Reject and delete a pending datasheet."""
        from apps.users.tasks import notify_contribution_reviewed

        datasheet = self.get_object()
        if datasheet.is_approved:
            return Response({'detail': 'Cannot reject an already-approved datasheet.'}, status=status.HTTP_400_BAD_REQUEST)
        if datasheet.uploaded_by:
            notify_contribution_reviewed.delay(
                str(datasheet.uploaded_by.pk), 'Datasheet', datasheet.title,
                '', False, request.data.get('notes', ''),
            )
        datasheet.file.delete(save=False)
        datasheet.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# Import models for cross_reference action
from django.db import models
