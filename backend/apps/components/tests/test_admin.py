"""
Tests for ComponentAdmin: the product (BOM) filter and the bulk-edit action.
"""
import pytest
from django.contrib.admin.sites import site
from django.urls import reverse

from apps.components.models import Component

pytestmark = pytest.mark.django_db


@pytest.fixture
def admin_user(user_factory):
    """A superuser, matching how real admin accounts are provisioned in this
    project - plain is_staff=True isn't enough to pass Django admin's
    changelist permission checks for a non-superuser.

    UserFactory sets `skip_postgeneration_save`, so its `set_password`
    post-generation hook never gets flushed to the DB - the returned object
    has a password hash in memory but an empty one in the row. That's fine
    for factory-only tests, but here it breaks session auth: force_login()
    computes _auth_user_hash from the in-memory password, while every
    later request re-fetches the user from the DB and recomputes the hash
    from the (empty) stored password, so Django treats it as a stale
    session and silently logs the user back out. Re-saving fixes it.
    """
    user = user_factory(is_staff=True, is_superuser=True)
    user.set_password('testpass123')
    user.save()
    return user


class TestComponentProductFilter:
    def test_filters_to_components_used_in_one_product(
        self, client, admin_user, product_factory, component_factory, product_component_factory,
    ):
        product_a = product_factory()
        product_b = product_factory()
        in_a = component_factory()
        in_b = component_factory()
        product_component_factory(product=product_a, component=in_a)
        product_component_factory(product=product_b, component=in_b)

        client.force_login(admin_user)
        response = client.get(reverse('admin:components_component_changelist'), {'product': str(product_a.id)})

        result_ids = {c.id for c in response.context['cl'].result_list}
        assert result_ids == {in_a.id}

    def test_no_filter_shows_all_components(
        self, client, admin_user, product_factory, component_factory, product_component_factory,
    ):
        product = product_factory()
        in_product = component_factory()
        not_in_product = component_factory()
        product_component_factory(product=product, component=in_product)

        client.force_login(admin_user)
        response = client.get(reverse('admin:components_component_changelist'))

        result_ids = {c.id for c in response.context['cl'].result_list}
        assert {in_product.id, not_in_product.id} <= result_ids


class TestBulkEditFieldAction:
    def test_action_redirects_to_bulk_edit_with_selection_in_session(
        self, client, admin_user, component_factory,
    ):
        components = [component_factory() for _ in range(2)]
        client.force_login(admin_user)

        response = client.post(reverse('admin:components_component_changelist'), {
            'action': 'bulk_edit_field',
            '_selected_action': [str(c.id) for c in components],
        })

        assert response.status_code == 302
        assert response.url == reverse('admin-component-bulk-edit')
        assert set(client.session['bulk_edit_component_ids']) == {str(c.id) for c in components}

    def test_action_registered_on_admin(self):
        admin_instance = site._registry[Component]
        assert 'bulk_edit_field' in admin_instance.actions
