"""
Points policy.

Discovery points reward growing the catalogue by searching. They are kept in
User.discovery_points, never in reputation_score, so they can't unlock
trusted status (which skips moderation):
  * +1 when a search adds a part the catalogue didn't have (max 10 a day)
  * +2 when a moderator creates the product someone asked for
  * signed-out visitors earn the same points against their browser session;
    signing in with a verified email within CLAIM_DAYS claims them, +5 bonus

The real reward is a product with a meaningful BOM. When an approved product's
creator has added at least 10 distinct, undisputed components, reputation
(which does count toward trust - a moderator approved the product) rises by
tier, paid once per tier: 10+ -> 20, 25+ -> 40, 50+ -> 75 in total.
Imported content (created by staff/superusers) earns nothing.
"""
from datetime import timedelta

from django.db import transaction
from django.db.models import F, Sum
from django.utils import timezone

DISCOVERY_POINTS = 1
DISCOVERY_DAILY_CAP = 10
REQUEST_FULFILLED_POINTS = 2
SIGNUP_BONUS = 5
CLAIM_DAYS = 7
BOM_TIERS = [(50, 75), (25, 40), (10, 20)]          # (distinct components, total bonus)


def _ledger():
    from .models import PointsLedger
    return PointsLedger


def _session_key(request):
    if request is None or not hasattr(request, 'session'):
        return ''
    if not request.session.session_key:
        request.session.save()
    return request.session.session_key or ''


def award_discovery(request, component):
    """A search added `component`. Returns points awarded (0 when capped)."""
    PointsLedger = _ledger()
    user = request.user if request and request.user.is_authenticated else None
    since = timezone.now() - timedelta(days=1)
    if user:
        if user.is_staff:
            return 0
        recent = PointsLedger.objects.filter(user=user, kind=PointsLedger.Kind.DISCOVERY, created_at__gte=since)
    else:
        key = _session_key(request)
        if not key:
            return 0
        recent = PointsLedger.objects.filter(session_key=key, user__isnull=True,
                                             kind=PointsLedger.Kind.DISCOVERY, created_at__gte=since)
    if recent.count() >= DISCOVERY_DAILY_CAP:
        return 0
    PointsLedger.objects.create(user=user, session_key='' if user else _session_key(request),
                                kind=PointsLedger.Kind.DISCOVERY, points=DISCOVERY_POINTS,
                                object_ref=f'component:{component.pk}', claimed_at=timezone.now() if user else None)
    if user:
        type(user).objects.filter(pk=user.pk).update(discovery_points=F('discovery_points') + DISCOVERY_POINTS)
    return DISCOVERY_POINTS


def award_request_fulfilled(product_request):
    """A moderator created the product a searcher asked for."""
    PointsLedger = _ledger()
    user = product_request.requested_by
    if user is None and not product_request.session_key:
        return 0
    PointsLedger.objects.create(user=user, session_key='' if user else product_request.session_key,
                                kind=PointsLedger.Kind.REQUEST_FULFILLED, points=REQUEST_FULFILLED_POINTS,
                                object_ref=f'product_request:{product_request.pk}',
                                claimed_at=timezone.now() if user else None)
    if user:
        type(user).objects.filter(pk=user.pk).update(discovery_points=F('discovery_points') + REQUEST_FULFILLED_POINTS)
    return REQUEST_FULFILLED_POINTS


def pending_for_session(session_key):
    PointsLedger = _ledger()
    if not session_key:
        return 0
    return PointsLedger.objects.filter(
        session_key=session_key, user__isnull=True,
        created_at__gte=timezone.now() - timedelta(days=CLAIM_DAYS),
    ).aggregate(total=Sum('points'))['total'] or 0


@transaction.atomic
def claim_session_points(user, session_key):
    """Move a browser's unclaimed points to `user` (verified email required). Returns points claimed."""
    PointsLedger = _ledger()
    if not user.email_verified or not session_key:
        return 0
    rows = PointsLedger.objects.select_for_update().filter(
        session_key=session_key, user__isnull=True,
        created_at__gte=timezone.now() - timedelta(days=CLAIM_DAYS))
    total = rows.aggregate(total=Sum('points'))['total'] or 0
    if not total:
        return 0
    rows.update(user=user, claimed_at=timezone.now())
    bonus_given = PointsLedger.objects.filter(user=user, kind=PointsLedger.Kind.SIGNUP_BONUS).exists()
    if not bonus_given:
        PointsLedger.objects.create(user=user, kind=PointsLedger.Kind.SIGNUP_BONUS, points=SIGNUP_BONUS,
                                    claimed_at=timezone.now())
        total += SIGNUP_BONUS
    type(user).objects.filter(pk=user.pk).update(discovery_points=F('discovery_points') + total)
    return total


def bom_tier(count):
    for threshold, _ in BOM_TIERS:
        if count >= threshold:
            return threshold
    return 0


def tier_bonus(tier):
    return next((bonus for threshold, bonus in BOM_TIERS if threshold == tier), 0)


@transaction.atomic
def award_bom_bonus(product):
    """Pay the creator for BOM tiers this approved product has newly reached. Returns reputation added."""
    from apps.products.models import Product
    product = Product.objects.select_for_update().get(pk=product.pk)
    creator = product.created_by
    if not product.is_approved or creator is None or creator.is_staff or creator.is_superuser:
        return 0
    count = (product.product_components.filter(created_by=creator, vote_score__gte=0)
             .values('component').distinct().count())
    tier = bom_tier(count)
    if tier <= product.bom_bonus_tier:
        return 0
    owed = tier_bonus(tier) - tier_bonus(product.bom_bonus_tier)
    product.bom_bonus_tier = tier
    product.save(update_fields=['bom_bonus_tier'])
    _ledger().objects.create(user=creator, kind=_ledger().Kind.BOM_BONUS, points=owed,
                             counts_toward_reputation=True, object_ref=f'product:{product.pk}:tier{tier}',
                             claimed_at=timezone.now())
    creator.reputation_score += owed
    creator._check_trusted_status()
    creator.save(update_fields=['reputation_score', 'is_trusted'])
    return owed
