"""
A product page lists the other revisions of its model (each its own product) so the page
can offer them in one selector.
"""
import pytest
from rest_framework.test import APIClient

from apps.products.serializers import revision_key

pytestmark = pytest.mark.django_db


def test_revision_key_orders_like_a_board_house():
    revisions = ['1.1', '0B', '', '10', '3.0C', '3.00', '1.0', '0A', '3.0B', '2.0']
    assert sorted(revisions, key=revision_key) == ['', '0A', '0B', '1.0', '1.1', '2.0', '3.00', '3.0B', '3.0C', '10']


def test_detail_lists_approved_sibling_revisions_in_order(product_factory, django_user_model):
    base = product_factory(manufacturer='MSI', model_number='MS-9902', revision='', is_approved=True)
    product_factory(manufacturer='MSI', model_number='MS-9902', revision='1.0', is_approved=True)
    rev0b = product_factory(manufacturer='msi', model_number='ms-9902', revision='0B', is_approved=True)   # case differs
    pending = product_factory(manufacturer='MSI', model_number='MS-9902', revision='1.1', is_approved=False)
    product_factory(manufacturer='MSI', model_number='MS-9903', revision='1.0', is_approved=True)         # another model
    api = APIClient()

    resp = api.get(f'/api/products/{rev0b.pk}/')
    assert resp.status_code == 200
    revisions = resp.data['revisions']
    assert [r['revision'] for r in revisions] == ['', '0B', '1.0']
    assert revisions[0]['slug'] == base.slug and revisions[1]['id'] == str(rev0b.pk)
    assert {'id', 'slug', 'revision', 'region', 'region_display', 'component_count', 'schematic_count'} <= set(revisions[0])

    staff = django_user_model.objects.create_user(username='mod', email='mod@example.com', password='x', is_staff=True)
    api.force_authenticate(staff)
    resp = api.get(f'/api/products/{pending.pk}/')
    assert [r['revision'] for r in resp.data['revisions']] == ['', '0B', '1.0', '1.1']


def test_detail_has_no_revisions_when_the_model_stands_alone(product_factory):
    alone = product_factory(manufacturer='Fender', model_number='Twin Reverb', revision='', is_approved=True)
    resp = APIClient().get(f'/api/products/{alone.pk}/')
    assert resp.status_code == 200 and resp.data['revisions'] == []
