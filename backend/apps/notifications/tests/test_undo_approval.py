"""
A moderator can undo an approval made in haste: the item goes back to the queue and the
submitter loses what the approval gave them (contribution, reputation, BOM bonus, the notice).
"""
from unittest import mock

from rest_framework.test import APIClient

from apps.components.models import ProductComponent
from apps.notifications.models import Notification
from apps.users.models import PointsLedger

EMAIL_TASK = 'apps.users.tasks.notify_contribution_reviewed.delay'


def _client(user):
    api = APIClient()
    api.force_authenticate(user)
    return api


def test_undo_image_approval(moderator, user, product_factory, product_image_factory):
    image = product_image_factory(product=product_factory(), uploaded_by=user, is_approved=False)
    api = _client(moderator)
    with mock.patch(EMAIL_TASK):
        assert api.post(f'/api/product-images/{image.id}/approve/').status_code == 200
    user.refresh_from_db()
    assert (user.contribution_count, user.reputation_score) == (1, 10)
    assert Notification.objects.filter(recipient=user, category=Notification.Category.CONTENT_APPROVED).exists()

    resp = api.post(f'/api/product-images/{image.id}/unapprove/')
    assert resp.status_code == 200
    image.refresh_from_db()
    user.refresh_from_db()
    assert not image.is_approved
    assert (user.contribution_count, user.reputation_score) == (0, 0)
    assert not Notification.objects.filter(recipient=user).exists()
    # back in the queue, so it can now be rejected with feedback
    with mock.patch(EMAIL_TASK):
        assert api.post(f'/api/product-images/{image.id}/reject/', {'notes': 'Poor cut-out.'},
                        format='json').status_code == 204


def test_undo_needs_an_approved_item(moderator, product_factory, product_image_factory):
    image = product_image_factory(product=product_factory(), is_approved=False)
    assert _client(moderator).post(f'/api/product-images/{image.id}/unapprove/').status_code == 400


def test_only_moderators_can_undo(user, product_factory, schematic_factory):
    schematic = schematic_factory(product=product_factory(), is_approved=True)
    assert _client(user).post(f'/api/schematics/{schematic.id}/unapprove/').status_code == 403
    schematic.refresh_from_db()
    assert schematic.is_approved


def test_undo_product_approval_takes_back_the_bom_bonus(moderator, user_factory, product_factory, component_factory):
    creator = user_factory()
    product = product_factory(created_by=creator, is_approved=False)
    for _ in range(10):
        ProductComponent.objects.create(product=product, component=component_factory(), created_by=creator)
    api = _client(moderator)
    with mock.patch(EMAIL_TASK):
        assert api.post(f'/api/products/{product.id}/approve/').status_code == 200
    creator.refresh_from_db()
    assert creator.reputation_score == 10 + 20                        # contribution + 10-part BOM bonus

    assert api.post(f'/api/products/{product.id}/unapprove/').status_code == 200
    creator.refresh_from_db()
    product.refresh_from_db()
    assert (product.is_approved, product.bom_bonus_tier) == (False, 0)
    assert (creator.contribution_count, creator.reputation_score) == (0, 0)
    assert not PointsLedger.objects.filter(kind=PointsLedger.Kind.BOM_BONUS).exists()

    with mock.patch(EMAIL_TASK):                                      # approving again pays again, once
        api.post(f'/api/products/{product.id}/approve/')
    creator.refresh_from_db()
    assert creator.reputation_score == 30
