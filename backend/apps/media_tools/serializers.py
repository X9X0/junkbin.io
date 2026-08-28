from rest_framework import serializers

from apps.components.models import ComponentImage
from apps.products.models import ProductImage

from .bg_removal import MODEL_NAMES
from .models import BackgroundRemovalPreview


class BackgroundRemovalPreviewSerializer(serializers.ModelSerializer):
    # Not required at the field level - exactly one of original/
    # product_image/component_image is enforced in validate() below.
    # product_image/component_image are the retroactive moderator flow
    # (see apps.media_tools.views); a plain pre-submission preview sends
    # only `original` and leaves both of these unset.
    original = serializers.ImageField(required=False)
    product_image = serializers.PrimaryKeyRelatedField(
        queryset=ProductImage.objects.all(), required=False, allow_null=True)
    component_image = serializers.PrimaryKeyRelatedField(
        queryset=ComponentImage.objects.all(), required=False, allow_null=True)

    class Meta:
        model = BackgroundRemovalPreview
        fields = [
            'id', 'original', 'result', 'status', 'error',
            'model_name', 'alpha_matting', 'foreground_threshold',
            'background_threshold', 'erode_size', 'created_at',
            'product_image', 'component_image', 'applied_at',
        ]
        read_only_fields = [
            'id', 'result', 'status', 'error', 'created_at', 'applied_at',
        ]

    def validate_model_name(self, value):
        if value not in MODEL_NAMES:
            raise serializers.ValidationError('Unknown model.')
        return value

    def validate(self, attrs):
        # Only enforce "exactly one source" on create - reprocess doesn't
        # use this serializer, and a partial update (there isn't one
        # today, but just in case) shouldn't re-litigate the source.
        if self.instance is None:
            sources = [attrs.get('original'), attrs.get('product_image'), attrs.get('component_image')]
            if sum(1 for s in sources if s) != 1:
                raise serializers.ValidationError(
                    'Provide exactly one of: original (file), product_image, or component_image.'
                )
        return attrs


class BackgroundRemovalReprocessSerializer(serializers.Serializer):
    """Same tunable params as create, but no file - reprocesses the
    already-uploaded original."""

    model_name = serializers.ChoiceField(choices=sorted(MODEL_NAMES), required=False)
    alpha_matting = serializers.BooleanField(required=False)
    foreground_threshold = serializers.IntegerField(min_value=0, max_value=255, required=False)
    background_threshold = serializers.IntegerField(min_value=0, max_value=255, required=False)
    erode_size = serializers.IntegerField(min_value=0, max_value=100, required=False)
