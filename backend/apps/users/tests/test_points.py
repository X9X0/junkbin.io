"""
Tests for the points policy (apps.users.points).
"""
from datetime import timedelta
from unittest.mock import MagicMock

import pytest
from django.contrib.sessions.backends.db import SessionStore
from django.utils import timezone

from apps.components.models import ProductComponent
from apps.users import points
from apps.users.models import PointsLedger

pytestmark = pytest.mark.django_db


def _request(user=None, session=None):
    req = MagicMock()
    req.user = user or MagicMock(is_authenticated=False)
    req.session = session or SessionStore()
    return req


def test_discovery_points_capped_and_kept_out_of_reputation(user_factory, component_factory):
    user = user_factory()
    for _ in range(points.DISCOVERY_DAILY_CAP + 3):
        points.award_discovery(_request(user), component_factory())
    user.refresh_from_db()
    assert user.discovery_points == points.DISCOVERY_DAILY_CAP
    assert user.reputation_score == 0 and not user.is_trusted


def test_anonymous_points_claimed_with_bonus_after_verification(user_factory, component_factory):
    session = SessionStore()
    for _ in range(3):
        points.award_discovery(_request(session=session), component_factory())
    key = session.session_key
    assert points.pending_for_session(key) == 3

    unverified = user_factory(email_verified=False)
    assert points.claim_session_points(unverified, key) == 0          # verified email required

    user = user_factory(email_verified=True)
    assert points.claim_session_points(user, key) == 3 + points.SIGNUP_BONUS
    user.refresh_from_db()
    assert user.discovery_points == 3 + points.SIGNUP_BONUS
    assert points.claim_session_points(user, key) == 0                # nothing left to claim


def test_old_anonymous_points_expire(user_factory, component_factory):
    session = SessionStore()
    points.award_discovery(_request(session=session), component_factory())
    PointsLedger.objects.update(created_at=timezone.now() - timedelta(days=points.CLAIM_DAYS + 1))
    assert points.claim_session_points(user_factory(email_verified=True), session.session_key) == 0


def _bom(product, creator, n, component_factory):
    for _ in range(n):
        ProductComponent.objects.create(product=product, component=component_factory(), created_by=creator)


def test_bom_bonus_paid_once_per_tier(user_factory, product_factory, component_factory):
    creator = user_factory()
    product = product_factory(created_by=creator, is_approved=True)
    _bom(product, creator, 9, component_factory)
    creator.refresh_from_db()
    assert creator.reputation_score == 0                              # below 10 components: nothing
    _bom(product, creator, 1, component_factory)                      # 10th component crosses the tier
    creator.refresh_from_db()
    assert creator.reputation_score == 20
    _bom(product, creator, 15, component_factory)                     # 25 components
    creator.refresh_from_db()
    assert creator.reputation_score == 40                             # tier total, not 20 + 40
    assert points.award_bom_bonus(product) == 0                       # paid once


def test_unapproved_product_earns_nothing_until_approved(user_factory, product_factory, component_factory):
    creator = user_factory()
    product = product_factory(created_by=creator, is_approved=False)
    _bom(product, creator, 12, component_factory)
    creator.refresh_from_db()
    assert creator.reputation_score == 0
    product.is_approved = True
    product.save(update_fields=['is_approved'])
    assert points.award_bom_bonus(product) == 20


def test_imports_by_staff_earn_nothing(user_factory, product_factory, component_factory):
    staff = user_factory(is_staff=True)
    product = product_factory(created_by=staff, is_approved=True)
    _bom(product, staff, 12, component_factory)
    staff.refresh_from_db()
    assert staff.reputation_score == 0


def test_disputed_rows_and_other_peoples_rows_dont_count(user_factory, product_factory, component_factory):
    creator, other = user_factory(), user_factory()
    product = product_factory(created_by=creator, is_approved=True)
    _bom(product, other, 10, component_factory)                       # someone else's rows
    _bom(product, creator, 9, component_factory)
    ProductComponent.objects.filter(product=product, created_by=creator).update(vote_score=-1)
    _bom(product, creator, 1, component_factory)
    creator.refresh_from_db()
    assert creator.reputation_score == 0
