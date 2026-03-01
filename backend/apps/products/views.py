"""
Product views for Junkbin.io API
"""
import csv
import io
import json

from django.db import models, transaction
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
from apps.api.throttling import SubmissionRateThrottle
from apps.api.metrics import submission_counter


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
        if self.action in ['create', 'add_component', 'batch_add_components',
                           'upload_image', 'upload_schematic',
                           'comments', 'parse_bom', 'import_bom']:
            if self.request.method == 'POST':
                return [permissions.IsAuthenticated(), IsVerifiedEmail()]
            return [permissions.AllowAny()]
        elif self.action == 'comment_detail':
            return [permissions.IsAuthenticated()]
        elif self.action in ['update', 'partial_update', 'destroy']:
            return [permissions.IsAuthenticated(), IsOwnerOrReadOnly()]
        elif self.action in ['approve', 'reject', 'pending_counts']:
            return [IsModeratorOrAdmin()]
        return [permissions.AllowAny()]

    def get_throttles(self):
        if self.action in ['create', 'add_component', 'batch_add_components',
                           'comments', 'upload_image', 'upload_schematic']:
            if self.request.method == 'POST':
                return [SubmissionRateThrottle()]
        return super().get_throttles()

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
        submission_counter.labels(content_type='product').inc()

        # Auto-approve for trusted users
        if self.request.user.can_submit_without_review:
            product.is_approved = True
            product.save(update_fields=['is_approved'])
            self.request.user.increment_contribution()

        # Webhook notification
        from apps.webhooks.tasks import dispatch_webhook_event
        dispatch_webhook_event.delay('product.created', {
            'name': str(product),
            'manufacturer': product.manufacturer,
            'model_number': product.model_number,
            'slug': str(product.pk),
            'created_by': self.request.user.username,
        })

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

        from django.db.models import Prefetch
        from apps.components.models import ProductComponent, ComponentVote
        from apps.components.serializers import ProductComponentSerializer

        components = ProductComponent.objects.filter(
            product=product
        ).select_related('component', 'created_by')

        # Prefetch current user's vote for efficient serialization
        if request.user.is_authenticated:
            components = components.prefetch_related(
                Prefetch(
                    'votes',
                    queryset=ComponentVote.objects.filter(user=request.user),
                    to_attr='current_user_votes'
                )
            )
        else:
            components = components.prefetch_related(
                Prefetch(
                    'votes',
                    queryset=ComponentVote.objects.none(),
                    to_attr='current_user_votes'
                )
            )

        serializer = ProductComponentSerializer(
            components, many=True, context={'request': request}
        )
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

    @action(detail=True, methods=['post'])
    def batch_add_components(self, request, pk=None):
        """Add multiple components to this product in one request."""
        from django.conf import settings as django_settings
        from apps.components.models import Component, ProductComponent
        from .bom_utils import classify_component_type, extract_package

        product = self.get_object()
        valid_types = {ct[0] for ct in django_settings.COMPONENT_TYPES}
        items = request.data.get('components', [])

        if not isinstance(items, list) or not items:
            return Response({'detail': 'A non-empty "components" array is required.'},
                            status=status.HTTP_400_BAD_REQUEST)
        if len(items) > 50:
            return Response({'detail': 'Maximum 50 components per batch.'},
                            status=status.HTTP_400_BAD_REQUEST)

        created = 0
        reused = 0
        linked = 0
        skipped = 0
        row_errors = []

        with transaction.atomic():
            for idx, item in enumerate(items, start=1):
                part_number = (item.get('part_number') or '').strip()
                manufacturer = (item.get('manufacturer') or '').strip()

                if not part_number or not manufacturer:
                    row_errors.append({'row': idx, 'errors': ['Part Number and Manufacturer are required.']})
                    skipped += 1
                    continue

                comp_type = (item.get('component_type') or '').strip().lower()
                if comp_type not in valid_types:
                    desc = item.get('description', '')
                    comp_type = classify_component_type(desc)

                pkg = (item.get('package_type') or '').strip()
                if not pkg and item.get('description'):
                    pkg = extract_package(item['description'])

                qty = item.get('quantity', 1)
                try:
                    qty = max(1, int(qty))
                except (ValueError, TypeError):
                    qty = 1

                component, was_created = Component.objects.get_or_create(
                    manufacturer=manufacturer,
                    part_number=part_number,
                    defaults={
                        'component_type': comp_type,
                        'package_type': pkg,
                        'description': (item.get('description') or '').strip(),
                        'created_by': request.user,
                    }
                )
                if was_created:
                    created += 1
                else:
                    reused += 1

                _, pc_created = ProductComponent.objects.get_or_create(
                    product=product,
                    component=component,
                    defaults={
                        'reference_designator': (item.get('reference_designator') or '').strip(),
                        'quantity': qty,
                        'notes': (item.get('notes') or '').strip(),
                        'submission_level': 'advanced',
                        'created_by': request.user,
                    }
                )
                if pc_created:
                    linked += 1

        return Response({
            'created': created,
            'reused': reused,
            'linked': linked,
            'skipped': skipped,
            'errors': row_errors,
            'total': created + reused + skipped,
        }, status=status.HTTP_201_CREATED if linked > 0 else status.HTTP_200_OK)

    @action(
        detail=True,
        methods=['post'],
        parser_classes=[MultiPartParser, FormParser]
    )
    def parse_bom(self, request, pk=None):
        """Parse a CSV BOM and return headers, preview rows, and auto-detected column mapping."""
        from .bom_utils import detect_column_mapping, BOM_FIELDS

        file = request.FILES.get('file')
        if not file:
            return Response({'detail': 'No file provided.'}, status=status.HTTP_400_BAD_REQUEST)

        if file.size > 5 * 1024 * 1024:
            return Response({'detail': 'File too large (max 5MB).'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            content = file.read().decode('utf-8-sig')
        except UnicodeDecodeError:
            try:
                file.seek(0)
                content = file.read().decode('latin-1')
            except Exception:
                return Response({'detail': 'Could not decode file. Please use UTF-8 or Latin-1 encoding.'},
                                status=status.HTTP_400_BAD_REQUEST)

        reader = csv.DictReader(io.StringIO(content))
        headers = reader.fieldnames or []
        if not headers:
            return Response({'detail': 'CSV has no headers.'}, status=status.HTTP_400_BAD_REQUEST)

        # Collect preview rows (first 5)
        preview_rows = []
        for i, row in enumerate(reader):
            if i >= 5:
                break
            preview_rows.append(dict(row))

        # Count total rows
        total_rows = len(preview_rows)
        for _ in reader:
            total_rows += 1

        mapping = detect_column_mapping(headers)

        return Response({
            'headers': headers,
            'preview_rows': preview_rows,
            'detected_mapping': mapping,
            'available_fields': BOM_FIELDS,
            'total_rows': total_rows,
        })

    @action(
        detail=True,
        methods=['post'],
        parser_classes=[MultiPartParser, FormParser]
    )
    def import_bom(self, request, pk=None):
        """Import components from a CSV BOM file."""
        from apps.components.models import Component, ProductComponent
        from .bom_utils import (
            validate_row, classify_component_type, extract_package,
            extract_value_from_text,
        )

        product = self.get_object()
        file = request.FILES.get('file')
        if not file:
            return Response({'detail': 'No file provided.'}, status=status.HTTP_400_BAD_REQUEST)

        column_mapping_raw = request.data.get('column_mapping', '{}')
        if isinstance(column_mapping_raw, str):
            try:
                column_mapping = json.loads(column_mapping_raw)
            except json.JSONDecodeError:
                return Response({'detail': 'Invalid column_mapping JSON.'},
                                status=status.HTTP_400_BAD_REQUEST)
        else:
            column_mapping = column_mapping_raw

        dry_run = str(request.data.get('dry_run', 'false')).lower() in ('true', '1', 'yes')

        try:
            content = file.read().decode('utf-8-sig')
        except UnicodeDecodeError:
            try:
                file.seek(0)
                content = file.read().decode('latin-1')
            except Exception:
                return Response({'detail': 'Could not decode file.'},
                                status=status.HTTP_400_BAD_REQUEST)

        reader = csv.DictReader(io.StringIO(content))

        created = 0
        reused = 0
        linked = 0
        skipped = 0
        row_errors = []

        sid = transaction.savepoint()
        try:
            for row_num, row in enumerate(reader, start=2):  # row 1 = header
                cleaned, errors = validate_row(row, column_mapping)

                if errors:
                    row_errors.append({'row': row_num, 'errors': errors, 'data': dict(row)})
                    skipped += 1
                    continue

                # Auto-classify component type if not provided
                comp_type = cleaned.get('component_type')
                if not comp_type:
                    desc = cleaned.get('description', '')
                    comp_type = classify_component_type(desc)

                # Auto-detect package from description if not provided
                pkg = cleaned.get('package_type', '')
                if not pkg and cleaned.get('description'):
                    pkg = extract_package(cleaned['description'])

                # Extract specifications from value column
                specs = {}
                if cleaned.get('value'):
                    specs = extract_value_from_text(cleaned['value'], comp_type)

                # Get or create the Component
                component, was_created = Component.objects.get_or_create(
                    manufacturer=cleaned['manufacturer'].strip(),
                    part_number=cleaned['part_number'].strip(),
                    defaults={
                        'component_type': comp_type,
                        'package_type': pkg,
                        'description': cleaned.get('description', ''),
                        'specifications': specs,
                        'created_by': request.user,
                    }
                )

                if was_created:
                    created += 1
                else:
                    reused += 1

                # Create the ProductComponent link (skip duplicates)
                _, pc_created = ProductComponent.objects.get_or_create(
                    product=product,
                    component=component,
                    defaults={
                        'reference_designator': cleaned.get('reference_designator', ''),
                        'quantity': cleaned.get('quantity', 1),
                        'location_description': cleaned.get('location_description', ''),
                        'notes': cleaned.get('notes', ''),
                        'submission_level': 'advanced',
                        'created_by': request.user,
                    }
                )
                if pc_created:
                    linked += 1

            if dry_run:
                transaction.savepoint_rollback(sid)
            else:
                transaction.savepoint_commit(sid)
        except Exception as e:
            transaction.savepoint_rollback(sid)
            return Response({'detail': f'Import failed: {str(e)}'},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response({
            'created': created,
            'reused': reused,
            'linked': linked,
            'skipped': skipped,
            'errors': row_errors[:50],  # Cap error details
            'total': created + reused + skipped,
            'dry_run': dry_run,
        })

    @action(
        detail=True,
        methods=['post'],
        parser_classes=[MultiPartParser, FormParser]
    )
    def upload_image(self, request, pk=None):
        """Upload an image for this product."""
        product = self.get_object()

        serializer = ProductImageUploadSerializer(data=request.data)
        if serializer.is_valid():
            image = serializer.save(
                product=product,
                uploaded_by=request.user
            )
            submission_counter.labels(content_type='image').inc()

            # Auto-approve for trusted users
            if request.user.can_submit_without_review:
                image.is_approved = True
                image.save(update_fields=['is_approved'])
                request.user.increment_contribution()

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

        # Non-staff users only see approved images (plus their own)
        if not request.user.is_staff:
            if request.user.is_authenticated:
                images = images.filter(
                    models.Q(is_approved=True) |
                    models.Q(uploaded_by=request.user)
                )
            else:
                images = images.filter(is_approved=True)

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
            submission_counter.labels(content_type='schematic').inc()

            # Auto-approve for trusted users
            if request.user.can_submit_without_review:
                schematic.is_approved = True
                schematic.save(update_fields=['is_approved'])
                request.user.increment_contribution()


            # Webhook notification
            from apps.webhooks.tasks import dispatch_webhook_event
            dispatch_webhook_event.delay('schematic.uploaded', {
                'title': schematic.title,
                'product_name': str(product),
                'product_slug': str(product.pk),
                'schematic_type': schematic.get_schematic_type_display(),
                'uploaded_by': request.user.username,
            })

            return Response(
                SchematicSerializer(schematic, context={'request': request}).data,
                status=status.HTTP_201_CREATED
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        """Approve a pending product (staff/moderator only)."""
        product = self.get_object()
        if product.is_approved:
            return Response({'detail': 'Product is already approved.'}, status=status.HTTP_400_BAD_REQUEST)
        product.is_approved = True
        product.save(update_fields=['is_approved'])

        if product.created_by:
            product.created_by.increment_contribution()

        return Response({'detail': 'Product approved.'})

    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        """Reject and delete a pending product (staff/moderator only)."""
        product = self.get_object()
        if product.is_approved:
            return Response({'detail': 'Cannot reject an already-approved product.'}, status=status.HTTP_400_BAD_REQUEST)
        product.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=['get'])
    def pending_counts(self, request):
        """Get counts of pending (unapproved) content for moderation dashboard."""
        from apps.recipes.models import Recipe
        from apps.components.models import ComponentImage, ComponentDatasheet

        return Response({
            'products': Product.objects.filter(is_approved=False).count(),
            'schematics': Schematic.objects.filter(is_approved=False).count(),
            'recipes': Recipe.objects.filter(is_approved=False).count(),
            'images': ProductImage.objects.filter(is_approved=False).count(),
            'component_images': ComponentImage.objects.filter(is_approved=False).count(),
            'datasheets': ComponentDatasheet.objects.filter(is_approved=False).count(),
        })


class SchematicViewSet(viewsets.ModelViewSet):
    """
    ViewSet for schematic operations.

    Right to Repair: Schematics and service documentation help
    independent repair technicians fix devices.
    """

    queryset = Schematic.objects.select_related('product', 'uploaded_by')
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['schematic_type', 'source_type', 'is_approved', 'product', 'uploaded_by']
    search_fields = ['title', 'description', 'product__manufacturer', 'product__model_number']
    ordering_fields = ['uploaded_at', 'download_count']
    ordering = ['-uploaded_at']

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return SchematicUploadSerializer
        return SchematicSerializer

    def get_queryset(self):
        queryset = super().get_queryset()

        # Non-staff users only see approved schematics (plus their own)
        if not self.request.user.is_staff:
            if self.request.user.is_authenticated:
                queryset = queryset.filter(
                    models.Q(is_approved=True) |
                    models.Q(uploaded_by=self.request.user)
                )
            else:
                queryset = queryset.filter(is_approved=True)

        return queryset

    def get_permissions(self):
        if self.action in ['create']:
            return [permissions.IsAuthenticated(), IsVerifiedEmail()]
        elif self.action in ['update', 'partial_update', 'destroy']:
            return [permissions.IsAdminUser()]
        elif self.action in ['approve', 'reject']:
            return [IsModeratorOrAdmin()]
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

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        """Approve a pending schematic (staff/moderator only)."""
        schematic = self.get_object()
        if schematic.is_approved:
            return Response({'detail': 'Schematic is already approved.'}, status=status.HTTP_400_BAD_REQUEST)
        schematic.is_approved = True
        schematic.save(update_fields=['is_approved'])

        if schematic.uploaded_by:
            schematic.uploaded_by.increment_contribution()

        return Response({'detail': 'Schematic approved.'})

    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        """Reject and delete a pending schematic (staff/moderator only)."""
        schematic = self.get_object()
        if schematic.is_approved:
            return Response({'detail': 'Cannot reject an already-approved schematic.'}, status=status.HTTP_400_BAD_REQUEST)
        schematic.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class ProductImageViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for product image moderation.
    Staff-only list with approve/reject actions.
    """

    queryset = ProductImage.objects.select_related('product', 'uploaded_by')
    serializer_class = ProductImageSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['is_approved', 'product', 'uploaded_by']
    ordering_fields = ['uploaded_at']
    ordering = ['-uploaded_at']

    def get_permissions(self):
        return [IsModeratorOrAdmin()]

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        """Approve a pending image (staff/moderator only)."""
        image = self.get_object()
        if image.is_approved:
            return Response({'detail': 'Image is already approved.'}, status=status.HTTP_400_BAD_REQUEST)
        image.is_approved = True
        image.save(update_fields=['is_approved'])

        if image.uploaded_by:
            image.uploaded_by.increment_contribution()

        return Response({'detail': 'Image approved.'})

    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        """Reject and delete a pending image (staff/moderator only)."""
        image = self.get_object()
        if image.is_approved:
            return Response({'detail': 'Cannot reject an already-approved image.'}, status=status.HTTP_400_BAD_REQUEST)
        image.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
