"""
API tests for the background-removal preview endpoints.

process_bg_removal.delay is mocked throughout - these tests are about the
HTTP/permission/ownership contract, not about running rembg for real
(that's apps.media_tools.tests.test_bg_removal, which does).
"""
import io
from unittest.mock import patch

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from PIL import Image
from rest_framework import status
from rest_framework.test import APIClient

from apps.media_tools.models import BackgroundRemovalPreview
from apps.users.tests.factories import UserFactory


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def user(db):
    return UserFactory(email_verified=True)


def _test_image_file(name='test.png'):
    img = Image.new('RGB', (32, 32), (255, 0, 0))
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    buf.seek(0)
    return SimpleUploadedFile(name, buf.read(), content_type='image/png')


def list_url():
    return reverse('bg-removal-list')


def detail_url(pk):
    return reverse('bg-removal-detail', kwargs={'pk': pk})


def reprocess_url(pk):
    return reverse('bg-removal-reprocess', kwargs={'pk': pk})


class TestCreate:
    @patch('apps.media_tools.views.process_bg_removal.delay')
    def test_requires_authentication(self, mock_delay, api_client):
        response = api_client.post(list_url(), {'original': _test_image_file()}, format='multipart')
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        mock_delay.assert_not_called()

    @patch('apps.media_tools.views.process_bg_removal.delay')
    def test_unverified_email_forbidden(self, mock_delay, api_client, db):
        unverified = UserFactory(email_verified=False)
        api_client.force_authenticate(user=unverified)
        response = api_client.post(list_url(), {'original': _test_image_file()}, format='multipart')
        assert response.status_code == status.HTTP_403_FORBIDDEN
        mock_delay.assert_not_called()

    @patch('apps.media_tools.views.process_bg_removal.delay')
    def test_create_dispatches_task_and_returns_pending(self, mock_delay, api_client, user):
        api_client.force_authenticate(user=user)
        response = api_client.post(list_url(), {'original': _test_image_file()}, format='multipart')
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['status'] == 'pending'
        assert response.data['model_name'] == 'u2net'
        mock_delay.assert_called_once()

        preview = BackgroundRemovalPreview.objects.get(id=response.data['id'])
        assert preview.created_by == user

    @patch('apps.media_tools.views.process_bg_removal.delay')
    def test_create_accepts_custom_model(self, mock_delay, api_client, user):
        api_client.force_authenticate(user=user)
        response = api_client.post(
            list_url(),
            {'original': _test_image_file(), 'model_name': 'isnet-general-use', 'alpha_matting': 'true'},
            format='multipart',
        )
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['model_name'] == 'isnet-general-use'
        assert response.data['alpha_matting'] is True

    @patch('apps.media_tools.views.process_bg_removal.delay')
    def test_create_rejects_unknown_model(self, mock_delay, api_client, user):
        api_client.force_authenticate(user=user)
        response = api_client.post(
            list_url(),
            {'original': _test_image_file(), 'model_name': 'not-a-real-model'},
            format='multipart',
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        mock_delay.assert_not_called()


class TestRetrieveOwnership:
    @patch('apps.media_tools.views.process_bg_removal.delay')
    def test_owner_can_retrieve(self, mock_delay, api_client, user):
        api_client.force_authenticate(user=user)
        create_resp = api_client.post(list_url(), {'original': _test_image_file()}, format='multipart')
        preview_id = create_resp.data['id']

        response = api_client.get(detail_url(preview_id))
        assert response.status_code == status.HTTP_200_OK
        assert response.data['id'] == preview_id

    @patch('apps.media_tools.views.process_bg_removal.delay')
    def test_other_user_cannot_retrieve(self, mock_delay, api_client, user, db):
        api_client.force_authenticate(user=user)
        create_resp = api_client.post(list_url(), {'original': _test_image_file()}, format='multipart')
        preview_id = create_resp.data['id']

        other = UserFactory(email_verified=True)
        api_client.force_authenticate(user=other)
        response = api_client.get(detail_url(preview_id))
        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestReprocess:
    @patch('apps.media_tools.views.process_bg_removal.delay')
    def test_reprocess_accepts_json_and_resets_status(self, mock_delay, api_client, user):
        """Regression test: the reprocess action previously inherited the
        viewset's multipart-only parser_classes, so a JSON body (what the
        frontend actually sends) was rejected with a 415."""
        api_client.force_authenticate(user=user)
        create_resp = api_client.post(list_url(), {'original': _test_image_file()}, format='multipart')
        preview_id = create_resp.data['id']
        assert mock_delay.call_count == 1

        response = api_client.post(
            reprocess_url(preview_id),
            {'model_name': 'isnet-general-use', 'alpha_matting': True, 'foreground_threshold': 200},
            format='json',
        )
        assert response.status_code == status.HTTP_202_ACCEPTED
        assert response.data['status'] == 'pending'
        assert response.data['model_name'] == 'isnet-general-use'
        assert response.data['alpha_matting'] is True
        assert response.data['foreground_threshold'] == 200
        assert mock_delay.call_count == 2

    @patch('apps.media_tools.views.process_bg_removal.delay')
    def test_reprocess_rejects_out_of_range_threshold(self, mock_delay, api_client, user):
        api_client.force_authenticate(user=user)
        create_resp = api_client.post(list_url(), {'original': _test_image_file()}, format='multipart')
        preview_id = create_resp.data['id']

        response = api_client.post(
            reprocess_url(preview_id),
            {'foreground_threshold': 999},
            format='json',
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @patch('apps.media_tools.views.process_bg_removal.delay')
    def test_other_user_cannot_reprocess(self, mock_delay, api_client, user, db):
        api_client.force_authenticate(user=user)
        create_resp = api_client.post(list_url(), {'original': _test_image_file()}, format='multipart')
        preview_id = create_resp.data['id']

        other = UserFactory(email_verified=True)
        api_client.force_authenticate(user=other)
        response = api_client.post(reprocess_url(preview_id), {'model_name': 'u2net'}, format='json')
        assert response.status_code == status.HTTP_404_NOT_FOUND
