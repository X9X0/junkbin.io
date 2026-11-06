"""A category a moderator sets (the review viewer's 'Wrong category: fix it') survives re-imports."""
from rest_framework.test import APIClient

from apps.products.management.commands.import_board_bom import Command


def _patch(user, product, data):
    api = APIClient()
    api.force_authenticate(user)
    return api.patch(f'/api/products/{product.id}/', data, format='json')


def test_moderator_category_fix_is_kept_by_imports(moderator, product_factory):
    product = product_factory(category='laptop', is_approved=True, model_number='ET2311I')
    resp = _patch(moderator, product, {'category': 'desktop', 'subcategory': 'All-in-One'})
    assert resp.status_code == 200
    product.refresh_from_db()
    assert (product.category, product.subcategory, product.category_locked) == ('desktop', 'All-in-One', True)

    Command.update_identity(product, {'manufacturer': product.manufacturer, 'model_number': 'ET2311I',
                                      'revision': product.revision, 'description': 'Re-imported.',
                                      'category': 'laptop', 'subcategory': ''})
    product.refresh_from_db()
    assert (product.category, product.subcategory) == ('desktop', 'All-in-One')
    assert product.description == 'Re-imported.'                      # everything else still updates


def test_other_edits_leave_the_category_to_imports(moderator, product_factory):
    product = product_factory(category='laptop', is_approved=True)
    assert _patch(moderator, product, {'description': 'Clearer.'}).status_code == 200
    product.refresh_from_db()
    assert not product.category_locked
