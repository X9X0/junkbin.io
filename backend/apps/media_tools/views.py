from django.core.files.base import ContentFile
from django.utils import timezone
from rest_framework import mixins, viewsets, status
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.parsers import JSONParser, MultiPartParser, FormParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.api.permissions import IsVerifiedEmail
from apps.api.throttling import BgRemovalRateThrottle
from apps.components.models import ComponentImage
from apps.components.serializers import ComponentImageSerializer
from apps.products.serializers import ProductImageSerializer

from .models import BackgroundRemovalPreview
from .serializers import BackgroundRemovalPreviewSerializer, BackgroundRemovalReprocessSerializer
from .tasks import process_bg_removal


def _is_moderator_or_staff(user):
    return bool(user and user.is_authenticated and (user.is_staff or getattr(user, 'is_moderator', False)))


def _target_image(preview):
    return preview.product_image or preview.component_image


def _serialize_target(target, request):
    if isinstance(target, ComponentImage):
        return ComponentImageSerializer(target, context={'request': request}).data
    return ProductImageSerializer(target, context={'request': request}).data


class BackgroundRemovalPreviewViewSet(
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.ListModelMixin,
    viewsets.GenericViewSet,
):
    """
    Background-removal workspace, covering two flows:

    1. Pre-submission preview: upload a photo, get back a processed
       preview to compare against the original before deciding whether
       to attach it to a product/component (any verified user).
    2. Retroactive moderator apply: create a preview FROM an existing
       product_image/component_image instead of a file upload, then
       /apply/ (or /revert/) it onto that live image (moderators/staff
       only - this mutates already-public content).
    """

    serializer_class = BackgroundRemovalPreviewSerializer
    permission_classes = [IsAuthenticated, IsVerifiedEmail]
    throttle_classes = [BgRemovalRateThrottle]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get_queryset(self):
        # Moderators/staff can retrieve/apply/revert any preview - the
        # retroactive flow is a team tool, not tied to whoever happened to
        # click first. Regular users stay confined to their own scratch
        # previews from the pre-submission flow.
        qs = BackgroundRemovalPreview.objects.all()
        if not _is_moderator_or_staff(self.request.user):
            qs = qs.filter(created_by=self.request.user)

        # Lets the frontend find "the applied preview for this image" (for
        # an Undo control) without denormalizing a pointer onto
        # ProductImage/ComponentImage - list is only ever used this way.
        product_image = self.request.query_params.get('product_image')
        if product_image:
            qs = qs.filter(product_image_id=product_image)
        component_image = self.request.query_params.get('component_image')
        if component_image:
            qs = qs.filter(component_image_id=component_image)

        return qs

    def perform_create(self, serializer):
        target = serializer.validated_data.get('product_image') or serializer.validated_data.get('component_image')

        if target is not None:
            if not _is_moderator_or_staff(self.request.user):
                raise PermissionDenied('Only moderators can apply background removal to an existing image.')
            if target.background_removed:
                raise ValidationError('This image has already had its background removed.')
            if target.has_transparency:
                raise ValidationError('This image already has a transparent background.')

            with target.image.open('rb') as f:
                content = ContentFile(f.read(), name=target.image.name.rsplit('/', 1)[-1])
            preview = serializer.save(created_by=self.request.user, original=content)
        else:
            preview = serializer.save(created_by=self.request.user)

        process_bg_removal.delay(str(preview.id))

    @action(detail=True, methods=['post'], parser_classes=[JSONParser, FormParser, MultiPartParser])
    def reprocess(self, request, pk=None):
        """Re-run with different parameters against the already-uploaded
        original - no need to re-send the file."""
        preview = self.get_object()
        params = BackgroundRemovalReprocessSerializer(data=request.data)
        params.is_valid(raise_exception=True)

        for field, value in params.validated_data.items():
            setattr(preview, field, value)
        preview.status = BackgroundRemovalPreview.Status.PENDING
        preview.error = ''
        preview.save()

        process_bg_removal.delay(str(preview.id))
        return Response(
            self.get_serializer(preview).data,
            status=status.HTTP_202_ACCEPTED,
        )

    @action(detail=True, methods=['post'])
    def apply(self, request, pk=None):
        """Replace the linked product/component image's file with this
        preview's processed result. Moderators/staff only."""
        if not _is_moderator_or_staff(request.user):
            raise PermissionDenied('Only moderators can apply background removal to an existing image.')

        preview = self.get_object()
        target = _target_image(preview)
        if target is None:
            raise ValidationError('This preview is not linked to an existing image.')
        if preview.status != BackgroundRemovalPreview.Status.DONE:
            raise ValidationError('Preview is not ready yet.')

        with preview.result.open('rb') as f:
            target.image.save(f'{preview.id}.png', ContentFile(f.read()), save=False)
        target.width = None
        target.height = None
        target.file_size = None
        target.background_removed = True
        target.has_transparency = False
        target.save()

        preview.applied_at = timezone.now()
        preview.save(update_fields=['applied_at'])

        return Response(_serialize_target(target, request))

    @action(detail=True, methods=['post'])
    def revert(self, request, pk=None):
        """Undo a previous /apply/, restoring the image this preview was
        created from. Moderators/staff only."""
        if not _is_moderator_or_staff(request.user):
            raise PermissionDenied('Only moderators can revert background removal.')

        preview = self.get_object()
        target = _target_image(preview)
        if target is None:
            raise ValidationError('This preview is not linked to an existing image.')
        if not preview.applied_at:
            raise ValidationError('This preview was never applied.')

        from PIL import Image
        from apps.products.models import image_has_transparency

        with preview.original.open('rb') as f:
            content = f.read()
        target.image.save(f'{preview.id}-reverted.png', ContentFile(content), save=False)
        target.width = None
        target.height = None
        target.file_size = None
        target.background_removed = False
        with Image.open(target.image) as img:
            target.has_transparency = image_has_transparency(img)
        target.save()

        preview.applied_at = None
        preview.save(update_fields=['applied_at'])

        return Response(_serialize_target(target, request))
