"""
Recipe serializers for Junkbin.io API
"""
from rest_framework import serializers
from django.contrib.auth import get_user_model

from .models import Recipe, RecipeComponent
from apps.components.models import Component

User = get_user_model()


class CreatedBySerializer(serializers.ModelSerializer):
    """Minimal user serializer for nested representation."""

    class Meta:
        model = User
        fields = ['id', 'username', 'is_trusted']


class RecipeComponentSerializer(serializers.ModelSerializer):
    """Read serializer for recipe BOM items."""

    component_id = serializers.UUIDField(source='component.id')
    part_number = serializers.CharField(source='component.part_number')
    manufacturer = serializers.CharField(source='component.manufacturer')
    component_type = serializers.CharField(source='component.component_type')
    component_type_display = serializers.CharField(
        source='component.get_component_type_display'
    )
    primary_value = serializers.CharField(source='component.primary_value')

    class Meta:
        model = RecipeComponent
        fields = [
            'id', 'component_id', 'part_number', 'manufacturer',
            'component_type', 'component_type_display', 'primary_value',
            'quantity', 'notes', 'is_optional',
        ]


class RecipeComponentCreateSerializer(serializers.Serializer):
    """Write serializer for recipe BOM items."""

    component_id = serializers.UUIDField()
    quantity = serializers.IntegerField(default=1, min_value=1, max_value=9999)
    notes = serializers.CharField(max_length=500, required=False, default='')
    is_optional = serializers.BooleanField(default=False)


class RecipeListSerializer(serializers.ModelSerializer):
    """Serializer for recipe list view."""

    created_by = CreatedBySerializer(read_only=True)
    difficulty_display = serializers.CharField(
        source='get_difficulty_display', read_only=True
    )
    category_display = serializers.CharField(
        source='get_category_display', read_only=True
    )
    match_percentage = serializers.SerializerMethodField()

    class Meta:
        model = Recipe
        fields = [
            'id', 'slug', 'name', 'description', 'difficulty',
            'difficulty_display', 'category', 'category_display',
            'external_url', 'estimated_time', 'image',
            'component_count', 'view_count', 'is_approved',
            'is_featured', 'created_by', 'created_at',
            'match_percentage',
        ]

    def get_match_percentage(self, obj):
        return getattr(obj, '_match_percentage', None)


class RecipeDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for single recipe view."""

    created_by = CreatedBySerializer(read_only=True)
    difficulty_display = serializers.CharField(
        source='get_difficulty_display', read_only=True
    )
    category_display = serializers.CharField(
        source='get_category_display', read_only=True
    )
    bom = RecipeComponentSerializer(
        source='recipe_components', many=True, read_only=True
    )
    match_percentage = serializers.SerializerMethodField()

    class Meta:
        model = Recipe
        fields = [
            'id', 'slug', 'name', 'description', 'difficulty',
            'difficulty_display', 'category', 'category_display',
            'external_url', 'estimated_time', 'image',
            'component_count', 'view_count', 'build_count',
            'is_approved', 'is_featured',
            'created_by', 'created_at', 'updated_at',
            'bom', 'match_percentage',
        ]
        read_only_fields = [
            'id', 'slug', 'component_count', 'view_count',
            'build_count', 'created_by', 'created_at', 'updated_at',
            'is_approved', 'is_featured',
        ]

    def get_match_percentage(self, obj):
        return getattr(obj, '_match_percentage', None)


class RecipeCreateSerializer(serializers.ModelSerializer):
    """Write serializer for creating/updating recipes."""

    bom = RecipeComponentCreateSerializer(many=True, write_only=True)

    class Meta:
        model = Recipe
        fields = [
            'id', 'slug', 'name', 'description', 'difficulty',
            'category', 'external_url', 'estimated_time', 'image',
            'bom',
        ]
        read_only_fields = ['id', 'slug']

    def to_internal_value(self, data):
        # Handle bom as JSON string from FormData multipart submissions
        import json
        if hasattr(data, 'getlist'):
            # QueryDict from multipart
            bom_raw = data.get('bom')
            if isinstance(bom_raw, str):
                try:
                    data = data.copy()
                    data.setlist('bom', [])
                    result = super().to_internal_value(data)
                    bom_serializer = RecipeComponentCreateSerializer(
                        data=json.loads(bom_raw), many=True
                    )
                    bom_serializer.is_valid(raise_exception=True)
                    result['bom'] = bom_serializer.validated_data
                    return result
                except json.JSONDecodeError:
                    raise serializers.ValidationError(
                        {'bom': ['Invalid JSON.']}
                    )
        return super().to_internal_value(data)

    def validate_name(self, value):
        stripped = value.strip()
        if not stripped:
            raise serializers.ValidationError('Name cannot be empty.')
        from utils.content_filter import check_content
        is_clean, _ = check_content(stripped)
        if not is_clean:
            raise serializers.ValidationError(
                'Name contains prohibited language. '
                'Please review our community guidelines.'
            )
        return stripped

    def validate_description(self, value):
        stripped = value.strip()
        if not stripped:
            raise serializers.ValidationError('Description cannot be empty.')
        from utils.content_filter import check_content
        is_clean, _ = check_content(stripped)
        if not is_clean:
            raise serializers.ValidationError(
                'Description contains prohibited language. '
                'Please review our community guidelines.'
            )
        return stripped

    def validate_bom(self, value):
        if not value:
            raise serializers.ValidationError('BOM must have at least 1 item.')
        if len(value) > 100:
            raise serializers.ValidationError('BOM cannot exceed 100 items.')

        component_ids = [item['component_id'] for item in value]
        if len(component_ids) != len(set(component_ids)):
            raise serializers.ValidationError('BOM contains duplicate components.')

        existing = set(
            Component.objects.filter(
                id__in=component_ids
            ).values_list('id', flat=True)
        )
        missing = [str(cid) for cid in component_ids if cid not in existing]
        if missing:
            raise serializers.ValidationError(
                f'Components not found: {", ".join(missing)}'
            )

        return value

    def create(self, validated_data):
        bom_data = validated_data.pop('bom')
        validated_data['created_by'] = self.context['request'].user
        recipe = Recipe.objects.create(**validated_data)

        RecipeComponent.objects.bulk_create([
            RecipeComponent(
                recipe=recipe,
                component_id=item['component_id'],
                quantity=item.get('quantity', 1),
                notes=item.get('notes', ''),
                is_optional=item.get('is_optional', False),
            )
            for item in bom_data
        ])

        # Update component count after bulk create
        recipe.update_component_count()
        return recipe

    def update(self, instance, validated_data):
        bom_data = validated_data.pop('bom', None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if bom_data is not None:
            # Replace entire BOM
            instance.recipe_components.all().delete()
            RecipeComponent.objects.bulk_create([
                RecipeComponent(
                    recipe=instance,
                    component_id=item['component_id'],
                    quantity=item.get('quantity', 1),
                    notes=item.get('notes', ''),
                    is_optional=item.get('is_optional', False),
                )
                for item in bom_data
            ])
            instance.update_component_count()

        return instance


class MatchedComponentSerializer(serializers.ModelSerializer):
    """Serializer for match response — BOM items with match indicators."""

    component_id = serializers.UUIDField(source='component.id')
    part_number = serializers.CharField(source='component.part_number')
    manufacturer = serializers.CharField(source='component.manufacturer')
    component_type = serializers.CharField(source='component.component_type')
    component_type_display = serializers.CharField(
        source='component.get_component_type_display'
    )
    primary_value = serializers.CharField(source='component.primary_value')
    user_has = serializers.BooleanField()
    available_from = serializers.ListField(child=serializers.DictField())

    class Meta:
        model = RecipeComponent
        fields = [
            'id', 'component_id', 'part_number', 'manufacturer',
            'component_type', 'component_type_display', 'primary_value',
            'quantity', 'notes', 'is_optional',
            'user_has', 'available_from',
        ]
