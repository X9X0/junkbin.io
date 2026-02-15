"""
Junkbin views for Junkbin.io API
"""
from django.contrib.contenttypes.models import ContentType
from django.db import models
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import JunkbinItem
from .serializers import (
    JunkbinItemListSerializer,
    JunkbinItemDetailSerializer,
    JunkbinItemCreateSerializer,
    JunkbinItemUpdateSerializer,
)


class JunkbinItemViewSet(viewsets.ModelViewSet):
    """
    ViewSet for junkbin item CRUD.

    - Authenticated users can manage their own items.
    - Anyone can browse public "have" items from other users.
    """

    queryset = JunkbinItem.objects.select_related('user', 'content_type')
    ordering = ['-created_at']

    def get_permissions(self):
        if self.action in ('list', 'retrieve', 'user_summary'):
            return [permissions.AllowAny()]
        return [permissions.IsAuthenticated()]

    def get_serializer_class(self):
        if self.action == 'create':
            return JunkbinItemCreateSerializer
        if self.action in ('update', 'partial_update'):
            return JunkbinItemUpdateSerializer
        if self.action == 'retrieve':
            return JunkbinItemDetailSerializer
        return JunkbinItemListSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        params = self.request.query_params

        # Filter by specific user
        filter_user = params.get('user')
        if filter_user:
            qs = qs.filter(user_id=filter_user)
            # Non-owner sees only public "have" items
            if not user.is_authenticated or str(user.id) != filter_user:
                qs = qs.filter(visibility='public', item_type='have')
        elif self.action == 'list':
            # Default list: only public "have" items (browse mode)
            if not user.is_authenticated:
                qs = qs.filter(visibility='public', item_type='have')
            else:
                # Authenticated user: show public "have" from others + all own items
                qs = qs.filter(
                    models.Q(visibility='public', item_type='have') |
                    models.Q(user=user)
                )

        # Additional filters
        item_type = params.get('item_type')
        if item_type:
            qs = qs.filter(item_type=item_type)

        content_type = params.get('content_type')
        if content_type:
            model_map = {
                'product': ('products', 'product'),
                'component': ('components', 'component'),
            }
            if content_type in model_map:
                app_label, model = model_map[content_type]
                try:
                    ct = ContentType.objects.get(app_label=app_label, model=model)
                    qs = qs.filter(content_type=ct)
                except ContentType.DoesNotExist:
                    pass

        filter_status = params.get('status')
        if filter_status:
            qs = qs.filter(status=filter_status)

        filter_condition = params.get('condition')
        if filter_condition:
            qs = qs.filter(condition=filter_condition)

        return qs.distinct()

    def perform_create(self, serializer):
        instance = serializer.save()
        # Trigger want-list matching when a public+available item is added
        if (
            instance.item_type == 'have'
            and instance.status == 'available'
            and instance.visibility == 'public'
        ):
            from .tasks import match_want_lists
            match_want_lists.delay(str(instance.id))
        # Check for new badges
        from apps.users.badges import check_and_award_badges
        check_and_award_badges(self.request.user)

    def perform_update(self, serializer):
        instance = serializer.save()
        # Trigger want-list matching when item becomes publicly available
        if (
            instance.item_type == 'have'
            and instance.status == 'available'
            and instance.visibility == 'public'
        ):
            from .tasks import match_want_lists
            match_want_lists.delay(str(instance.id))

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.user != request.user and not request.user.is_staff:
            return Response(status=status.HTTP_403_FORBIDDEN)
        return super().destroy(request, *args, **kwargs)

    @action(detail=False, methods=['get'])
    def my_items(self, request):
        """Return the current user's junkbin items (all visibility, both types)."""
        qs = JunkbinItem.objects.select_related(
            'user', 'content_type'
        ).filter(user=request.user)

        item_type = request.query_params.get('item_type')
        if item_type:
            qs = qs.filter(item_type=item_type)

        content_type = request.query_params.get('content_type')
        if content_type:
            model_map = {
                'product': ('products', 'product'),
                'component': ('components', 'component'),
            }
            if content_type in model_map:
                app_label, model = model_map[content_type]
                try:
                    ct = ContentType.objects.get(app_label=app_label, model=model)
                    qs = qs.filter(content_type=ct)
                except ContentType.DoesNotExist:
                    pass

        page = self.paginate_queryset(qs)
        if page is not None:
            serializer = JunkbinItemListSerializer(page, many=True, context={'request': request})
            return self.get_paginated_response(serializer.data)

        serializer = JunkbinItemListSerializer(qs, many=True, context={'request': request})
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def my_summary(self, request):
        """Return summary counts for the current user's junkbin."""
        qs = JunkbinItem.objects.filter(user=request.user)
        return Response({
            'have_count': qs.filter(item_type='have').count(),
            'want_count': qs.filter(item_type='want').count(),
            'available_count': qs.filter(
                item_type='have', status='available'
            ).count(),
        })

    @action(detail=False, methods=['get'])
    def user_summary(self, request):
        """Return public summary counts for a given user."""
        user_id = request.query_params.get('user')
        if not user_id:
            return Response(
                {'detail': 'user parameter required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        qs = JunkbinItem.objects.filter(
            user_id=user_id, visibility='public', item_type='have'
        )
        return Response({
            'have_count': qs.count(),
            'available_count': qs.filter(status='available').count(),
        })

    @action(detail=False, methods=['get'])
    def check(self, request):
        """Check whether the current user has a specific item in their junkbin."""
        content_type_str = request.query_params.get('content_type')
        object_id = request.query_params.get('object_id')

        if not content_type_str or not object_id:
            return Response(
                {'detail': 'content_type and object_id parameters required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        model_map = {
            'product': ('products', 'product'),
            'component': ('components', 'component'),
        }
        if content_type_str not in model_map:
            return Response(
                {'detail': 'content_type must be "product" or "component"'},
                status=status.HTTP_400_BAD_REQUEST
            )

        app_label, model = model_map[content_type_str]
        try:
            ct = ContentType.objects.get(app_label=app_label, model=model)
        except ContentType.DoesNotExist:
            return Response({'items': []})

        items = JunkbinItem.objects.filter(
            user=request.user, content_type=ct, object_id=object_id
        )
        serializer = JunkbinItemListSerializer(
            items, many=True, context={'request': request}
        )
        return Response({'items': serializer.data})
