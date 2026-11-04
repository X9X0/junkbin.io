"""
One part lookup across every configured provider.

Nexar is asked first (it already aggregates DigiKey, Mouser and 100+ others).
If it has no answer, or refuses the query (its plan has a hard part limit),
DigiKey and Mouser are asked directly and their answers merged: specs and
description from DigiKey when it has the part (it returns full parametrics),
sellers from both.

The merged dict has the same shape as NexarClient.search_mpn, plus
"sources" (which providers answered), so the stored result keeps working
with ComponentDetailSerializer.pricing_data and the PricingPanel UI.
"""
import logging

from django.core.cache import cache

from .distributors import get_digikey, get_mouser
from .nexar import NexarError, get_client

logger = logging.getLogger(__name__)

# After Nexar refuses a query (quota), skip it for a while instead of
# burning a round trip on every lookup.
NEXAR_PAUSE_KEY = 'nexar_refused'
NEXAR_PAUSE_SECONDS = 6 * 60 * 60


class LookupUnavailable(RuntimeError):
    """Every configured provider refused or failed; nothing was looked up."""


def lookup_part(part_number, manufacturer=None):
    """Merged provider answer, None when every provider that answered had no
    such part, LookupUnavailable when no provider answered at all."""
    answered = False
    nexar = get_client()
    if nexar.is_configured and not cache.get(NEXAR_PAUSE_KEY):
        try:
            result = nexar.search_mpn(part_number, manufacturer)
        except NexarError as exc:
            logger.warning('Nexar refused lookup, pausing it: %s', exc)
            cache.set(NEXAR_PAUSE_KEY, str(exc), NEXAR_PAUSE_SECONDS)
        except Exception:
            logger.exception('Nexar lookup failed for %s', part_number)
        else:
            if result:
                return {**result, 'sources': ['nexar']}
            answered = True

    answers = []
    for client in (get_digikey(), get_mouser()):
        if not client.is_configured:
            continue
        try:
            result = client.search_mpn(part_number, manufacturer)
        except Exception as exc:
            logger.warning('%s lookup failed for %s: %s', type(client).__name__, part_number, exc)
            continue
        answered = True
        if result:
            answers.append(result)

    if answers:
        return merge(answers)
    if not answered:
        raise LookupUnavailable(f'no part lookup provider answered for {part_number}')
    return None


def merge(answers):
    """Combine distributor answers; the one with the most specs leads."""
    lead = max(answers, key=lambda a: len(a.get('specs') or []))
    sellers = [s for a in answers for s in a.get('sellers') or []]
    sellers.sort(key=lambda s: min(o['price'] for o in s['offers']))
    return {
        'mpn': lead['mpn'],
        'manufacturer': lead['manufacturer'],
        'description': lead.get('description', ''),
        'datasheet_url': next((a['datasheet_url'] for a in answers if a.get('datasheet_url')), None),
        'specs': lead.get('specs') or [],
        'sellers': sellers,
        'status': next((a['status'] for a in answers if a.get('status')), ''),
        'sources': [a['source'] for a in answers],
    }
