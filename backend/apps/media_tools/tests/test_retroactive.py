"""
Tests for the retroactive moderator flow: creating a preview from an
existing product/component image, then /apply/ or /revert/ing it -
apps.media_tools.views.BackgroundRemovalPreviewViewSet.perform_create's
product_image/component_image branch, .apply(), and .revert().

process_bg_removal.delay is mocked throughout, same as test_views.py.
"""
import io
from unittest.mock import patch

import pytest
from django.urls import reverse
from django.utils import timezone
from PIL import Image
from rest_framework import status
from rest_framework.test import APIClient

from apps.components.models import Component, ComponentImage
from apps.media_tools.models import BackgroundRemovalPreview
from apps.products.tests.factories import ProductImageFactory
from apps.users.tests.factories import UserFactory


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def user(db):
    return UserFactory(email_verified=True)


@pytest.fixture
def moderator(db):
    return UserFactory(email_verified=True, moderator=True)


def _image_bytes():
    img = Image.new('RGB', (32, 32), (255, 0, 0))
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    return buf.getvalue()


def _product_image(**kwargs):
    from django.core.files.base import ContentFile
    pi = ProductImageFactory(**kwargs)
    pi.image.save('source.png', ContentFile(_image_bytes()), save=True)
    return pi


def _component_image(**kwargs):
    from django.core.files.base import ContentFile
    component = Component.objects.create(
        manufacturer='TestMfg', part_number='TEST-1', component_type='ic',
    )
    ci = ComponentImage(component=component, image_type=kwargs.pop('image_type', 'package'), **kwargs)
    ci.image.save('source.png', ContentFile(_image_bytes()), save=True)
    return ci


def list_url():
    return reverse('bg-removal-list')


def apply_url(pk):
    return reverse('bg-removal-apply', kwargs={'pk': pk})


def revert_url(pk):
    return reverse('bg-removal-revert', kwargs={'pk': pk})


class TestCreateFromExistingImage:
    @patch('apps.media_tools.views.process_bg_removal.delay')
    def test_plain_user_forbidden(self, mock_delay, api_client, user):
        pi = _product_image()
        api_client.force_authenticate(user=user)
        response = api_client.post(list_url(), {'product_image': str(pi.id)}, format='json')
        assert response.status_code == status.HTTP_403_FORBIDDEN
        mock_delay.assert_not_called()

    @patch('apps.media_tools.views.process_bg_removal.delay')
    def test_moderator_can_create_from_product_image(self, mock_delay, api_client, moderator):
        pi = _product_image()
        api_client.force_authenticate(user=moderator)
        response = api_client.post(list_url(), {'product_image': str(pi.id)}, format='json')
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['status'] == 'pending'
        mock_delay.assert_called_once()

        preview = BackgroundRemovalPreview.objects.get(id=response.data['id'])
        assert preview.product_image_id == pi.id
        assert preview.original.read() == _image_bytes()

    @patch('apps.media_tools.views.process_bg_removal.delay')
    def test_moderator_can_create_from_component_image(self, mock_delay, api_client, moderator):
        ci = _component_image()
        api_client.force_authenticate(user=moderator)
        response = api_client.post(list_url(), {'component_image': str(ci.id)}, format='json')
        assert response.status_code == status.HTTP_201_CREATED
        preview = BackgroundRemovalPreview.objects.get(id=response.data['id'])
        assert preview.component_image_id == ci.id

    @patch('apps.media_tools.views.process_bg_removal.delay')
    def test_rejects_already_background_removed(self, mock_delay, api_client, moderator):
        pi = _product_image(background_removed=True)
        api_client.force_authenticate(user=moderator)
        response = api_client.post(list_url(), {'product_image': str(pi.id)}, format='json')
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        mock_delay.assert_not_called()

    @patch('apps.media_tools.views.process_bg_removal.delay')
    def test_rejects_already_transparent(self, mock_delay, api_client, moderator):
        pi = _product_image(has_transparency=True)
        api_client.force_authenticate(user=moderator)
        response = api_client.post(list_url(), {'product_image': str(pi.id)}, format='json')
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        mock_delay.assert_not_called()

    @patch('apps.media_tools.views.process_bg_removal.delay')
    def test_rejects_both_file_and_product_image(self, mock_delay, api_client, moderator):
        from django.core.files.uploadedfile import SimpleUploadedFile
        pi = _product_image()
        api_client.force_authenticate(user=moderator)
        response = api_client.post(
            list_url(),
            {
                'product_image': str(pi.id),
                'original': SimpleUploadedFile('x.png', _image_bytes(), content_type='image/png'),
            },
            format='multipart',
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @patch('apps.media_tools.views.process_bg_removal.delay')
    def test_rejects_neither_source(self, mock_delay, api_client, moderator):
        api_client.force_authenticate(user=moderator)
        response = api_client.post(list_url(), {}, format='json')
        assert response.status_code == status.HTTP_400_BAD_REQUEST


def _done_preview_for(target, *, field):
    """A preview already in 'done' state with a fake result, as if
    process_bg_removal_job had already run - avoids running rembg for
    real in these permission/plumbing tests."""
    from django.core.files.base import ContentFile
    kwargs = {field: target}
    preview = BackgroundRemovalPreview.objects.create(
        created_by=target.uploaded_by or UserFactory(email_verified=True),
        status=BackgroundRemovalPreview.Status.DONE,
        **kwargs,
    )
    preview.original.save('orig.png', ContentFile(_image_bytes()), save=False)
    preview.result.save('result.png', ContentFile(_image_bytes()), save=True)
    return preview


class TestApply:
    def test_plain_user_forbidden(self, api_client, user):
        pi = _product_image()
        preview = _done_preview_for(pi, field='product_image')
        api_client.force_authenticate(user=user)
        response = api_client.post(apply_url(preview.id))
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_moderator_applies_to_product_image(self, api_client, moderator):
        pi = _product_image()
        preview = _done_preview_for(pi, field='product_image')
        api_client.force_authenticate(user=moderator)
        response = api_client.post(apply_url(preview.id))
        assert response.status_code == status.HTTP_200_OK

        pi.refresh_from_db()
        assert pi.background_removed is True
        assert pi.has_transparency is False

        preview.refresh_from_db()
        assert preview.applied_at is not None

    def test_not_ready_rejected(self, api_client, moderator):
        pi = _product_image()
        preview = BackgroundRemovalPreview.objects.create(
            created_by=moderator, status=BackgroundRemovalPreview.Status.PENDING, product_image=pi,
        )
        from django.core.files.base import ContentFile
        preview.original.save('orig.png', ContentFile(_image_bytes()), save=True)
        api_client.force_authenticate(user=moderator)
        response = api_client.post(apply_url(preview.id))
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_unlinked_preview_rejected(self, api_client, moderator, user):
        from django.core.files.base import ContentFile
        preview = BackgroundRemovalPreview.objects.create(
            created_by=user, status=BackgroundRemovalPreview.Status.DONE,
        )
        preview.original.save('orig.png', ContentFile(_image_bytes()), save=False)
        preview.result.save('result.png', ContentFile(_image_bytes()), save=True)
        api_client.force_authenticate(user=moderator)
        response = api_client.post(apply_url(preview.id))
        assert response.status_code == status.HTTP_400_BAD_REQUEST


class TestRevert:
    def test_revert_restores_original_and_flag(self, api_client, moderator):
        pi = _product_image()
        preview = _done_preview_for(pi, field='product_image')
        api_client.force_authenticate(user=moderator)

        assert api_client.post(apply_url(preview.id)).status_code == status.HTTP_200_OK
        pi.refresh_from_db()
        assert pi.background_removed is True

        response = api_client.post(revert_url(preview.id))
        assert response.status_code == status.HTTP_200_OK

        pi.refresh_from_db()
        assert pi.background_removed is False

        preview.refresh_from_db()
        assert preview.applied_at is None

    def test_revert_without_apply_rejected(self, api_client, moderator):
        pi = _product_image()
        preview = _done_preview_for(pi, field='product_image')
        api_client.force_authenticate(user=moderator)
        response = api_client.post(revert_url(preview.id))
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_plain_user_forbidden(self, api_client, user):
        pi = _product_image()
        preview = _done_preview_for(pi, field='product_image')
        preview.applied_at = timezone.now()
        preview.save(update_fields=['applied_at'])
        api_client.force_authenticate(user=user)
        response = api_client.post(revert_url(preview.id))
        assert response.status_code == status.HTTP_403_FORBIDDEN


class TestListFilter:
    """Backs the frontend's Undo control - finding the applied preview for
    a given image without denormalizing a pointer onto it."""

    def test_filters_by_product_image(self, api_client, moderator):
        pi1 = _product_image()
        pi2 = _product_image()
        preview1 = _done_preview_for(pi1, field='product_image')
        _done_preview_for(pi2, field='product_image')

        api_client.force_authenticate(user=moderator)
        response = api_client.get(list_url(), {'product_image': str(pi1.id)})
        assert response.status_code == status.HTTP_200_OK
        ids = [r['id'] for r in response.data['results']]
        assert ids == [str(preview1.id)]

    def test_plain_user_only_sees_own_previews(self, api_client, user):
        pi = _product_image()
        other_user = UserFactory(email_verified=True)
        preview = BackgroundRemovalPreview.objects.create(
            created_by=other_user, status=BackgroundRemovalPreview.Status.DONE, product_image=pi,
        )
        from django.core.files.base import ContentFile
        preview.original.save('orig.png', ContentFile(_image_bytes()), save=True)

        api_client.force_authenticate(user=user)
        response = api_client.get(list_url(), {'product_image': str(pi.id)})
        assert response.data['results'] == []
