"""
Nexar (Octopart) API client for component enrichment.

Provides MPN search with pricing, availability, datasheets, and specs
aggregated across DigiKey, Mouser, and 100+ other distributors.

Auth: OAuth2 client credentials → https://identity.nexar.com/connect/token
API:  GraphQL POST → https://api.nexar.com/graphql
"""
import logging
import time

import requests
from django.conf import settings

logger = logging.getLogger(__name__)

GRAPHQL_QUERY = """
query SearchMPN($mpn: String!) {
  supSearchMpn(q: $mpn, limit: 3) {
    hits
    results {
      part {
        mpn
        manufacturer { name }
        shortDescription
        bestDatasheet { url }
        specs { attribute { name } displayValue }
        sellers(authorizedOnly: false) {
          company { name homepageUrl }
          offers {
            inventoryLevel
            prices { price quantity currency }
            clickUrl
          }
        }
      }
    }
  }
}
"""


class NexarClient:
    TOKEN_URL = "https://identity.nexar.com/connect/token"
    GRAPHQL_URL = "https://api.nexar.com/graphql"

    def __init__(self):
        self.client_id = settings.NEXAR_CLIENT_ID
        self.client_secret = settings.NEXAR_CLIENT_SECRET
        self._token = None
        self._token_expires = 0

    @property
    def is_configured(self):
        return bool(self.client_id and self.client_secret)

    def _get_token(self):
        """OAuth2 client credentials flow with in-memory caching."""
        if self._token and time.time() < self._token_expires:
            return self._token

        resp = requests.post(
            self.TOKEN_URL,
            data={
                "grant_type": "client_credentials",
                "client_id": self.client_id,
                "client_secret": self.client_secret,
            },
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        self._token = data["access_token"]
        # Cache for slightly less than the full expiry (default 24h)
        self._token_expires = time.time() + data.get("expires_in", 86400) - 300
        return self._token

    def search_mpn(self, part_number, manufacturer=None):
        """
        Search by manufacturer part number.

        Returns a normalised dict:
        {
            "mpn": str,
            "manufacturer": str,
            "description": str,
            "datasheet_url": str | None,
            "specs": [{"name": str, "value": str}, ...],
            "sellers": [{
                "name": str, "url": str,
                "offers": [{"stock": int, "price": float, "currency": str,
                            "qty_min": int, "buy_url": str}, ...]
            }, ...],
        }
        """
        if not self.is_configured:
            raise RuntimeError("Nexar API credentials not configured")

        token = self._get_token()
        # Search by MPN only — prefixing with manufacturer name
        # causes Nexar's supSearchMpn to return zero results.
        query_str = part_number

        resp = requests.post(
            self.GRAPHQL_URL,
            json={"query": GRAPHQL_QUERY, "variables": {"mpn": query_str}},
            headers={"Authorization": f"Bearer {token}"},
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()

        results = (
            data.get("data", {})
            .get("supSearchMpn", {})
            .get("results", [])
        )

        if not results:
            return None

        # Pick the best match (first result)
        part = results[0].get("part", {})
        return self._parse_part(part)

    @staticmethod
    def _parse_part(part):
        """Parse a GraphQL part result into our normalised format."""
        datasheet = part.get("bestDatasheet") or {}
        specs = [
            {"name": s["attribute"]["name"], "value": s["displayValue"]}
            for s in (part.get("specs") or [])
            if s.get("attribute")
        ]

        sellers = []
        for seller in part.get("sellers") or []:
            company = seller.get("company") or {}
            offers = []
            for offer in seller.get("offers") or []:
                prices = offer.get("prices") or []
                best_price = None
                best_qty = 1
                best_currency = "USD"
                for p in prices:
                    if best_price is None or p.get("price", 0) < best_price:
                        best_price = p.get("price")
                        best_qty = p.get("quantity", 1)
                        best_currency = p.get("currency", "USD")

                stock = offer.get("inventoryLevel") or 0
                if isinstance(stock, str):
                    # inventoryLevel can be an int or descriptive string
                    stock = 0

                if best_price is not None:
                    offers.append({
                        "stock": stock,
                        "price": round(best_price, 4),
                        "currency": best_currency,
                        "qty_min": best_qty,
                        "buy_url": offer.get("clickUrl", ""),
                    })

            if offers:
                sellers.append({
                    "name": company.get("name", "Unknown"),
                    "url": company.get("homepageUrl", ""),
                    "offers": offers,
                })

        # Sort sellers by lowest price
        sellers.sort(key=lambda s: min(o["price"] for o in s["offers"]))

        return {
            "mpn": part.get("mpn", ""),
            "manufacturer": (part.get("manufacturer") or {}).get("name", ""),
            "description": part.get("shortDescription", ""),
            "datasheet_url": datasheet.get("url"),
            "specs": specs,
            "sellers": sellers,
        }


# Module-level singleton (lazy)
_client = None


def get_client():
    global _client
    if _client is None:
        _client = NexarClient()
    return _client
