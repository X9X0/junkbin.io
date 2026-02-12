"""
Tests for product comments API.
"""
import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.products.models import ProductComment
from apps.products.tests.factories import ProductFactory
from apps.users.tests.factories import UserFactory


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def product(db):
    return ProductFactory(approved=True)


@pytest.fixture
def user(db):
    return UserFactory(email_verified=True)


@pytest.fixture
def moderator(db):
    return UserFactory(moderator=True, email_verified=True)


def comments_url(product_id):
    return reverse('product-comments', kwargs={'pk': product_id})


def comment_detail_url(product_id, comment_id):
    return reverse('product-comment-detail', kwargs={'pk': product_id, 'comment_id': comment_id})


class TestListComments:
    """Tests for GET /api/products/{id}/comments/"""

    def test_list_comments_unauthenticated(self, api_client, product):
        """Anyone can read comments."""
        comment = ProductComment.objects.create(
            product=product,
            author=product.created_by,
            content='Great teardown!'
        )
        response = api_client.get(comments_url(product.id))
        assert response.status_code == status.HTTP_200_OK
        assert response.data['count'] == 1
        assert response.data['results'][0]['content'] == 'Great teardown!'
        assert response.data['results'][0]['author']['username'] == product.created_by.username

    def test_list_comments_ordered_by_newest(self, api_client, product):
        """Comments are ordered newest first."""
        c1 = ProductComment.objects.create(product=product, author=product.created_by, content='First')
        c2 = ProductComment.objects.create(product=product, author=product.created_by, content='Second')
        response = api_client.get(comments_url(product.id))
        assert response.data['results'][0]['content'] == 'Second'
        assert response.data['results'][1]['content'] == 'First'

    def test_list_comments_empty(self, api_client, product):
        """Empty product returns empty list."""
        response = api_client.get(comments_url(product.id))
        assert response.status_code == status.HTTP_200_OK
        assert response.data['count'] == 0


class TestCreateComment:
    """Tests for POST /api/products/{id}/comments/"""

    def test_create_comment_authenticated(self, api_client, product, user):
        """Verified user can create a comment."""
        api_client.force_authenticate(user=user)
        response = api_client.post(
            comments_url(product.id),
            {'content': 'This is very helpful!'}
        )
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['content'] == 'This is very helpful!'
        assert response.data['author']['username'] == user.username
        assert ProductComment.objects.filter(product=product).count() == 1

    def test_create_comment_unauthenticated(self, api_client, product):
        """Unauthenticated user cannot create a comment."""
        response = api_client.post(
            comments_url(product.id),
            {'content': 'Should fail'}
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_create_comment_empty_content(self, api_client, product, user):
        """Empty content is rejected."""
        api_client.force_authenticate(user=user)
        response = api_client.post(
            comments_url(product.id),
            {'content': ''}
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_create_comment_unverified_email(self, api_client, product, db):
        """Unverified user cannot create a comment."""
        unverified = UserFactory(email_verified=False)
        api_client.force_authenticate(user=unverified)
        response = api_client.post(
            comments_url(product.id),
            {'content': 'Should fail'}
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN


class TestDeleteComment:
    """Tests for DELETE /api/products/{id}/comments/{comment_id}/"""

    def test_delete_own_comment(self, api_client, product, user):
        """User can delete their own comment."""
        comment = ProductComment.objects.create(
            product=product, author=user, content='My comment'
        )
        api_client.force_authenticate(user=user)
        response = api_client.delete(comment_detail_url(product.id, comment.id))
        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not ProductComment.objects.filter(pk=comment.id).exists()

    def test_cannot_delete_others_comment(self, api_client, product, user):
        """User cannot delete another user's comment."""
        other = UserFactory()
        comment = ProductComment.objects.create(
            product=product, author=other, content='Not yours'
        )
        api_client.force_authenticate(user=user)
        response = api_client.delete(comment_detail_url(product.id, comment.id))
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert ProductComment.objects.filter(pk=comment.id).exists()

    def test_moderator_can_delete_any_comment(self, api_client, product, moderator):
        """Moderator can delete any comment."""
        other = UserFactory()
        comment = ProductComment.objects.create(
            product=product, author=other, content='Bad comment'
        )
        api_client.force_authenticate(user=moderator)
        response = api_client.delete(comment_detail_url(product.id, comment.id))
        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not ProductComment.objects.filter(pk=comment.id).exists()

    def test_delete_unauthenticated(self, api_client, product):
        """Unauthenticated user cannot delete a comment."""
        comment = ProductComment.objects.create(
            product=product, author=product.created_by, content='Test'
        )
        response = api_client.delete(comment_detail_url(product.id, comment.id))
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestCommentCount:
    """Tests for comment_count on product serializers."""

    def test_comment_count_in_product_detail(self, api_client, product):
        """Product detail includes comment_count."""
        ProductComment.objects.create(product=product, author=product.created_by, content='One')
        ProductComment.objects.create(product=product, author=product.created_by, content='Two')
        response = api_client.get(reverse('product-detail', kwargs={'pk': product.id}))
        assert response.status_code == status.HTTP_200_OK
        assert response.data['comment_count'] == 2
