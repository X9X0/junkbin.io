"""
Junkbin serializers for Junkbin.io API
"""
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from rest_framework import serializers

from apps.components.models import Component
from apps.products.models import Product

from .models import JunkbinItem

User = get_user_model()


class JunkbinUserSerializer(serializers.ModelSerializer):
    """Minimal user serializer for junkbin items."""

    class Meta:
        model = User
        fields = ['id', 'username', 'display_name', 'avatar']


class JunkbinItemListSerializer(serializers.ModelSerializer):
    """Serializer for junkbin item list views."""

    user = JunkbinUserSerializer(read_only=True)
    content_type = serializers.SerializerMethodField()
    item_name = serializers.SerializerMethodField()
    item_manufacturer = serializers.SerializerMethodField()
    item_slug = serializers.SerializerMethodField()

    class Meta:
        model = JunkbinItem
        fields = [
            'id', 'user', 'content_type', 'object_id',
            'item_name', 'item_manufacturer', 'item_slug',
            'item_type', 'status', 'condition', 'visibility',
            'notes', 'quantity', 'created_at', 'updated_at',
        ]
        read_only_fields = fields

    def get_content_type(self, obj):
        return obj.content_type.model

    def get_item_name(self, obj):
        target = obj.content_object
        if target is None:
            return '[Deleted]'
        if isinstance(target, Product):
            return f'{target.manufacturer} {target.model_number}'
        if isinstance(target, Component):
            return f'{target.manufacturer} {target.part_number}'
        return str(target)

    def get_item_manufacturer(self, obj):
        target = obj.content_object
        if target is None:
            return ''
        return getattr(target, 'manufacturer', '')

    def get_item_slug(self, obj):
        target = obj.content_object
        if target is None:
            return None
        return getattr(target, 'slug', None)


class JunkbinItemDetailSerializer(JunkbinItemListSerializer):
    """Serializer for junkbin item detail view."""
    pass


class JunkbinItemCreateSerializer(serializers.ModelSerializer):
    """Write serializer for creating/updating junkbin items."""

    content_type = serializers.ChoiceField(
        choices=['product', 'component'],
        write_only=True,
    )

    class Meta:
        model = JunkbinItem
        fields = [
            'content_type', 'object_id', 'item_type',
            'status', 'condition', 'visibility', 'notes', 'quantity',
        ]

    def validate(self, data):
        ct_str = data.pop('content_type')
        model_map = {
            'product': ('products', 'product'),
            'component': ('components', 'component'),
        }
        app_label, model = model_map[ct_str]
        ct = ContentType.objects.get(app_label=app_label, model=model)
        data['content_type'] = ct

        # Validate referenced object exists
        model_class = ct.model_class()
        if not model_class.objects.filter(id=data['object_id']).exists():
            raise serializers.ValidationError({
                'object_id': f'{ct_str.capitalize()} with this ID does not exist.'
            })

        return data

    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)


class JunkbinItemUpdateSerializer(serializers.ModelSerializer):
    """Update serializer — cannot change the target object or item_type."""

    class Meta:
        model = JunkbinItem
        fields = ['status', 'condition', 'visibility', 'notes', 'quantity']
