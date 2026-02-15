"""
BOM-to-junkbin matching engine for recipes.

Compares a user's component collection against recipe BOMs
to determine what they can build.
"""
from django.contrib.contenttypes.models import ContentType


def get_user_component_ids(user):
    """
    Get the set of component IDs that a user has in their junkbin.

    Returns a Python set for O(1) lookups.
    """
    from apps.junkbin.models import JunkbinItem

    component_ct = ContentType.objects.get(app_label='components', model='component')
    return set(
        JunkbinItem.objects.filter(
            user=user,
            content_type=component_ct,
            item_type='have',
        ).values_list('object_id', flat=True)
    )


def calculate_recipe_match(recipe, user_component_ids):
    """
    Calculate match data for a single recipe against a user's components.

    Returns dict with match_percentage, counts, and component lists.
    """
    required = []
    optional = []

    for rc in recipe.recipe_components.all():
        if rc.is_optional:
            optional.append(rc)
        else:
            required.append(rc)

    matched = [rc for rc in required if rc.component_id in user_component_ids]
    missing = [rc for rc in required if rc.component_id not in user_component_ids]
    optional_matched = [rc for rc in optional if rc.component_id in user_component_ids]
    optional_missing = [rc for rc in optional if rc.component_id not in user_component_ids]

    total_required = len(required)
    match_percentage = (len(matched) / total_required * 100) if total_required > 0 else 0

    return {
        'match_percentage': round(match_percentage, 1),
        'total_required': total_required,
        'matched_count': len(matched),
        'matched_components': matched,
        'missing_components': missing,
        'optional_matched': optional_matched,
        'optional_missing': optional_missing,
    }


def get_buildable_recipes(user, queryset=None, min_match_percentage=0):
    """
    Get all recipes sorted by match percentage for a user.

    Returns list of (recipe, match_data) tuples.
    """
    from .models import Recipe

    if queryset is None:
        queryset = Recipe.objects.filter(is_approved=True)

    queryset = queryset.prefetch_related('recipe_components__component')
    user_component_ids = get_user_component_ids(user)

    results = []
    for recipe in queryset:
        match_data = calculate_recipe_match(recipe, user_component_ids)
        if match_data['match_percentage'] >= min_match_percentage:
            results.append((recipe, match_data))

    results.sort(key=lambda x: x[1]['match_percentage'], reverse=True)
    return results


def get_missing_part_availability(missing_component_ids, exclude_user):
    """
    Find other users who have the missing components available.

    Returns {component_id: [{user_id, username, quantity, condition}]}.
    """
    from apps.junkbin.models import JunkbinItem

    component_ct = ContentType.objects.get(app_label='components', model='component')
    items = JunkbinItem.objects.filter(
        content_type=component_ct,
        object_id__in=missing_component_ids,
        item_type='have',
        status='available',
        visibility='public',
    ).exclude(
        user=exclude_user
    ).select_related('user')

    availability = {}
    for item in items:
        comp_id = str(item.object_id)
        if comp_id not in availability:
            availability[comp_id] = []
        availability[comp_id].append({
            'user_id': str(item.user.id),
            'username': item.user.username,
            'quantity': item.quantity,
            'condition': item.condition,
        })

    return availability
