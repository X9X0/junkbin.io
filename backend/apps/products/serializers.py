"""
Product serializers for Junkbin.io API
"""
from rest_framework import serializers
from django.contrib.auth import get_user_model

from .models import Product, ProductImage, Schematic
from utils.file_validation import validate_image_file, validate_schematic_file
from utils.image_processing import strip_exif

User = get_user_model()


class ProductImageSerializer(serializers.ModelSerializer):
    """Serializer for product images."""

    thumbnail = serializers.SerializerMethodField()
    medium = serializers.SerializerMethodField()

    class Meta:
        model = ProductImage
        fields = [
            'id', 'image', 'thumbnail', 'medium',
            'image_type', 'caption', 'display_order',
            'width', 'height', 'uploaded_at'
        ]
        read_only_fields = ['id', 'width', 'height', 'uploaded_at']

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


class ProductImageUploadSerializer(serializers.ModelSerializer):
    """Serializer for uploading product images."""

    class Meta:
        model = ProductImage
        fields = ['image', 'image_type', 'caption', 'display_order']

    def validate_image(self, value):
        """Validate image file and strip EXIF data for privacy."""
        # Verify file content matches extension using magic bytes
        validate_image_file(value)

        # Strip EXIF data to protect user privacy (removes GPS, camera info, etc.)
        stripped = strip_exif(value)
        if stripped != value:
            # Update the file with EXIF-stripped version
            value.file = stripped
            value.seek(0)

        return value


class CreatedBySerializer(serializers.ModelSerializer):
    """Minimal user serializer for nested representation."""

    class Meta:
        model = User
        fields = ['id', 'username', 'is_trusted']


class ProductListSerializer(serializers.ModelSerializer):
    """Serializer for product list view."""

    created_by = CreatedBySerializer(read_only=True)
    primary_image = serializers.SerializerMethodField()
    image_count = serializers.SerializerMethodField()
    schematic_count = serializers.SerializerMethodField()
    category_display = serializers.CharField(
        source='get_category_display',
        read_only=True
    )
    region_display = serializers.CharField(
        source='get_region_display',
        read_only=True
    )

    class Meta:
        model = Product
        fields = [
            'id', 'slug', 'manufacturer', 'model_number', 'revision',
            'region', 'region_display', 'category', 'category_display',
            'year_manufactured', 'component_count', 'image_count',
            'schematic_count', 'primary_image',
            'created_by', 'created_at', 'is_approved', 'is_featured'
        ]

    def get_primary_image(self, obj):
        image = obj.primary_image
        if image:
            return ProductImageSerializer(image, context=self.context).data
        return None

    def get_image_count(self, obj):
        return obj.images.count()

    def get_schematic_count(self, obj):
        return obj.schematics.filter(is_approved=True).count()


class ProductDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for single product view."""

    created_by = CreatedBySerializer(read_only=True)
    images = ProductImageSerializer(many=True, read_only=True)
    image_count = serializers.SerializerMethodField()
    schematic_count = serializers.SerializerMethodField()
    category_display = serializers.CharField(
        source='get_category_display',
        read_only=True
    )
    region_display = serializers.CharField(
        source='get_region_display',
        read_only=True
    )

    class Meta:
        model = Product
        fields = [
            'id', 'slug', 'manufacturer', 'model_number', 'revision',
            'region', 'region_display', 'category', 'category_display',
            'subcategory', 'year_manufactured', 'fcc_id', 'ic_id',
            'part_number', 'description', 'teardown_notes',
            'component_count', 'image_count', 'schematic_count',
            'view_count', 'images',
            'created_by', 'created_at', 'updated_at',
            'is_approved', 'is_featured'
        ]
        read_only_fields = [
            'id', 'slug', 'component_count', 'view_count',
            'created_by', 'created_at', 'updated_at',
            'is_approved', 'is_featured'
        ]

    def get_image_count(self, obj):
        return obj.images.count()

    def get_schematic_count(self, obj):
        return obj.schematics.filter(is_approved=True).count()


class ProductCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating new products."""

    class Meta:
        model = Product
        fields = [
            'id', 'slug', 'manufacturer', 'model_number', 'revision', 'region',
            'category', 'subcategory', 'year_manufactured',
            'fcc_id', 'ic_id', 'part_number', 'description', 'teardown_notes'
        ]
        read_only_fields = ['id', 'slug']
        extra_kwargs = {
            'revision': {'required': False, 'default': ''},
            'region': {'required': False, 'default': 'global'},
            'subcategory': {'required': False, 'default': ''},
            'fcc_id': {'required': False, 'default': ''},
            'ic_id': {'required': False, 'default': ''},
            'part_number': {'required': False, 'default': ''},
            'description': {'required': False, 'default': ''},
            'teardown_notes': {'required': False, 'default': ''},
        }

    def validate(self, attrs):
        # Check for duplicate product
        queryset = Product.objects.filter(
            manufacturer__iexact=attrs['manufacturer'],
            model_number__iexact=attrs['model_number'],
            revision=attrs.get('revision', ''),
            region=attrs.get('region', 'global')
        )
        if self.instance:
            queryset = queryset.exclude(pk=self.instance.pk)

        if queryset.exists():
            raise serializers.ValidationError(
                'A product with this manufacturer, model, revision, and region already exists.'
            )
        return attrs

    def create(self, validated_data):
        validated_data['created_by'] = self.context['request'].user
        return super().create(validated_data)


class ProductSearchSerializer(serializers.Serializer):
    """Serializer for product search parameters."""

    q = serializers.CharField(required=False, allow_blank=True, max_length=200)
    manufacturer = serializers.CharField(required=False, max_length=200)
    category = serializers.CharField(required=False, max_length=50)
    region = serializers.CharField(required=False, max_length=20)
    year_min = serializers.IntegerField(required=False)
    year_max = serializers.IntegerField(required=False)
    has_component = serializers.UUIDField(required=False)


class SchematicSerializer(serializers.ModelSerializer):
    """Serializer for schematics."""

    uploaded_by = CreatedBySerializer(read_only=True)
    schematic_type_display = serializers.CharField(
        source='get_schematic_type_display',
        read_only=True
    )
    source_type_display = serializers.CharField(
        source='get_source_type_display',
        read_only=True
    )
    file_url = serializers.SerializerMethodField()

    class Meta:
        model = Schematic
        fields = [
            'id', 'schematic_type', 'schematic_type_display',
            'title', 'description', 'version', 'page_count',
            'file', 'file_url', 'file_type', 'file_size',
            'source_type', 'source_type_display', 'source_url', 'source_notes',
            'repair_relevance', 'download_count',
            'uploaded_by', 'uploaded_at', 'is_approved'
        ]
        read_only_fields = [
            'id', 'file_type', 'file_size', 'download_count',
            'uploaded_by', 'uploaded_at', 'is_approved'
        ]

    def get_file_url(self, obj):
        if obj.file:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.file.url)
            return obj.file.url
        return None


class SchematicUploadSerializer(serializers.ModelSerializer):
    """Serializer for uploading schematics."""

    class Meta:
        model = Schematic
        fields = [
            'file', 'schematic_type', 'title', 'description', 'version',
            'page_count', 'source_type', 'source_url', 'source_notes',
            'repair_relevance'
        ]

    def validate_file(self, value):
        """Validate schematic file content matches extension using magic bytes."""
        validate_schematic_file(value)
        return value

    def create(self, validated_data):
        validated_data['uploaded_by'] = self.context['request'].user
        return super().create(validated_data)
