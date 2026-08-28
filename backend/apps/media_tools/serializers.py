from rest_framework import serializers

from .bg_removal import MODEL_NAMES
from .models import BackgroundRemovalPreview


class BackgroundRemovalPreviewSerializer(serializers.ModelSerializer):
    class Meta:
        model = BackgroundRemovalPreview
        fields = [
            'id', 'original', 'result', 'status', 'error',
            'model_name', 'alpha_matting', 'foreground_threshold',
            'background_threshold', 'erode_size', 'created_at',
        ]
        read_only_fields = [
            'id', 'result', 'status', 'error', 'created_at',
        ]

    def validate_model_name(self, value):
        if value not in MODEL_NAMES:
            raise serializers.ValidationError('Unknown model.')
        return value


class BackgroundRemovalReprocessSerializer(serializers.Serializer):
    """Same tunable params as create, but no file - reprocesses the
    already-uploaded original."""

    model_name = serializers.ChoiceField(choices=sorted(MODEL_NAMES), required=False)
    alpha_matting = serializers.BooleanField(required=False)
    foreground_threshold = serializers.IntegerField(min_value=0, max_value=255, required=False)
    background_threshold = serializers.IntegerField(min_value=0, max_value=255, required=False)
    erode_size = serializers.IntegerField(min_value=0, max_value=100, required=False)
