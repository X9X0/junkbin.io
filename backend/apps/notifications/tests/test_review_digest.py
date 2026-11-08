"""
Approval/rejection emails are batched: reviewing queues a ReviewEmail, and every few minutes
each user gets one email listing all of theirs (keeps the mail provider's limits free for
sign-up mail).
"""
from django.core import mail
from rest_framework.test import APIClient

from apps.notifications.models import ReviewEmail
from apps.notifications.tasks import send_review_email_digests


def _client(user):
    api = APIClient()
    api.force_authenticate(user)
    return api


def test_reviews_are_queued_not_mailed(moderator, user, product_factory, django_capture_on_commit_callbacks):
    products = [product_factory(is_approved=False, created_by=user) for _ in range(3)]
    api = _client(moderator)
    api.post(f'/api/products/{products[0].id}/approve/')
    api.post(f'/api/products/{products[1].id}/approve/')
    api.post(f'/api/products/{products[2].id}/reject/', {'notes': 'Duplicate.'}, format='json')
    assert len(mail.outbox) == 0
    assert ReviewEmail.objects.filter(user=user, sent_at__isnull=True).count() == 3

    assert send_review_email_digests() == 1
    assert len(mail.outbox) == 1
    msg = mail.outbox[0]
    assert msg.to == [user.email]
    assert '2 approved, 1 need attention' in msg.subject
    assert 'Duplicate.' in msg.body
    assert not ReviewEmail.objects.filter(sent_at__isnull=True).exists()

    assert send_review_email_digests() == 0          # nothing new: nothing sent
    assert len(mail.outbox) == 1


def test_one_email_per_user(moderator, user_factory, product_factory):
    a, b = user_factory(), user_factory()
    api = _client(moderator)
    for owner in (a, a, b):
        api.post(f'/api/products/{product_factory(is_approved=False, created_by=owner).id}/approve/')
    assert send_review_email_digests() == 2
    assert sorted(m.to[0] for m in mail.outbox) == sorted([a.email, b.email])


def test_undo_withdraws_the_queued_approval_email(moderator, user, product_factory, product_image_factory):
    image = product_image_factory(product=product_factory(), uploaded_by=user, is_approved=False)
    api = _client(moderator)
    api.post(f'/api/product-images/{image.id}/approve/')
    assert ReviewEmail.objects.filter(user=user, approved=True).count() == 1
    api.post(f'/api/product-images/{image.id}/unapprove/')
    assert not ReviewEmail.objects.exists()
    assert send_review_email_digests() == 0


def test_email_preferences_still_respected(moderator, user, product_factory):
    user.preferences = {'email_notifications': False}
    user.save()
    _client(moderator).post(f'/api/products/{product_factory(is_approved=False, created_by=user).id}/approve/')
    assert not ReviewEmail.objects.exists()
