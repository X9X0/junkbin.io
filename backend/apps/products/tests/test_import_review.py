"""
Tests for import batch review (apps.products.import_review and the import-review API).
"""
import pytest
from rest_framework.test import APIClient

from apps.products import import_review
from apps.products.models import ImportReview, Product

pytestmark = pytest.mark.django_db


@pytest.fixture
def moderator(user_factory):
    return user_factory(is_staff=True)


def _batch(product_factory, n=3, tag='norway-schem'):
    return [product_factory(import_source=f'{tag}:p{i}', is_approved=False) for i in range(n)]


def _api(user):
    api = APIClient()
    api.force_authenticate(user)
    return api


def test_gate_requires_every_item_reviewed_when_batch_is_small(product_factory, moderator, monkeypatch):
    products = _batch(product_factory, 3)
    api = _api(moderator)
    stats = {s['batch']: s for s in api.get('/api/import-review/').data}
    assert stats['norway-schem']['total'] == 3 and stats['norway-schem']['target'] == 3
    assert not stats['norway-schem']['can_approve']
    assert api.post('/api/import-review/approve/', {'batch': 'norway-schem'}, format='json').status_code == 400

    items = api.get('/api/import-review/next/', {'batch': 'norway-schem', 'n': 10}).data
    assert {i['id'] for i in items} == {str(p.pk) for p in products}
    for i in items:
        api.post('/api/import-review/verdict/', {'batch': 'norway-schem', 'object_id': i['id'],
                                                 'verdict': 'correct'}, format='json')
    assert api.get('/api/import-review/next/', {'batch': 'norway-schem'}).data == []   # nothing left to draw
    resp = api.post('/api/import-review/approve/', {'batch': 'norway-schem'}, format='json')
    assert resp.status_code == 200 and resp.data['products'] == 3
    assert Product.objects.filter(is_approved=True).count() == 3


def test_a_flag_blocks_approval_until_resolved(product_factory, moderator):
    products = _batch(product_factory, 2)
    api = _api(moderator)
    api.post('/api/import-review/verdict/', {'batch': 'norway-schem', 'object_id': str(products[0].pk),
                                             'verdict': 'flagged', 'note': 'wrong revision'}, format='json')
    api.post('/api/import-review/verdict/', {'batch': 'norway-schem', 'object_id': str(products[1].pk),
                                             'verdict': 'correct'}, format='json')
    flagged = api.get('/api/import-review/flagged/', {'batch': 'norway-schem'}).data
    assert flagged[0]['note'] == 'wrong revision'
    assert not import_review.stats('norway-schem')['can_approve']
    api.post('/api/import-review/verdict/', {'batch': 'norway-schem', 'object_id': str(products[0].pk),
                                             'verdict': 'correct'}, format='json')    # fixed, re-reviewed
    assert import_review.stats('norway-schem')['can_approve']


def test_items_outside_the_batch_are_refused(product_factory, moderator):
    other = product_factory(import_source='')
    resp = _api(moderator).post('/api/import-review/verdict/', {'batch': 'norway-schem', 'object_id': str(other.pk),
                                                                'verdict': 'correct'}, format='json')
    assert resp.status_code == 400 and not ImportReview.objects.exists()


def test_only_moderators_and_force_only_for_superusers(product_factory, user_factory, moderator):
    _batch(product_factory, 2)
    assert _api(user_factory()).get('/api/import-review/').status_code == 403
    assert _api(moderator).post('/api/import-review/approve/', {'batch': 'norway-schem', 'force': True},
                                format='json').status_code == 400
    admin = user_factory(is_staff=True, is_superuser=True)
    assert _api(admin).post('/api/import-review/approve/', {'batch': 'norway-schem', 'force': True},
                            format='json').status_code == 200
