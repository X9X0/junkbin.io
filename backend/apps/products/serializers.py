"""
Product serializers for Junkbin.io API
"""
from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _

from .models import (
    Product, ProductImage, ProductComment, Schematic, Firmware,
    ComponentSuggestion, RepairReport, RepairReportVote,
)
from utils.file_validation import validate_firmware_file, validate_image_file, validate_schematic_file
from utils.image_processing import strip_exif

User = get_user_model()


class ProductImageSerializer(serializers.ModelSerializer):
    """Serializer for product images."""

    thumbnail = serializers.SerializerMethodField()
    medium = serializers.SerializerMethodField()
    uploaded_by = serializers.SerializerMethodField()
    product = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = ProductImage
        fields = [
            'id', 'product', 'image', 'thumbnail', 'medium',
            'image_type', 'caption', 'display_order',
            'width', 'height', 'uploaded_by', 'uploaded_at', 'is_approved',
            'background_removed', 'has_transparency',
        ]
        read_only_fields = [
            'id', 'width', 'height', 'uploaded_at', 'is_approved',
            'has_transparency',
        ]

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


class ProductImageUploadSerializer(serializers.ModelSerializer):
    """Serializer for uploading product images."""

    class Meta:
        model = ProductImage
        fields = ['image', 'image_type', 'caption', 'display_order', 'background_removed']

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
    firmware_count = serializers.SerializerMethodField()
    category_display = serializers.CharField(
        source='get_category_display',
        read_only=True
    )
    region_display = serializers.CharField(
        source='get_region_display',
        read_only=True
    )

    comment_count = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = [
            'id', 'slug', 'manufacturer', 'model_number', 'revision',
            'region', 'region_display', 'category', 'category_display',
            'year_manufactured', 'component_count', 'image_count',
            'schematic_count', 'firmware_count', 'comment_count', 'primary_image',
            'created_by', 'created_at', 'is_approved', 'is_featured'
        ]

    def get_primary_image(self, obj):
        images = self._visible_images(obj)
        image = images.filter(image_type='overview').first() or images.first()
        if image:
            return ProductImageSerializer(image, context=self.context).data
        return None

    def _visible_images(self, obj):
        request = self.context.get('request')
        qs = obj.images.all()
        if request and hasattr(request, 'user') and request.user.is_staff:
            return qs
        return qs.filter(is_approved=True)

    def get_image_count(self, obj):
        return self._visible_images(obj).count()

    def get_schematic_count(self, obj):
        return obj.schematics.filter(is_approved=True).count()

    def get_firmware_count(self, obj):
        return obj.firmware_files.filter(is_approved=True).count()

    def get_comment_count(self, obj):
        return obj.comments.count()


class ProductDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for single product view."""

    created_by = CreatedBySerializer(read_only=True)
    images = serializers.SerializerMethodField()
    image_count = serializers.SerializerMethodField()
    schematic_count = serializers.SerializerMethodField()
    firmware_count = serializers.SerializerMethodField()
    category_display = serializers.CharField(
        source='get_category_display',
        read_only=True
    )
    region_display = serializers.CharField(
        source='get_region_display',
        read_only=True
    )

    comment_count = serializers.SerializerMethodField()
    repair_report_count = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = [
            'id', 'slug', 'manufacturer', 'model_number', 'revision',
            'region', 'region_display', 'category', 'category_display',
            'subcategory', 'year_manufactured', 'fcc_id', 'ic_id',
            'part_number', 'description', 'teardown_notes',
            'component_count', 'image_count', 'schematic_count', 'firmware_count',
            'comment_count', 'repair_report_count', 'view_count', 'images',
            'created_by', 'created_at', 'updated_at',
            'is_approved', 'is_featured'
        ]
        read_only_fields = [
            'id', 'slug', 'component_count', 'view_count',
            'created_by', 'created_at', 'updated_at',
            'is_approved', 'is_featured'
        ]

    def _visible_images(self, obj):
        request = self.context.get('request')
        qs = obj.images.all()
        if request and hasattr(request, 'user') and request.user.is_staff:
            return qs
        return qs.filter(is_approved=True)

    def get_images(self, obj):
        return ProductImageSerializer(
            self._visible_images(obj), many=True, context=self.context
        ).data

    def get_image_count(self, obj):
        return self._visible_images(obj).count()

    def get_schematic_count(self, obj):
        return obj.schematics.filter(is_approved=True).count()

    def get_firmware_count(self, obj):
        return obj.firmware_files.filter(is_approved=True).count()

    def get_comment_count(self, obj):
        return obj.comments.count()

    def get_repair_report_count(self, obj):
        return obj.repair_reports.filter(is_approved=True).count()


def _product_duplicate_thumbnail(product, request):
    """Best-approved image URL for a product, for the duplicate-suggestion UI."""
    image = product.images.filter(is_approved=True, image_type='overview').first()
    if not image:
        image = product.images.filter(is_approved=True).first()
    if image and image.thumbnail:
        url = image.thumbnail.url
        return request.build_absolute_uri(url) if request else url
    return None


class ProductCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating new products."""

    class Meta:
        model = Product
        fields = [
            'id', 'slug', 'manufacturer', 'model_number', 'revision', 'region',
            'category', 'subcategory', 'year_manufactured',
            'fcc_id', 'ic_id', 'part_number', 'description', 'teardown_notes',
            'is_approved'
        ]
        read_only_fields = ['id', 'slug', 'is_approved']
        # Disable DRF's auto-generated UniqueTogetherValidator (from the model's
        # UniqueConstraint) — it would run before validate() below and short-circuit
        # with a generic message, never attaching duplicate_of for the frontend.
        validators = []
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

        existing = queryset.first()
        if existing:
            request = self.context.get('request')
            description = existing.description or ''
            raise serializers.ValidationError({
                'non_field_errors': [
                    _('A product with this manufacturer, model, revision, and region already exists.')
                ],
                'duplicate_of': {
                    'type': 'product',
                    'id': str(existing.id),
                    'slug': existing.slug,
                    'manufacturer': existing.manufacturer,
                    'model_number': existing.model_number,
                    'category_display': existing.get_category_display(),
                    'year_manufactured': existing.year_manufactured,
                    'description': description[:200] + ('…' if len(description) > 200 else ''),
                    'thumbnail': _product_duplicate_thumbnail(existing, request),
                },
            })
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
            'id', 'product', 'schematic_type', 'schematic_type_display',
            'title', 'description', 'version', 'page_count',
            'file', 'file_url', 'file_type', 'file_size',
            'source_type', 'source_type_display', 'source_url', 'source_notes',
            'repair_relevance', 'download_count',
            'uploaded_by', 'uploaded_at', 'is_approved'
        ]
        read_only_fields = [
            'id', 'product', 'file_type', 'file_size', 'download_count',
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


class FirmwareSerializer(serializers.ModelSerializer):
    """Serializer for firmware."""

    uploaded_by = CreatedBySerializer(read_only=True)
    source_type_display = serializers.CharField(
        source='get_source_type_display',
        read_only=True
    )
    file_url = serializers.SerializerMethodField()

    class Meta:
        model = Firmware
        fields = [
            'id', 'product', 'title', 'description', 'version', 'chip_architecture',
            'file', 'file_url', 'file_type', 'file_size',
            'source_type', 'source_type_display', 'source_url', 'source_notes',
            'download_count', 'uploaded_by', 'uploaded_at', 'is_approved'
        ]
        read_only_fields = [
            'id', 'product', 'file_type', 'file_size', 'download_count',
            'uploaded_by', 'uploaded_at', 'is_approved'
        ]

    def get_file_url(self, obj):
        if obj.file:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.file.url)
            return obj.file.url
        return None


class FirmwareUploadSerializer(serializers.ModelSerializer):
    """Serializer for uploading firmware."""

    class Meta:
        model = Firmware
        fields = [
            'file', 'title', 'description', 'version', 'chip_architecture',
            'source_type', 'source_url', 'source_notes'
        ]

    def validate_file(self, value):
        """Validate firmware file content matches extension using magic bytes."""
        validate_firmware_file(value)
        return value

    def create(self, validated_data):
        validated_data['uploaded_by'] = self.context['request'].user
        return super().create(validated_data)


class ComponentSuggestionSerializer(serializers.ModelSerializer):
    """Serializer for reviewing machine-extracted component suggestions."""

    uploaded_by = CreatedBySerializer(read_only=True)
    source_type_display = serializers.CharField(source='get_source_type_display', read_only=True)
    confidence_display = serializers.CharField(source='get_confidence_display', read_only=True)
    matched_component = serializers.SerializerMethodField()

    class Meta:
        model = ComponentSuggestion
        fields = [
            'id', 'product', 'source_type', 'source_type_display', 'source_file',
            'page_number', 'extraction_context', 'confidence', 'confidence_display',
            'part_number', 'manufacturer', 'reference_designator', 'component_type',
            'package_type', 'description', 'value_raw', 'quantity', 'location_description',
            'matched_component', 'uploaded_by', 'uploaded_at', 'is_approved',
        ]
        read_only_fields = [
            'id', 'product', 'source_type', 'source_file', 'page_number',
            'extraction_context', 'confidence', 'matched_component',
            'uploaded_by', 'uploaded_at', 'is_approved',
        ]

    def get_matched_component(self, obj):
        if obj.matched_component:
            return {
                'id': str(obj.matched_component.id),
                'part_number': obj.matched_component.part_number,
                'manufacturer': obj.matched_component.manufacturer,
            }
        return None


class ProductCommentSerializer(serializers.ModelSerializer):
    """Serializer for reading product comments."""

    author = CreatedBySerializer(read_only=True)

    class Meta:
        model = ProductComment
        fields = ['id', 'author', 'content', 'created_at', 'updated_at']
        read_only_fields = ['id', 'author', 'created_at', 'updated_at']


class ProductCommentCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating product comments."""

    class Meta:
        model = ProductComment
        fields = ['content']

    def validate_content(self, value):
        stripped = value.strip()
        if not stripped:
            raise serializers.ValidationError(_('Comment cannot be empty.'))
        from utils.content_filter import check_content
        is_clean, _ = check_content(stripped)
        if not is_clean:
            raise serializers.ValidationError(
                _('Your comment contains prohibited language. '
                  'Please review our community guidelines.')
            )
        return stripped

    def create(self, validated_data):
        validated_data['author'] = self.context['request'].user
        validated_data['product'] = self.context['product']
        return super().create(validated_data)


class RepairReportSerializer(serializers.ModelSerializer):
    """Serializer for reading repair reports."""

    author = CreatedBySerializer(read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    product_component = serializers.SerializerMethodField()
    user_vote = serializers.SerializerMethodField()

    class Meta:
        model = RepairReport
        fields = [
            'id', 'author', 'title', 'symptom', 'diagnostics', 'resolution',
            'status', 'status_display', 'product_component',
            'helpful_count', 'unhelpful_count', 'user_vote',
            'is_approved', 'created_at', 'updated_at',
        ]
        read_only_fields = fields

    def get_product_component(self, obj):
        if obj.product_component:
            return {
                'id': str(obj.product_component.id),
                'reference_designator': obj.product_component.reference_designator,
                'component': str(obj.product_component.component),
            }
        return None

    def get_user_vote(self, obj):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return None
        vote = obj.votes.filter(user=request.user).first()
        return vote.vote_type if vote else None


class RepairReportCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating/updating repair reports."""

    class Meta:
        model = RepairReport
        fields = ['title', 'symptom', 'diagnostics', 'resolution', 'status', 'product_component']

    def validate_product_component(self, value):
        if value is not None:
            product = self.context['product']
            if value.product_id != product.id:
                raise serializers.ValidationError(
                    _('Selected component does not belong to this product.')
                )
        return value

    def validate(self, attrs):
        status = attrs.get('status', RepairReport.Status.UNRESOLVED)
        resolution = attrs.get('resolution', '').strip()
        if status == RepairReport.Status.RESOLVED and not resolution:
            raise serializers.ValidationError({
                'resolution': _('Resolution is required to mark a repair as resolved.')
            })
        return attrs

    def validate_title(self, value):
        stripped = value.strip()
        if not stripped:
            raise serializers.ValidationError(_('Title cannot be empty.'))
        return stripped

    def validate_symptom(self, value):
        stripped = value.strip()
        if not stripped:
            raise serializers.ValidationError(_('Symptom description cannot be empty.'))
        return stripped

    def create(self, validated_data):
        from utils.content_filter import check_content

        text = ' '.join(filter(None, [
            validated_data.get('title', ''),
            validated_data.get('symptom', ''),
            validated_data.get('diagnostics', ''),
            validated_data.get('resolution', ''),
        ]))
        is_clean, _matched = check_content(text)
        if not is_clean:
            raise serializers.ValidationError(
                _('Your report contains prohibited language. '
                  'Please review our community guidelines.')
            )

        validated_data['author'] = self.context['request'].user
        validated_data['product'] = self.context['product']
        return super().create(validated_data)


class RepairReportVoteSerializer(serializers.ModelSerializer):
    """Write serializer for casting a vote on a repair report."""

    class Meta:
        model = RepairReportVote
        fields = ['vote_type']
