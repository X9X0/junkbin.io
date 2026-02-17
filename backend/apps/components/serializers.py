"""
Component serializers for Junkbin.io API
"""
from rest_framework import serializers
from django.contrib.auth import get_user_model

from .models import Component, ComponentImage, ComponentTypeImage, ProductComponent, ComponentVote
from utils.file_validation import validate_image_file
from utils.image_processing import strip_exif

User = get_user_model()


class CreatedBySerializer(serializers.ModelSerializer):
    """Minimal user serializer for nested representation."""

    class Meta:
        model = User
        fields = ['id', 'username', 'is_trusted']


class ComponentImageSerializer(serializers.ModelSerializer):
    """Serializer for component images."""

    thumbnail = serializers.SerializerMethodField()
    medium = serializers.SerializerMethodField()
    uploaded_by = serializers.SerializerMethodField()
    component = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = ComponentImage
        fields = [
            'id', 'component', 'image', 'thumbnail', 'medium',
            'image_type', 'caption', 'display_order',
            'width', 'height', 'uploaded_by', 'uploaded_at', 'is_approved'
        ]
        read_only_fields = ['id', 'width', 'height', 'uploaded_at', 'is_approved']

    def get_uploaded_by(self, obj):
        if obj.uploaded_by:
            return {'id': str(obj.uploaded_by.id), 'username': obj.uploaded_by.username}
        return None

    def get_thumbnail(self, obj):
        if obj.thumbnail:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.thumbnail.url)
            return obj.thumbnail.url
        return None

    def get_medium(self, obj):
        if obj.medium:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.medium.url)
            return obj.medium.url
        return None


class ComponentImageUploadSerializer(serializers.ModelSerializer):
    """Serializer for uploading component images."""

    class Meta:
        model = ComponentImage
        fields = ['image', 'image_type', 'caption', 'display_order']

    def validate_image(self, value):
        validate_image_file(value)
        stripped = strip_exif(value)
        if stripped != value:
            value.file = stripped
            value.seek(0)
        return value


class ComponentListSerializer(serializers.ModelSerializer):
    """Serializer for component list view."""

    component_type_display = serializers.CharField(
        source='get_component_type_display',
        read_only=True
    )
    primary_value = serializers.CharField(read_only=True)
    primary_image = serializers.SerializerMethodField()

    class Meta:
        model = Component
        fields = [
            'id', 'part_number', 'manufacturer', 'component_type',
            'component_type_display', 'package_type', 'typical_function',
            'primary_value', 'primary_image', 'datasheet_url',
            'usage_count', 'is_verified'
        ]

    def _get_type_image_cache(self):
        """Load all ComponentTypeImage records once per serializer context."""
        if '_type_images' not in self.context:
            cache = {}
            for ti in ComponentTypeImage.objects.all():
                cache[(ti.component_type, ti.package_type)] = ti
            self.context['_type_images'] = cache
        return self.context['_type_images']

    def get_primary_image(self, obj):
        """
        Resolve component image with fallback:
        1. Component's own approved image (prefetched)
        2. ComponentTypeImage for (type, package)
        3. ComponentTypeImage for (type, '')
        4. None
        """
        # Own image (uses prefetched data)
        for image in obj.images.all():
            if image.is_approved:
                return ComponentImageSerializer(image, context=self.context).data

        # Type+package default, then type-only default (in-memory lookup)
        cache = self._get_type_image_cache()
        type_img = cache.get((obj.component_type, obj.package_type))
        if not type_img and obj.package_type:
            type_img = cache.get((obj.component_type, ''))
        if type_img:
            request = self.context.get('request')
            data = {'image': type_img.image.url, 'is_default': True}
            if type_img.thumbnail:
                url = type_img.thumbnail.url
                data['thumbnail'] = request.build_absolute_uri(url) if request else url
            if request:
                data['image'] = request.build_absolute_uri(data['image'])
            return data

        return None


class ComponentDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for single component view."""

    component_type_display = serializers.CharField(
        source='get_component_type_display',
        read_only=True
    )
    created_by = CreatedBySerializer(read_only=True)
    cross_references = ComponentListSerializer(many=True, read_only=True)
    pricing_data = serializers.SerializerMethodField()
    images = serializers.SerializerMethodField()

    class Meta:
        model = Component
        fields = [
            'id', 'part_number', 'manufacturer', 'manufacturer_aliases',
            'component_type', 'component_type_display', 'package_type',
            'description', 'typical_function', 'specifications',
            'datasheet_url', 'octopart_url', 'alternative_part_numbers',
            'cross_references', 'usage_count', 'is_verified',
            'created_by', 'created_at', 'updated_at', 'pricing_data',
            'images'
        ]
        read_only_fields = [
            'id', 'usage_count', 'is_verified',
            'created_by', 'created_at', 'updated_at'
        ]

    def get_pricing_data(self, obj):
        """Return cached Nexar data from specifications if available."""
        specs = obj.specifications or {}
        return specs.get('nexar_data')

    def get_images(self, obj):
        request = self.context.get('request')
        qs = obj.images.all()
        if not (request and hasattr(request, 'user') and request.user.is_staff):
            qs = qs.filter(is_approved=True)
        return ComponentImageSerializer(qs, many=True, context=self.context).data


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
    current_user_vote = serializers.SerializerMethodField()

    class Meta:
        model = ProductComponent
        fields = [
            'id', 'component', 'component_id', 'reference_designator',
            'quantity', 'location_description', 'board_name', 'notes',
            'image_reference', 'submission_level', 'submission_level_display',
            'is_verified', 'vote_score', 'confirm_count', 'dispute_count',
            'needs_review', 'current_user_vote', 'created_by', 'created_at'
        ]
        read_only_fields = [
            'id', 'is_verified', 'vote_score', 'confirm_count',
            'dispute_count', 'needs_review', 'created_by', 'created_at'
        ]

    def get_current_user_vote(self, obj):
        # Use prefetched current_user_votes if available
        if hasattr(obj, 'current_user_votes'):
            votes = obj.current_user_votes
            if votes:
                return votes[0].vote_type
            return None
        # Fallback: check from request context
        request = self.context.get('request')
        if request and hasattr(request, 'user') and request.user.is_authenticated:
            vote = obj.votes.filter(user=request.user).first()
            if vote:
                return vote.vote_type
        return None

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


class ComponentVoteSerializer(serializers.ModelSerializer):
    """Write serializer for casting a vote."""

    class Meta:
        model = ComponentVote
        fields = ['vote_type']


class ComponentVoteDetailSerializer(serializers.ModelSerializer):
    """Read serializer for vote details."""

    user = CreatedBySerializer(read_only=True)

    class Meta:
        model = ComponentVote
        fields = ['id', 'user', 'vote_type', 'weight', 'created_at']
