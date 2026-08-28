from rest_framework import mixins, viewsets, status
from rest_framework.decorators import action
from rest_framework.parsers import JSONParser, MultiPartParser, FormParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.api.permissions import IsVerifiedEmail
from apps.api.throttling import BgRemovalRateThrottle

from .models import BackgroundRemovalPreview
from .serializers import BackgroundRemovalPreviewSerializer, BackgroundRemovalReprocessSerializer
from .tasks import process_bg_removal


class BackgroundRemovalPreviewViewSet(
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    """
    Pre-submission background-removal workspace: upload a photo, get back
    a processed preview to compare against the original before deciding
    whether to actually attach it to a product/component.
    """

    serializer_class = BackgroundRemovalPreviewSerializer
    permission_classes = [IsAuthenticated, IsVerifiedEmail]
    throttle_classes = [BgRemovalRateThrottle]
    parser_classes = [MultiPartParser, FormParser]

    def get_queryset(self):
        return BackgroundRemovalPreview.objects.filter(created_by=self.request.user)

    def perform_create(self, serializer):
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
