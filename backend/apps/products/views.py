"""
Product views for Junkbin.io API
"""
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from django.shortcuts import get_object_or_404
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from drf_spectacular.utils import extend_schema, extend_schema_view

from utils.cache import staff_key_prefix

from .models import Product, ProductImage, ProductComment, Schematic
from .serializers import (
    ProductListSerializer,
    ProductDetailSerializer,
    ProductCreateSerializer,
    ProductImageSerializer,
    ProductImageUploadSerializer,
    ProductCommentSerializer,
    ProductCommentCreateSerializer,
    SchematicSerializer,
    SchematicUploadSerializer,
)
from .filters import ProductFilter
from apps.users.permissions import IsModerator
from apps.api.permissions import IsOwnerOrReadOnly, IsModeratorOrAdmin, IsVerifiedEmail


@extend_schema_view(
    list=extend_schema(description='List all approved products'),
    retrieve=extend_schema(description='Get detailed product information'),
    create=extend_schema(description='Create a new product entry'),
    update=extend_schema(description='Update product information'),
    partial_update=extend_schema(description='Partially update product'),
)
class ProductViewSet(viewsets.ModelViewSet):
    """
    ViewSet for product CRUD operations.
    """

    queryset = Product.objects.select_related('created_by').prefetch_related('images')
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = ProductFilter
    search_fields = ['manufacturer', 'model_number', 'description', 'fcc_id']
    ordering_fields = ['created_at', 'manufacturer', 'component_count', 'view_count']
    ordering = ['-created_at']

    def get_queryset(self):
        queryset = super().get_queryset()

        # Non-staff users only see approved products (unless viewing their own)
        if not self.request.user.is_staff:
            if self.request.user.is_authenticated:
                queryset = queryset.filter(
                    models.Q(is_approved=True) |
                    models.Q(created_by=self.request.user)
                )
            else:
                queryset = queryset.filter(is_approved=True)

        return queryset

    def get_serializer_class(self):
        if self.action == 'list':
            return ProductListSerializer
        elif self.action == 'create':
            return ProductCreateSerializer
        return ProductDetailSerializer

    def get_permissions(self):
        if self.action in ['create', 'add_component', 'upload_image', 'upload_schematic', 'comments']:
            if self.request.method == 'POST':
                return [permissions.IsAuthenticated(), IsVerifiedEmail()]
            return [permissions.AllowAny()]
        elif self.action == 'comment_detail':
            return [permissions.IsAuthenticated()]
        elif self.action in ['update', 'partial_update', 'destroy']:
            return [permissions.IsAuthenticated(), IsOwnerOrReadOnly()]
        return [permissions.AllowAny()]

    @method_decorator(cache_page(60 * 5, key_prefix=staff_key_prefix))
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        # Increment view count
        instance.increment_view_count()
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    def perform_create(self, serializer):
        product = serializer.save(created_by=self.request.user)

        # Auto-approve for trusted users
        if self.request.user.can_submit_without_review:
            product.is_approved = True
            product.save(update_fields=['is_approved'])

    def perform_update(self, serializer):
        # Save the update (permission already checked by IsOwnerOrReadOnly)
        instance = serializer.save()
        # Reset approval if non-staff/moderator edits an approved product
        if not self.request.user.is_staff and not self.request.user.is_moderator:
            if instance.is_approved:
                instance.is_approved = False
                instance.save(update_fields=['is_approved'])

    @action(detail=True, methods=['get'])
    def components(self, request, pk=None):
        """Get all components for this product."""
        product = self.get_object()

        from apps.components.models import ProductComponent
        from apps.components.serializers import ProductComponentSerializer

        components = ProductComponent.objects.filter(
            product=product
        ).select_related('component', 'created_by')

        serializer = ProductComponentSerializer(components, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def add_component(self, request, pk=None):
        """Add a component to this product."""
        product = self.get_object()

        from apps.components.models import ProductComponent
        from apps.components.serializers import ProductComponentCreateSerializer

        serializer = ProductComponentCreateSerializer(
            data=request.data,
            context={'request': request}
        )
        if serializer.is_valid():
            product_component = serializer.save(product=product)

            # Return the created ProductComponent with component details
            from apps.components.serializers import ProductComponentSerializer
            return Response(
                ProductComponentSerializer(product_component).data,
                status=status.HTTP_201_CREATED
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(
        detail=True,
        methods=['post'],
        parser_classes=[MultiPartParser, FormParser]
    )
    def upload_image(self, request, pk=None):
        """Upload an image for this product."""
        product = self.get_object()

        # Check permission
        if product.created_by != request.user and not request.user.is_staff:
            return Response(
                {'detail': 'You do not have permission to add images to this product.'},
                status=status.HTTP_403_FORBIDDEN
            )

        serializer = ProductImageUploadSerializer(data=request.data)
        if serializer.is_valid():
            image = serializer.save(
                product=product,
                uploaded_by=request.user
            )
            return Response(
                ProductImageSerializer(image, context={'request': request}).data,
                status=status.HTTP_201_CREATED
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['get'])
    def images(self, request, pk=None):
        """Get all images for this product."""
        product = self.get_object()
        images = product.images.all()
        serializer = ProductImageSerializer(
            images,
            many=True,
            context={'request': request}
        )
        return Response(serializer.data)

    @method_decorator(cache_page(60 * 15))
    @action(detail=False, methods=['get'])
    def featured(self, request):
        """Get featured products."""
        products = self.get_queryset().filter(
            is_featured=True,
            is_approved=True
        )[:10]
        serializer = ProductListSerializer(
            products,
            many=True,
            context={'request': request}
        )
        return Response(serializer.data)

    @method_decorator(cache_page(60 * 10))
    @action(detail=False, methods=['get'])
    def recent(self, request):
        """Get recently added products."""
        products = self.get_queryset().filter(is_approved=True)[:20]
        serializer = ProductListSerializer(
            products,
            many=True,
            context={'request': request}
        )
        return Response(serializer.data)

    @method_decorator(cache_page(60 * 60))
    @action(detail=False, methods=['get'])
    def categories(self, request):
        """Get list of categories with counts."""
        from django.db.models import Count
        from django.conf import settings

        categories = (
            Product.objects
            .filter(is_approved=True)
            .values('category')
            .annotate(count=Count('id'))
            .order_by('-count')
        )

        # Add display names
        category_dict = dict(settings.PRODUCT_CATEGORIES)
        result = [
            {
                'value': cat['category'],
                'label': category_dict.get(cat['category'], cat['category']),
                'count': cat['count']
            }
            for cat in categories
        ]

        return Response(result)

    @method_decorator(cache_page(60 * 60))
    @action(detail=False, methods=['get'])
    def manufacturers(self, request):
        """Get list of manufacturers with counts."""
        from django.db.models import Count

        manufacturers = (
            Product.objects
            .filter(is_approved=True)
            .values('manufacturer')
            .annotate(count=Count('id'))
            .order_by('-count')[:50]
        )

        return Response(list(manufacturers))

    @action(detail=True, methods=['get'])
    def schematics(self, request, pk=None):
        """Get all schematics for this product."""
        product = self.get_object()
        schematics = product.schematics.filter(is_approved=True)

        # Staff can see unapproved schematics
        if request.user.is_staff:
            schematics = product.schematics.all()

        serializer = SchematicSerializer(
            schematics,
            many=True,
            context={'request': request}
        )
        return Response(serializer.data)

    @action(detail=True, methods=['get', 'post'])
    def comments(self, request, pk=None):
        """Get or add comments on a product."""
        product = self.get_object()

        if request.method == 'GET':
            comments = product.comments.select_related('author').all()
            page = self.paginate_queryset(comments)
            if page is not None:
                serializer = ProductCommentSerializer(page, many=True)
                return self.get_paginated_response(serializer.data)
            serializer = ProductCommentSerializer(comments, many=True)
            return Response(serializer.data)

        # POST — add comment
        serializer = ProductCommentCreateSerializer(
            data=request.data,
            context={'request': request, 'product': product}
        )
        serializer.is_valid(raise_exception=True)
        comment = serializer.save()
        return Response(
            ProductCommentSerializer(comment).data,
            status=status.HTTP_201_CREATED
        )

    @action(
        detail=True,
        methods=['delete'],
        url_path='comments/(?P<comment_id>[^/.]+)',
        url_name='comment-detail'
    )
    def comment_detail(self, request, pk=None, comment_id=None):
        """Delete a comment (owner or moderator only)."""
        product = self.get_object()
        comment = get_object_or_404(ProductComment, pk=comment_id, product=product)

        # Only author or moderator/staff can delete
        if comment.author != request.user and not request.user.is_staff and not request.user.is_moderator:
            return Response(
                {'detail': 'You do not have permission to delete this comment.'},
                status=status.HTTP_403_FORBIDDEN
            )

        comment.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        detail=True,
        methods=['post'],
        parser_classes=[MultiPartParser, FormParser]
    )
    def upload_schematic(self, request, pk=None):
        """
        Upload a schematic or service document for this product.

        Supports the Right to Repair movement by enabling sharing of
        technical documentation.
        """
        product = self.get_object()

        serializer = SchematicUploadSerializer(
            data=request.data,
            context={'request': request}
        )
        if serializer.is_valid():
            schematic = serializer.save(
                product=product,
                uploaded_by=request.user
            )

            # Auto-approve for trusted users
            if request.user.can_submit_without_review:
                schematic.is_approved = True
                schematic.save(update_fields=['is_approved'])

            return Response(
                SchematicSerializer(schematic, context={'request': request}).data,
                status=status.HTTP_201_CREATED
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class SchematicViewSet(viewsets.ModelViewSet):
    """
    ViewSet for schematic operations.

    Right to Repair: Schematics and service documentation help
    independent repair technicians fix devices.
    """

    queryset = Schematic.objects.select_related('product', 'uploaded_by')
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['schematic_type', 'source_type', 'is_approved', 'product']
    search_fields = ['title', 'description', 'product__manufacturer', 'product__model_number']
    ordering_fields = ['uploaded_at', 'download_count']
    ordering = ['-uploaded_at']

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return SchematicUploadSerializer
        return SchematicSerializer

    def get_queryset(self):
        queryset = super().get_queryset()

        # Non-staff users only see approved schematics
        if not self.request.user.is_staff:
            queryset = queryset.filter(is_approved=True)

        return queryset

    def get_permissions(self):
        if self.action in ['create']:
            return [permissions.IsAuthenticated(), IsVerifiedEmail()]
        elif self.action in ['update', 'partial_update', 'destroy']:
            return [permissions.IsAdminUser()]
        return [permissions.AllowAny()]

    @action(detail=True, methods=['get'])
    def download(self, request, pk=None):
        """
        Download a schematic file and increment download count.
        """
        schematic = self.get_object()
        schematic.increment_download_count()

        # Return file URL for client to download
        return Response({
            'download_url': request.build_absolute_uri(schematic.file.url),
            'filename': schematic.file.name.split('/')[-1],
            'file_type': schematic.file_type,
            'file_size': schematic.file_size,
        })

    @action(detail=False, methods=['get'])
    def recent(self, request):
        """Get recently uploaded schematics."""
        schematics = self.get_queryset().filter(is_approved=True)[:20]
        serializer = SchematicSerializer(
            schematics,
            many=True,
            context={'request': request}
        )
        return Response(serializer.data)


# Import models for queryset filtering
from django.db import models
