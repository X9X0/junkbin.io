"""The junkbin list's filters answer bad input with 400, not a server error."""
import pytest
from rest_framework.test import APIClient

pytestmark = pytest.mark.django_db


def test_object_id_must_be_a_uuid(product_factory):
    product = product_factory()
    api = APIClient()
    assert api.get('/api/junkbin/', {'content_type': 'product', 'object_id': 'msi-ms-6743-200'}).status_code == 400
    assert api.get('/api/junkbin/', {'content_type': 'product', 'object_id': str(product.pk)}).status_code == 200
