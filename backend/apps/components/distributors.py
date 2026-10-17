"""
DigiKey and Mouser part lookups, used next to Nexar (see nexar.py).

Both clients return the same normalised dict as NexarClient.search_mpn, plus:
    "source":      "digikey" | "mouser"
    "status":      lifecycle text ("Active", "Obsolete", ...) or ""
    "product_url": distributor product page

DigiKey: Product Information v4, OAuth2 client credentials, 1000 calls/day.
Mouser:  Search API v1, API key, 1000 calls/day and 30/minute.
Both answer an exact manufacturer part number; a hit whose MPN differs from
the query (after dropping punctuation) is treated as no hit.
"""
import logging
import re
import time

import requests
from django.conf import settings

logger = logging.getLogger(__name__)


class DistributorError(RuntimeError):
    """The distributor refused the call (quota, auth, outage)."""


def same_mpn(a, b):
    def norm(s):
        return re.sub(r'[^A-Z0-9]', '', (s or '').upper())
    return norm(a) == norm(b)


# BOM/vendor abbreviations and acquisitions -> the name distributors list today
MAKER_SYNONYMS = {
    'TI': 'TEXAS INSTRUMENTS', 'NS': 'TEXAS INSTRUMENTS', 'NATIONAL': 'TEXAS INSTRUMENTS',
    'ST': 'STMICROELECTRONICS', 'ON': 'ONSEMI', 'FAIRCHILD': 'ONSEMI',
    'PHILIPS': 'NEXPERIA', 'NXP': 'NEXPERIA', 'AD': 'ANALOG DEVICES', 'ADI': 'ANALOG DEVICES',
    'LINEAR': 'ANALOG DEVICES', 'MAXIM': 'ANALOG DEVICES', 'IR': 'INFINEON',
    'SILICONIX': 'VISHAY', 'GS': 'VISHAY', 'DII': 'DIODES', 'ZETEX': 'DIODES',
    'MICREL': 'MICROCHIP', 'ATMEL': 'MICROCHIP', 'SST': 'MICROCHIP',
}


def same_maker(a, b):
    """Loose manufacturer comparison: first significant word, after synonyms."""
    def key(name):
        words = re.findall(r'[A-Z0-9]+', (name or '').upper())
        if not words:
            return ''
        first = MAKER_SYNONYMS.get(words[0], words[0])
        return first.split()[0]
    return bool(key(a)) and key(a) == key(b)


def _money(text):
    """Mouser prices are strings like '$0.014' or '1,23 €'."""
    m = re.search(r'\d[\d,]*\.?\d*', text or '')
    return float(m.group(0).replace(',', '')) if m else None


class DigiKeyClient:
    TOKEN_URL = 'https://api.digikey.com/v1/oauth2/token'
    DETAILS_URL = 'https://api.digikey.com/products/v4/search/{mpn}/productdetails'
    KEYWORD_URL = 'https://api.digikey.com/products/v4/search/keyword'

    def __init__(self):
        self.client_id = settings.DIGIKEY_CLIENT_ID
        self.client_secret = settings.DIGIKEY_CLIENT_SECRET
        self._token = None
        self._token_expires = 0
        self.remaining = None   # x-ratelimit-remaining from the last call

    @property
    def is_configured(self):
        return bool(self.client_id and self.client_secret)

    def _get_token(self):
        if self._token and time.time() < self._token_expires:
            return self._token
        resp = requests.post(self.TOKEN_URL, data={
            'grant_type': 'client_credentials',
            'client_id': self.client_id,
            'client_secret': self.client_secret,
        }, timeout=15)
        if not resp.ok:
            raise DistributorError(f'DigiKey token: HTTP {resp.status_code} {resp.text[:200]}')
        data = resp.json()
        self._token = data['access_token']
        self._token_expires = time.time() + int(data.get('expires_in', 600)) - 60
        return self._token

    def search_mpn(self, part_number, manufacturer=None):
        if not self.is_configured:
            raise RuntimeError('DigiKey API credentials not configured')
        resp = self._call('get', self.DETAILS_URL.format(mpn=requests.utils.quote(part_number, safe='')))
        if resp.status_code == 404 and 'Duplicate Products' in resp.text:
            # Several makers sell this MPN (LM358DR: TI and Rohm); pick by maker.
            return self._exact_match(part_number, manufacturer)
        if resp.status_code == 404:
            return None
        part = resp.json().get('Product') or {}
        if not same_mpn(part.get('ManufacturerProductNumber'), part_number):
            return None
        return self._parse_part(part)

    def _exact_match(self, part_number, manufacturer):
        resp = self._call('post', self.KEYWORD_URL, json={'Keywords': part_number, 'Limit': 10})
        if resp.status_code == 404:
            return None
        matches = [p for p in resp.json().get('ExactMatches') or []
                   if same_mpn(p.get('ManufacturerProductNumber'), part_number)]
        if manufacturer:
            preferred = [p for p in matches
                         if same_maker((p.get('Manufacturer') or {}).get('Name'), manufacturer)]
            matches = preferred or matches
        return self._parse_part(matches[0]) if matches else None

    def _call(self, method, url, **kwargs):
        resp = requests.request(method, url, headers={
            'Authorization': f'Bearer {self._get_token()}',
            'X-DIGIKEY-Client-Id': self.client_id,
            'X-DIGIKEY-Locale-Site': 'US',
            'X-DIGIKEY-Locale-Language': 'en',
            'X-DIGIKEY-Locale-Currency': 'USD',
        }, timeout=15, **kwargs)
        if 'x-ratelimit-remaining' in resp.headers:
            self.remaining = int(resp.headers['x-ratelimit-remaining'])
        if not resp.ok and resp.status_code != 404:
            raise DistributorError(f'DigiKey: HTTP {resp.status_code} {resp.text[:200]}')
        return resp

    @staticmethod
    def _parse_part(part):
        offers = []
        stock = part.get('QuantityAvailable') or 0
        for var in part.get('ProductVariations') or []:
            prices = var.get('StandardPricing') or []
            if not prices:
                continue
            best = min(prices, key=lambda p: p['UnitPrice'])
            offers.append({
                'stock': var.get('QuantityAvailableforPackageType') or 0,
                'price': round(best['UnitPrice'], 5),
                'currency': 'USD',
                'qty_min': best['BreakQuantity'],
                'buy_url': part.get('ProductUrl', ''),
                'sku': var.get('DigiKeyProductNumber', ''),
                'packaging': (var.get('PackageType') or {}).get('Name', ''),
            })
        description = part.get('Description') or {}
        return {
            'source': 'digikey',
            'mpn': part.get('ManufacturerProductNumber', ''),
            'manufacturer': (part.get('Manufacturer') or {}).get('Name', ''),
            'description': description.get('DetailedDescription') or description.get('ProductDescription', ''),
            'datasheet_url': part.get('DatasheetUrl') or None,
            'product_url': part.get('ProductUrl', ''),
            'status': (part.get('ProductStatus') or {}).get('Status', ''),
            'category': (part.get('Category') or {}).get('Name', ''),
            'stock': stock,
            'specs': [{'name': p.get('ParameterText', ''), 'value': p.get('ValueText', '')}
                      for p in part.get('Parameters') or []],
            'sellers': [{'name': 'DigiKey', 'url': 'https://www.digikey.com', 'offers': offers}] if offers else [],
        }


class MouserClient:
    SEARCH_URL = 'https://api.mouser.com/api/v1/search/partnumber'

    def __init__(self):
        self.api_key = settings.MOUSER_API_KEY

    @property
    def is_configured(self):
        return bool(self.api_key)

    def search_mpn(self, part_number, manufacturer=None):
        if not self.is_configured:
            raise RuntimeError('Mouser API key not configured')
        resp = requests.post(
            self.SEARCH_URL,
            params={'apiKey': self.api_key},
            json={'SearchByPartRequest': {'mouserPartNumber': part_number, 'partSearchOptions': 'Exact'}},
            timeout=15,
        )
        if not resp.ok:
            raise DistributorError(f'Mouser: HTTP {resp.status_code} {resp.text[:200]}')
        data = resp.json()
        if data.get('Errors'):
            raise DistributorError('Mouser: ' + '; '.join(
                e.get('Message', '') for e in data['Errors']))
        parts = (data.get('SearchResults') or {}).get('Parts') or []
        parts = [p for p in parts if same_mpn(p.get('ManufacturerPartNumber'), part_number)]
        if not parts:
            return None
        return self._parse_part(parts[0])

    @staticmethod
    def _parse_part(part):
        prices = [(b['Quantity'], _money(b.get('Price'))) for b in part.get('PriceBreaks') or []]
        prices = [(q, p) for q, p in prices if p is not None]
        stock = int(part.get('AvailabilityInStock') or 0)
        offers = []
        if prices:
            qty, price = min(prices, key=lambda x: x[1])
            offers.append({
                'stock': stock, 'price': price, 'currency': 'USD', 'qty_min': qty,
                'buy_url': part.get('ProductDetailUrl', ''), 'sku': part.get('MouserPartNumber', ''),
            })
        return {
            'source': 'mouser',
            'mpn': part.get('ManufacturerPartNumber', ''),
            'manufacturer': part.get('Manufacturer', ''),
            'description': part.get('Description', ''),
            'datasheet_url': part.get('DataSheetUrl') or None,
            'product_url': part.get('ProductDetailUrl', ''),
            'status': part.get('LifecycleStatus') or '',
            'category': part.get('Category', ''),
            'stock': stock,
            'specs': [{'name': a['AttributeName'], 'value': a['AttributeValue']}
                      for a in part.get('ProductAttributes') or []
                      if a.get('AttributeName') not in ('Packaging', 'Standard Pack Qty')],
            'sellers': [{'name': 'Mouser', 'url': 'https://www.mouser.com', 'offers': offers}] if offers else [],
        }


_clients = {}


def get_digikey():
    if 'digikey' not in _clients:
        _clients['digikey'] = DigiKeyClient()
    return _clients['digikey']


def get_mouser():
    if 'mouser' not in _clients:
        _clients['mouser'] = MouserClient()
    return _clients['mouser']
