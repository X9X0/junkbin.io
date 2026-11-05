"""
A moderator's reason for a rejection reaches the submitter: the 'notes' sent
with reject/dismiss go into the email and the in-app notification.
"""
from unittest import mock

from rest_framework.test import APIClient

from apps.notifications.models import Notification

EMAIL_TASK = 'apps.users.tasks.notify_contribution_reviewed.delay'


def _client(user):
    api = APIClient()
    api.force_authenticate(user)
    return api


def test_product_reject_sends_feedback(moderator, user, product_factory):
    product = product_factory(is_approved=False, created_by=user)
    with mock.patch(EMAIL_TASK) as email:
        resp = _client(moderator).post(f'/api/products/{product.id}/reject/',
                                       {'notes': '  Photo shows a different model.  '}, format='json')
    assert resp.status_code == 204
    assert email.call_args.args[-1] == 'Photo shows a different model.'
    n = Notification.objects.get(recipient=user)
    assert n.category == Notification.Category.CONTENT_REJECTED
    assert n.body == 'Photo shows a different model.'


def test_reject_feedback_is_capped(moderator, user, product_factory):
    product = product_factory(is_approved=False, created_by=user)
    with mock.patch(EMAIL_TASK):
        _client(moderator).post(f'/api/products/{product.id}/reject/', {'notes': 'x' * 5000}, format='json')
    assert len(Notification.objects.get(recipient=user).body) == 2000


def test_recipe_reject_notifies_in_app(moderator, user):
    from apps.recipes.models import Recipe
    recipe = Recipe.objects.create(name='Bench supply', description='From a laptop brick',
                                   created_by=user, is_approved=False)
    with mock.patch(EMAIL_TASK):
        resp = _client(moderator).post(f'/api/recipes/{recipe.id}/reject/',
                                       {'notes': 'Add a parts list.'}, format='json')
    assert resp.status_code == 204
    n = Notification.objects.get(recipient=user)
    assert n.title == 'Your recipe "Bench supply" rejected' and n.body == 'Add a parts list.'


def test_product_request_dismiss_tells_the_requester(moderator, user):
    from apps.components.models import ProductRequest
    req = ProductRequest.objects.create(manufacturer='Onkyo', model_number='TX-SR507', requested_by=user)
    resp = _client(moderator).post(f'/api/product-requests/{req.id}/dismiss/',
                                   {'notes': 'Already listed as TX-SR507 (B).'}, format='json')
    assert resp.status_code == 200 and resp.data['status'] == 'dismissed'
    n = Notification.objects.get(recipient=user)
    assert n.body == 'Already listed as TX-SR507 (B).'


def test_anonymous_product_request_dismiss_notifies_nobody(moderator):
    from apps.components.models import ProductRequest
    req = ProductRequest.objects.create(manufacturer='Onkyo', model_number='TX-SR507')
    assert _client(moderator).post(f'/api/product-requests/{req.id}/dismiss/').status_code == 200
    assert not Notification.objects.exists()


def test_reviewing_your_own_item_notifies_nobody(moderator, product_factory):
    """Imports are credited to the account that ran them; reviewing them must not mail that account."""
    product = product_factory(is_approved=False, created_by=moderator)
    with mock.patch('utils.email.send_contribution_rejected_email') as email:
        resp = _client(moderator).post(f'/api/products/{product.id}/reject/', {'notes': 'Wrong photo.'}, format='json')
    assert resp.status_code == 204
    email.assert_not_called()
    assert not Notification.objects.exists()
