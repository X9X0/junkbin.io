"""
Badge/achievement system for Junkbin.io

Badge definitions live here as a registry dict. Each badge has a check function
that determines whether a user qualifies. check_and_award_badges() is called
at key trigger points (contribution approval, junkbin add, schematic upload,
recipe creation) and awards any newly-earned badges.
"""
import logging
from django.utils import timezone

logger = logging.getLogger(__name__)


BADGE_REGISTRY = {
    'first_contribution': {
        'name': 'First Contribution',
        'description': 'Made your first approved contribution',
        'icon': 'gift',
        'color': 'cyan',
        'check': lambda user: user.contribution_count >= 1,
    },
    'contributor_10': {
        'name': 'Prolific Contributor',
        'description': 'Made 10 approved contributions',
        'icon': 'zap',
        'color': 'pink',
        'check': lambda user: user.contribution_count >= 10,
    },
    'contributor_50': {
        'name': 'Master Contributor',
        'description': 'Made 50 approved contributions',
        'icon': 'crown',
        'color': 'yellow',
        'check': lambda user: user.contribution_count >= 50,
    },
    'trusted': {
        'name': 'Trusted',
        'description': 'Earned trusted contributor status',
        'icon': 'shield',
        'color': 'green',
        'check': lambda user: user.is_trusted,
    },
    'moderator': {
        'name': 'Moderator',
        'description': 'Community moderator',
        'icon': 'star',
        'color': 'yellow',
        'check': lambda user: user.is_moderator,
    },
    'early_adopter': {
        'name': 'Early Adopter',
        'description': 'Among the first 50 users to join',
        'icon': 'rocket',
        'color': 'purple',
        'check': lambda user: _is_early_adopter(user),
    },
    'schematic_uploader': {
        'name': 'Schematic Uploader',
        'description': 'Uploaded a schematic or service document',
        'icon': 'file-text',
        'color': 'cyan',
        'check': lambda user: user.uploaded_schematics.exists(),
    },
    'junkbin_starter': {
        'name': 'Salvager',
        'description': 'Added an item to your junkbin',
        'icon': 'archive',
        'color': 'green',
        'check': lambda user: user.junkbin_items.exists(),
    },
    'recipe_creator': {
        'name': 'Recipe Master',
        'description': 'Created a recipe',
        'icon': 'book-open',
        'color': 'pink',
        'check': lambda user: user.created_recipes.exists(),
    },
}


def _is_early_adopter(user):
    """Check if user is among the first 50 registered users."""
    from django.contrib.auth import get_user_model
    User = get_user_model()
    early_ids = User.objects.order_by('created_at').values_list('id', flat=True)[:50]
    return user.id in set(early_ids)


def check_and_award_badges(user):
    """
    Check all badge criteria and award any newly-earned badges.

    Skips badges the user already has. Saves user only if new badges
    were awarded.
    """
    current_slugs = {b['slug'] for b in (user.badges or [])}
    new_badges = []

    for slug, badge in BADGE_REGISTRY.items():
        if slug in current_slugs:
            continue
        try:
            if badge['check'](user):
                new_badges.append({
                    'slug': slug,
                    'awarded_at': timezone.now().isoformat(),
                })
        except Exception:
            logger.exception('Badge check failed for %s on user %s', slug, user.pk)

    if new_badges:
        if user.badges is None:
            user.badges = []
        user.badges = user.badges + new_badges
        user.save(update_fields=['badges'])

    return new_badges


def get_user_badges_display(user):
    """
    Merge stored badge data (slug + awarded_at) with registry display info.

    Returns a list of dicts suitable for API serialization.
    """
    result = []
    for badge_data in (user.badges or []):
        slug = badge_data.get('slug')
        registry_entry = BADGE_REGISTRY.get(slug)
        if not registry_entry:
            continue
        result.append({
            'slug': slug,
            'name': registry_entry['name'],
            'description': registry_entry['description'],
            'icon': registry_entry['icon'],
            'color': registry_entry['color'],
            'awarded_at': badge_data.get('awarded_at'),
        })
    return result
