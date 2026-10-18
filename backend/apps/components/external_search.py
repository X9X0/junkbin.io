"""
Distributor search for part numbers the site's catalogue doesn't have.

search(query) asks DigiKey (keyword search, full parametrics) and Mouser
(part-number search, begins-with) for up to MAX_RESULTS candidates and
caches the merged answer in ExternalPartSearch for CACHE_DAYS, so repeat
searches - by anyone - spend no quota. A daily budget keeps distributor
searches from eating the calls the per-component Lookup button needs:
DigiKey is skipped below DIGIKEY_RESERVE remaining calls, Mouser after
MOUSER_DAILY_BUDGET searches in a day.
"""
import logging
import re
from datetime import timedelta

import requests
from django.core.cache import cache
from django.utils import timezone

from .distributors import DistributorError, get_digikey, get_mouser, same_mpn
from .models import ExternalPartSearch

logger = logging.getLogger(__name__)

CACHE_DAYS = 7
MAX_RESULTS = 10
DIGIKEY_RESERVE = 150
MOUSER_DAILY_BUDGET = 700
PART_NUMBER = re.compile(r'^[A-Z0-9][A-Z0-9\-./#+,]{2,38}[A-Z0-9#+]$')


def normalise(query):
    return re.sub(r'\s+', '', (query or '').upper())


def looks_like_part_number(query):
    """Part-number shaped: 4-40 characters, letters AND digits, no spaces."""
    q = normalise(query)
    return bool(PART_NUMBER.match(q) and re.search(r'\d', q) and re.search(r'[A-Z]', q))


class SearchUnavailable(RuntimeError):
    """No distributor could be asked (budget spent, outage, not configured)."""


def search(query):
    """(results, from_cache). Raises SearchUnavailable when nothing could be asked."""
    q = normalise(query)
    cached = ExternalPartSearch.objects.filter(query=q).first()
    if cached and cached.fetched_at > timezone.now() - timedelta(days=CACHE_DAYS):
        ExternalPartSearch.objects.filter(pk=cached.pk).update(search_count=cached.search_count + 1)
        return cached.results, True

    answers, asked = [], []
    digikey, mouser = get_digikey(), get_mouser()
    if digikey.is_configured and cache.get('digikey_remaining', 1000) > DIGIKEY_RESERVE:
        try:
            answers += digikey_keyword(digikey, q)
            asked.append('digikey')
        except Exception as exc:
            logger.warning('DigiKey keyword search failed for %s: %s', q, exc)
        if digikey.remaining is not None:
            cache.set('digikey_remaining', digikey.remaining, 6 * 3600)
    day_key = f'mouser_searches:{timezone.now():%Y%m%d}'
    if mouser.is_configured and cache.get(day_key, 0) < MOUSER_DAILY_BUDGET:
        try:
            answers += mouser_begins_with(mouser, q)
            asked.append('mouser')
            cache.set(day_key, cache.get(day_key, 0) + 1, 26 * 3600)
        except Exception as exc:
            logger.warning('Mouser search failed for %s: %s', q, exc)
    if not asked:
        raise SearchUnavailable('distributor search budget for today is used up')

    results = rank(merge(answers), q)[:MAX_RESULTS]
    ExternalPartSearch.objects.update_or_create(
        query=q, defaults={'results': results, 'sources': asked, 'fetched_at': timezone.now(),
                           'search_count': (cached.search_count + 1) if cached else 1})
    return results, False


def digikey_keyword(client, q):
    resp = client._call('post', client.KEYWORD_URL, json={'Keywords': q, 'Limit': MAX_RESULTS})
    if resp.status_code == 404:
        return []
    data = resp.json()
    products = (data.get('ExactMatches') or []) + (data.get('Products') or [])
    return [client._parse_part(p) for p in products]


def mouser_begins_with(client, q):
    resp = requests.post(client.SEARCH_URL, params={'apiKey': client.api_key}, timeout=15,
                         json={'SearchByPartRequest': {'mouserPartNumber': q, 'partSearchOptions': ''}})   # '' = prefix matches (proven in mpn_verify)
    if not resp.ok:
        raise DistributorError(f'Mouser: HTTP {resp.status_code}')
    data = resp.json()
    if data.get('Errors'):
        raise DistributorError('Mouser: ' + '; '.join(e.get('Message', '') for e in data['Errors']))
    parts = (data.get('SearchResults') or {}).get('Parts') or []
    return [client._parse_part(p) for p in parts[:MAX_RESULTS]]


def merge(answers):
    """One entry per (maker, part number); sellers and missing fields combined."""
    out = {}
    for a in answers:
        if not a.get('mpn'):
            continue
        key = (re.sub(r'[^A-Z0-9]', '', a['manufacturer'].upper())[:12], re.sub(r'[^A-Z0-9]', '', a['mpn'].upper()))
        if key not in out:
            out[key] = {**a, 'sources': [a['source']]}
            continue
        have = out[key]
        have['sources'] = sorted(set(have['sources']) | {a['source']})
        have['sellers'] = (have.get('sellers') or []) + (a.get('sellers') or [])
        for field in ('datasheet_url', 'description', 'status', 'category', 'product_url'):
            have[field] = have.get(field) or a.get(field)
        if len(a.get('specs') or []) > len(have.get('specs') or []):
            have['specs'] = a['specs']
    for r in out.values():
        r.pop('source', None)
    return list(out.values())


def rank(results, q):
    """Exact part number first, then part numbers that start with the query, then in stock."""
    def key(r):
        mpn = r['mpn'].upper()
        return (not same_mpn(mpn, q), not mpn.startswith(q), -(r.get('stock') or 0))
    return sorted(results, key=key)
