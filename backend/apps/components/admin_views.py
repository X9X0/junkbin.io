"""
Bulk-edit view for components: apply one field/value change across many
selected Component records at once (e.g. "set package_type to 0805" for
every resistor selected in the admin change list).

Editable fields are discovered generically from the model rather than
hardcoded one at a time, so this covers most Component fields without
per-field code. A denylist excludes:
  - identity fields (part_number, manufacturer) - mass-renaming these can
    collide with the (manufacturer, part_number) uniqueness constraint and
    rarely makes sense as a "set them all to X" operation
  - JSON/relational fields (specifications, manufacturer_aliases,
    alternative_part_numbers, cross_references) - these need merge-vs-
    overwrite semantics this simple "set field to value" tool doesn't have
  - system-managed fields (id, usage_count, search_vector, created_by,
    created_at, updated_at)
"""
from django.contrib import admin, messages
from django.contrib.admin.views.decorators import staff_member_required
from django.db import models as db_models
from django.shortcuts import redirect, render
from django.urls import reverse

from apps.users.models import AdminAuditLog

from .models import Component

EXCLUDED_BULK_FIELDS = {
    'id', 'part_number', 'manufacturer', 'manufacturer_aliases',
    'specifications', 'alternative_part_numbers', 'cross_references',
    'usage_count', 'search_vector', 'created_by', 'created_at', 'updated_at',
}

MAX_PREVIEW_ROWS = 500


def _bulk_editable_fields():
    fields = []
    for f in Component._meta.get_fields():
        if f.name in EXCLUDED_BULK_FIELDS:
            continue
        if not getattr(f, 'concrete', False) or f.many_to_many or f.auto_created:
            continue
        fields.append(f)
    return fields


def _field_widget_kind(field):
    if field.choices:
        return 'choice'
    if isinstance(field, db_models.BooleanField):
        return 'boolean'
    if isinstance(field, db_models.TextField):
        return 'textarea'
    return 'text'


def _coerce_value(field, raw_value):
    """Convert the submitted string into the right Python type for `field`.

    Raises ValueError with a user-facing message on invalid input.
    """
    if isinstance(field, db_models.BooleanField):
        if raw_value not in ('true', 'false'):
            raise ValueError('Choose True or False.')
        return raw_value == 'true'
    if field.choices:
        valid = {choice for choice, _label in field.choices}
        if raw_value not in valid:
            raise ValueError(f'"{raw_value}" is not a valid choice for {field.verbose_name}.')
        return raw_value
    return raw_value.strip()


@staff_member_required
def bulk_edit_components(request):
    """Show the bulk-edit form for the components selected via the admin action."""
    ids = request.session.get('bulk_edit_component_ids') or []
    components = Component.objects.filter(id__in=ids)
    total_count = components.count()

    if not ids or total_count == 0:
        messages.warning(
            request,
            'No components selected. Select some in the component list and use '
            'the "Bulk edit selected components" action.',
        )
        return redirect('admin:components_component_changelist')

    type_counts = (
        components.values('component_type')
        .annotate(count=db_models.Count('id'))
        .order_by('-count')
    )

    context = {
        **admin.site.each_context(request),
        'title': 'Bulk Edit Components',
        'components': components.order_by('manufacturer', 'part_number')[:MAX_PREVIEW_ROWS],
        'total_count': total_count,
        'truncated': total_count > MAX_PREVIEW_ROWS,
        'type_counts': type_counts,
        'fields': [
            {
                'name': f.name,
                'label': str(f.verbose_name),
                'kind': _field_widget_kind(f),
                'choices': f.choices if f.choices else None,
            }
            for f in _bulk_editable_fields()
        ],
        'action_url': reverse('admin-component-bulk-edit-action'),
        'cancel_url': reverse('admin:components_component_changelist'),
    }
    return render(request, 'admin/component_bulk_edit.html', context)


@staff_member_required
def bulk_edit_components_action(request):
    """Apply the submitted field/value change to the selected components."""
    redirect_url = reverse('admin:components_component_changelist')

    if request.method != 'POST':
        return redirect(redirect_url)

    ids = request.session.get('bulk_edit_component_ids') or []
    components = list(Component.objects.filter(id__in=ids))
    if not components:
        messages.warning(request, 'No components selected.')
        return redirect(redirect_url)

    field_name = request.POST.get('field', '')
    raw_value = request.POST.get('value', '')

    editable_fields = {f.name: f for f in _bulk_editable_fields()}
    field = editable_fields.get(field_name)
    if field is None:
        messages.error(request, 'That field cannot be bulk-edited.')
        return redirect('admin-component-bulk-edit')

    try:
        value = _coerce_value(field, raw_value)
    except ValueError as exc:
        messages.error(request, str(exc))
        return redirect('admin-component-bulk-edit')

    # Same request -> same IP for every log entry, so this is computed once
    # rather than re-derived per component inside AdminAuditLog.log_action.
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    ip_address = (
        x_forwarded_for.split(',')[0].strip() if x_forwarded_for
        else request.META.get('REMOTE_ADDR')
    )
    admin_user = request.user if request.user.is_authenticated else None

    to_update = []
    audit_logs = []
    for component in components:
        old_value = getattr(component, field_name)
        if old_value == value:
            continue
        setattr(component, field_name, value)
        to_update.append(component)
        audit_logs.append(AdminAuditLog(
            admin_user=admin_user,
            action_type=AdminAuditLog.ActionType.COMPONENT_BULK_EDITED,
            target_model='Component',
            target_id=str(component.pk),
            target_repr=str(component)[:255],
            details={'field': field_name, 'old_value': str(old_value), 'new_value': str(value)},
            ip_address=ip_address,
        ))

    if to_update:
        Component.objects.bulk_update(to_update, [field_name])
        # bulk_update() writes columns directly and does not call each
        # instance's save() - which normally also recomputes search_vector.
        # Redo it here in one query if the edited field feeds that vector,
        # so bulk-editing doesn't silently leave search results stale.
        search_vector_fields = {'part_number', 'manufacturer', 'typical_function', 'description'}
        if field_name in search_vector_fields:
            from django.contrib.postgres.search import SearchVector
            Component.objects.filter(pk__in=[c.pk for c in to_update]).update(
                search_vector=(
                    SearchVector('part_number', weight='A') +
                    SearchVector('manufacturer', weight='A') +
                    SearchVector('typical_function', weight='B') +
                    SearchVector('description', weight='C')
                )
            )
    if audit_logs:
        AdminAuditLog.objects.bulk_create(audit_logs)
    updated = len(to_update)

    del request.session['bulk_edit_component_ids']
    unchanged = len(components) - updated
    summary_msg = f'Set {field.verbose_name} on {updated} component(s).'
    if unchanged:
        summary_msg += f' {unchanged} already had that value.'
    messages.success(request, summary_msg)
    return redirect(redirect_url)
