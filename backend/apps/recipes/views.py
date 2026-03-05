"""
Recipe views for Junkbin.io API
"""
from django.db import models
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.response import Response
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter

from .models import Recipe
from .serializers import (
    RecipeListSerializer,
    RecipeDetailSerializer,
    RecipeCreateSerializer,
    MatchedComponentSerializer,
)
from .filters import RecipeFilter
from .matching import (
    get_user_component_ids,
    calculate_recipe_match,
    get_buildable_recipes,
    get_missing_part_availability,
)
from apps.api.permissions import IsOwnerOrReadOnly, IsModeratorOrAdmin, IsVerifiedEmail
from apps.api.throttling import SubmissionRateThrottle
from apps.api.metrics import submission_counter


class RecipeViewSet(viewsets.ModelViewSet):
    """
    ViewSet for recipe CRUD and matching operations.
    """

    queryset = Recipe.objects.select_related('created_by')
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = RecipeFilter
    search_fields = ['name', 'description']
    ordering_fields = ['created_at', 'view_count', 'component_count', 'name']
    ordering = ['-created_at']
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get_queryset(self):
        queryset = super().get_queryset()

        user = self.request.user
        if not user.is_staff and not getattr(user, 'is_moderator', False):
            if user.is_authenticated:
                queryset = queryset.filter(
                    models.Q(is_approved=True) |
                    models.Q(created_by=user)
                )
            else:
                queryset = queryset.filter(is_approved=True)

        return queryset

    def get_serializer_class(self):
        if self.action == 'list':
            return RecipeListSerializer
        elif self.action in ['create', 'update', 'partial_update']:
            return RecipeCreateSerializer
        return RecipeDetailSerializer

    def get_permissions(self):
        if self.action in ['create']:
            return [permissions.IsAuthenticated(), IsVerifiedEmail()]
        elif self.action in ['update', 'partial_update', 'destroy']:
            return [permissions.IsAuthenticated(), IsOwnerOrReadOnly()]
        elif self.action in ['buildable', 'match']:
            return [permissions.IsAuthenticated()]
        elif self.action in ['approve', 'reject']:
            return [IsModeratorOrAdmin()]
        return [permissions.AllowAny()]

    def get_throttles(self):
        if self.action == 'create' and self.request.method == 'POST':
            return [SubmissionRateThrottle()]
        return super().get_throttles()

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        recipes = page if page is not None else queryset

        # Inject match percentages for authenticated users
        if request.user.is_authenticated:
            user_ids = get_user_component_ids(request.user)
            prefetched = Recipe.objects.filter(
                id__in=[r.id for r in recipes]
            ).prefetch_related('recipe_components__component')
            recipe_map = {r.id: r for r in prefetched}

            for recipe in recipes:
                pf_recipe = recipe_map.get(recipe.id)
                if pf_recipe:
                    match = calculate_recipe_match(pf_recipe, user_ids)
                    recipe._match_percentage = match['match_percentage']
                else:
                    recipe._match_percentage = None

        serializer = RecipeListSerializer(
            recipes, many=True, context={'request': request}
        )
        if page is not None:
            return self.get_paginated_response(serializer.data)
        return Response(serializer.data)

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.increment_view_count()

        # Inject match data for authenticated users
        if request.user.is_authenticated:
            user_ids = get_user_component_ids(request.user)
            prefetched = Recipe.objects.filter(
                pk=instance.pk
            ).prefetch_related('recipe_components__component').first()
            match = calculate_recipe_match(prefetched, user_ids)
            instance._match_percentage = match['match_percentage']
            # Pre-fetch recipe components for serializer
            instance = prefetched
            instance._match_percentage = match['match_percentage']

        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    def perform_create(self, serializer):
        recipe = serializer.save()
        submission_counter.labels(content_type='recipe').inc()
        if self.request.user.can_submit_without_review:
            recipe.is_approved = True
            recipe.save(update_fields=['is_approved'])
            self.request.user.increment_contribution()

        # Webhook notification
        from apps.webhooks.tasks import dispatch_webhook_event
        dispatch_webhook_event.delay('recipe.created', {
            'name': recipe.name,
            'slug': recipe.slug,
            'difficulty': recipe.get_difficulty_display(),
            'category': recipe.get_category_display(),
            'created_by': self.request.user.username,
        })

    def perform_update(self, serializer):
        instance = serializer.save()
        if not self.request.user.is_staff and not self.request.user.is_moderator:
            if instance.is_approved:
                instance.is_approved = False
                instance.save(update_fields=['is_approved'])

    @action(detail=False, methods=['get'])
    def buildable(self, request):
        """
        "What Can I Build?" — recipes sorted by match percentage.
        """
        category = request.query_params.get('category', '')
        difficulty = request.query_params.get('difficulty', '')
        min_match = float(request.query_params.get('min_match', 0))

        queryset = Recipe.objects.filter(is_approved=True)
        if category:
            queryset = queryset.filter(category=category)
        if difficulty:
            queryset = queryset.filter(difficulty=difficulty)

        results = get_buildable_recipes(
            request.user,
            queryset=queryset,
            min_match_percentage=min_match,
        )

        # Manual pagination
        page_size = 20
        page_num = int(request.query_params.get('page', 1))
        start = (page_num - 1) * page_size
        end = start + page_size
        page_results = results[start:end]

        # Attach match percentage to recipe objects for serializer
        recipes = []
        for recipe, match_data in page_results:
            recipe._match_percentage = match_data['match_percentage']
            recipes.append(recipe)

        serializer = RecipeListSerializer(
            recipes, many=True, context={'request': request}
        )

        return Response({
            'count': len(results),
            'next': f'?page={page_num + 1}' if end < len(results) else None,
            'previous': f'?page={page_num - 1}' if page_num > 1 else None,
            'results': serializer.data,
        })

    @action(detail=True, methods=['get'])
    def match(self, request, pk=None):
        """
        Detailed match for a single recipe with availability info.
        """
        recipe = Recipe.objects.filter(
            pk=pk
        ).prefetch_related('recipe_components__component').first()

        if not recipe:
            return Response(
                {'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND
            )

        user_ids = get_user_component_ids(request.user)
        match_data = calculate_recipe_match(recipe, user_ids)

        # Get availability for missing components
        missing_ids = [
            rc.component_id for rc in match_data['missing_components']
        ] + [
            rc.component_id for rc in match_data['optional_missing']
        ]
        availability = get_missing_part_availability(missing_ids, request.user)

        # Build response items
        items = []
        for rc in recipe.recipe_components.select_related('component').all():
            has = rc.component_id in user_ids
            avail = availability.get(str(rc.component_id), [])
            rc.user_has = has
            rc.available_from = avail
            items.append(rc)

        serializer = MatchedComponentSerializer(items, many=True)

        return Response({
            'recipe_id': str(recipe.id),
            'recipe_name': recipe.name,
            'match_percentage': match_data['match_percentage'],
            'total_required': match_data['total_required'],
            'matched_count': match_data['matched_count'],
            'components': serializer.data,
        })

    @method_decorator(cache_page(60 * 60))
    @action(detail=False, methods=['get'])
    def categories(self, request):
        """Get category choices with approved recipe counts."""
        from django.db.models import Count

        counts = dict(
            Recipe.objects.filter(is_approved=True)
            .values_list('category')
            .annotate(count=Count('id'))
            .values_list('category', 'count')
        )

        result = [
            {
                'value': choice[0],
                'label': choice[1],
                'count': counts.get(choice[0], 0),
            }
            for choice in Recipe.Category.choices
        ]

        return Response(result)

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        """Approve a pending recipe (staff/moderator only)."""
        recipe = self.get_object()
        if recipe.is_approved:
            return Response({'detail': 'Recipe is already approved.'}, status=status.HTTP_400_BAD_REQUEST)
        recipe.is_approved = True
        recipe.save(update_fields=['is_approved'])

        if recipe.created_by:
            recipe.created_by.increment_contribution()

        return Response({'detail': 'Recipe approved.'})

    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        """Reject and delete a pending recipe (staff/moderator only)."""
        recipe = self.get_object()
        if recipe.is_approved:
            return Response({'detail': 'Cannot reject an already-approved recipe.'}, status=status.HTTP_400_BAD_REQUEST)
        recipe.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
