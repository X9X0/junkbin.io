"""
Tests for the component bulk-edit admin views.
"""
import pytest
from django.urls import reverse

pytestmark = pytest.mark.django_db


@pytest.fixture
def admin_user(user_factory):
    """A superuser with a real, persisted password.

    Superuser (not just is_staff) because some of these views redirect to
    the real Component changelist, which - like any ModelAdmin view -
    needs full view permission for a non-superuser.

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


def _select(client, admin_user, component_ids):
    """Populate the session with a selection, the way the admin action does."""
    client.force_login(admin_user)
    session = client.session
    session['bulk_edit_component_ids'] = [str(cid) for cid in component_ids]
    session.save()


class TestBulkEditComponentsView:
    def test_requires_staff(self, client, user, component_factory):
        component = component_factory()
        client.force_login(user)
        response = client.get(reverse('admin-component-bulk-edit'))
        assert response.status_code in (302, 403)

    def test_no_selection_redirects_with_warning(self, client, admin_user):
        client.force_login(admin_user)
        response = client.get(reverse('admin-component-bulk-edit'), follow=True)
        assert response.status_code == 200
        messages = list(response.context['messages'])
        assert any('No components selected' in str(m) for m in messages)

    def test_shows_selected_components_and_type_counts(self, client, admin_user, component_factory):
        r1 = component_factory(component_type='resistor')
        r2 = component_factory(component_type='resistor')
        c1 = component_factory(component_type='capacitor')
        _select(client, admin_user, [r1.id, r2.id, c1.id])

        response = client.get(reverse('admin-component-bulk-edit'))

        assert response.status_code == 200
        assert response.context['total_count'] == 3
        counts = {row['component_type']: row['count'] for row in response.context['type_counts']}
        assert counts == {'resistor': 2, 'capacitor': 1}

    def test_editable_fields_exclude_identity_and_json_fields(self, client, admin_user, component_factory):
        component = component_factory()
        _select(client, admin_user, [component.id])

        response = client.get(reverse('admin-component-bulk-edit'))

        field_names = {f['name'] for f in response.context['fields']}
        assert 'package_type' in field_names
        assert 'component_type' in field_names
        assert 'is_verified' in field_names
        for excluded in ('id', 'part_number', 'manufacturer', 'specifications',
                          'manufacturer_aliases', 'alternative_part_numbers', 'cross_references'):
            assert excluded not in field_names


class TestBulkEditComponentsAction:
    def test_sets_text_field_on_all_selected(self, client, admin_user, component_factory):
        components = [component_factory(component_type='resistor', package_type='') for _ in range(3)]
        _select(client, admin_user, [c.id for c in components])

        response = client.post(
            reverse('admin-component-bulk-edit-action'),
            {'field': 'package_type', 'value': '0402'},
        )

        assert response.status_code == 302
        for c in components:
            c.refresh_from_db()
            assert c.package_type == '0402'

    def test_sets_boolean_field(self, client, admin_user, component_factory):
        component = component_factory(is_verified=False)
        _select(client, admin_user, [component.id])

        client.post(reverse('admin-component-bulk-edit-action'), {'field': 'is_verified', 'value': 'true'})

        component.refresh_from_db()
        assert component.is_verified is True

    def test_rejects_choice_field_with_invalid_value(self, client, admin_user, component_factory):
        component = component_factory(component_type='resistor')
        _select(client, admin_user, [component.id])

        response = client.post(
            reverse('admin-component-bulk-edit-action'),
            {'field': 'component_type', 'value': 'not_a_real_type'},
            follow=True,
        )

        component.refresh_from_db()
        assert component.component_type == 'resistor'
        messages = list(response.context['messages'])
        assert any('not a valid choice' in str(m) for m in messages)

    def test_rejects_excluded_field(self, client, admin_user, component_factory):
        component = component_factory(manufacturer='Sony')
        _select(client, admin_user, [component.id])

        response = client.post(
            reverse('admin-component-bulk-edit-action'),
            {'field': 'manufacturer', 'value': 'Panasonic'},
            follow=True,
        )

        component.refresh_from_db()
        assert component.manufacturer == 'Sony'
        messages = list(response.context['messages'])
        assert any('cannot be bulk-edited' in str(m) for m in messages)

    def test_skips_components_already_at_target_value(self, client, admin_user, component_factory):
        already_set = component_factory(package_type='0402')
        needs_update = component_factory(package_type='')
        _select(client, admin_user, [already_set.id, needs_update.id])

        response = client.post(
            reverse('admin-component-bulk-edit-action'),
            {'field': 'package_type', 'value': '0402'},
            follow=True,
        )

        messages = list(response.context['messages'])
        assert any('1 component(s)' in str(m) and '1 already had' in str(m) for m in messages)

    def test_logs_audit_entry_per_component(self, client, admin_user, component_factory):
        from apps.users.models import AdminAuditLog

        component = component_factory(package_type='')
        _select(client, admin_user, [component.id])

        client.post(reverse('admin-component-bulk-edit-action'), {'field': 'package_type', 'value': '0402'})

        log = AdminAuditLog.objects.get(
            action_type=AdminAuditLog.ActionType.COMPONENT_BULK_EDITED,
            target_id=str(component.id),
        )
        assert log.details == {'field': 'package_type', 'old_value': '', 'new_value': '0402'}

    def test_clears_session_selection_after_apply(self, client, admin_user, component_factory):
        component = component_factory(package_type='')
        _select(client, admin_user, [component.id])

        client.post(reverse('admin-component-bulk-edit-action'), {'field': 'package_type', 'value': '0402'})

        assert 'bulk_edit_component_ids' not in client.session

    def test_get_request_redirects_without_applying(self, client, admin_user, component_factory):
        component = component_factory(package_type='')
        _select(client, admin_user, [component.id])

        client.get(reverse('admin-component-bulk-edit-action'))

        component.refresh_from_db()
        assert component.package_type == ''
