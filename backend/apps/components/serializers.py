"""
Component serializers for Junkbin.io API
"""
from rest_framework import serializers
from django.contrib.auth import get_user_model

from .models import Component, ProductComponent

User = get_user_model()


class CreatedBySerializer(serializers.ModelSerializer):
    """Minimal user serializer for nested representation."""

    class Meta:
        model = User
        fields = ['id', 'username', 'is_trusted']


class ComponentListSerializer(serializers.ModelSerializer):
    """Serializer for component list view."""

    component_type_display = serializers.CharField(
        source='get_component_type_display',
        read_only=True
    )
    primary_value = serializers.CharField(read_only=True)

    class Meta:
        model = Component
        fields = [
            'id', 'part_number', 'manufacturer', 'component_type',
            'component_type_display', 'package_type', 'typical_function',
            'primary_value', 'datasheet_url', 'usage_count', 'is_verified'
        ]


class ComponentDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for single component view."""

    component_type_display = serializers.CharField(
        source='get_component_type_display',
        read_only=True
    )
    created_by = CreatedBySerializer(read_only=True)
    cross_references = ComponentListSerializer(many=True, read_only=True)

    class Meta:
        model = Component
        fields = [
            'id', 'part_number', 'manufacturer', 'manufacturer_aliases',
            'component_type', 'component_type_display', 'package_type',
            'description', 'typical_function', 'specifications',
            'datasheet_url', 'octopart_url', 'alternative_part_numbers',
            'cross_references', 'usage_count', 'is_verified',
            'created_by', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'usage_count', 'is_verified',
            'created_by', 'created_at', 'updated_at'
        ]


class ComponentCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating/updating components."""

    class Meta:
        model = Component
        fields = [
            'id', 'part_number', 'manufacturer', 'manufacturer_aliases',
            'component_type', 'package_type', 'description',
            'typical_function', 'specifications', 'datasheet_url',
            'octopart_url', 'alternative_part_numbers'
        ]
        read_only_fields = ['id']

    def validate(self, attrs):
        # Check for duplicate
        queryset = Component.objects.filter(
            manufacturer__iexact=attrs['manufacturer'],
            part_number__iexact=attrs['part_number']
        )
        if self.instance:
            queryset = queryset.exclude(pk=self.instance.pk)

        if queryset.exists():
            raise serializers.ValidationError(
                'A component with this manufacturer and part number already exists.'
            )
        return attrs

    def create(self, validated_data):
        validated_data['created_by'] = self.context['request'].user
        return super().create(validated_data)


class ProductComponentSerializer(serializers.ModelSerializer):
    """Serializer for product-component relationships."""

    component = ComponentListSerializer(read_only=True)
    component_id = serializers.UUIDField(write_only=True)
    created_by = CreatedBySerializer(read_only=True)
    submission_level_display = serializers.CharField(
        source='get_submission_level_display',
        read_only=True
    )

    class Meta:
        model = ProductComponent
        fields = [
            'id', 'component', 'component_id', 'reference_designator',
            'quantity', 'location_description', 'board_name', 'notes',
            'image_reference', 'submission_level', 'submission_level_display',
            'is_verified', 'created_by', 'created_at'
        ]
        read_only_fields = ['id', 'is_verified', 'created_by', 'created_at']

    def validate_component_id(self, value):
        try:
            Component.objects.get(pk=value)
        except Component.DoesNotExist:
            raise serializers.ValidationError('Component not found.')
        return value

    def create(self, validated_data):
        component_id = validated_data.pop('component_id')
        validated_data['component'] = Component.objects.get(pk=component_id)
        validated_data['created_by'] = self.context['request'].user
        return super().create(validated_data)


class ProductComponentCreateSerializer(serializers.ModelSerializer):
    """Serializer for adding components to products."""

    component_id = serializers.UUIDField(required=False)

    # Allow creating new component inline
    new_component = ComponentCreateSerializer(required=False)

    class Meta:
        model = ProductComponent
        fields = [
            'component_id', 'new_component', 'reference_designator',
            'quantity', 'location_description', 'board_name', 'notes',
            'image_reference', 'submission_level'
        ]

    def validate(self, attrs):
        component_id = attrs.get('component_id')
        new_component = attrs.get('new_component')

        if not component_id and not new_component:
            raise serializers.ValidationError(
                'Either component_id or new_component must be provided.'
            )
        if component_id and new_component:
            raise serializers.ValidationError(
                'Provide either component_id or new_component, not both.'
            )

        return attrs

    def create(self, validated_data):
        new_component_data = validated_data.pop('new_component', None)

        if new_component_data:
            # Create the new component
            component_serializer = ComponentCreateSerializer(
                data=new_component_data,
                context=self.context
            )
            component_serializer.is_valid(raise_exception=True)
            component = component_serializer.save()
            validated_data['component'] = component
        else:
            component_id = validated_data.pop('component_id')
            validated_data['component'] = Component.objects.get(pk=component_id)

        validated_data['created_by'] = self.context['request'].user
        return super().create(validated_data)


class ComponentSearchSerializer(serializers.Serializer):
    """Serializer for component search parameters."""

    q = serializers.CharField(required=False, allow_blank=True, max_length=200)
    manufacturer = serializers.CharField(required=False, max_length=200)
    component_type = serializers.CharField(required=False, max_length=50)
    package_type = serializers.CharField(required=False, max_length=50)


class CrossReferenceResultSerializer(serializers.Serializer):
    """Serializer for cross-reference search results."""

    component = ComponentListSerializer()
    products = serializers.ListField(child=serializers.DictField())
    total_products = serializers.IntegerField()
