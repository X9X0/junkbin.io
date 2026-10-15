"""
Tests for robots.txt and sitemap.xml.
"""
import xml.etree.ElementTree as ET

import pytest
from django.core.cache import cache
from django.test import Client

NS = {'sm': 'http://www.sitemaps.org/schemas/sitemap/0.9'}


@pytest.fixture(autouse=True)
def clear_cache(settings):
    settings.ALLOWED_HOSTS = ['junkbin.io']
    # Both views are cache_page'd; don't let one test's response leak into another
    cache.clear()
    yield
    cache.clear()


def _get(path):
    return Client(HTTP_HOST='junkbin.io').get(path, secure=True)


def _locs(response):
    root = ET.fromstring(response.content)
    return [el.text for el in root.findall('sm:url/sm:loc', NS)]


@pytest.mark.django_db
class TestRobotsTxt:
    def test_points_at_sitemap_on_request_host(self):
        response = _get('/robots.txt')
        assert response.status_code == 200
        assert response['Content-Type'].startswith('text/plain')
        body = response.content.decode()
        assert 'Sitemap: https://junkbin.io/sitemap.xml' in body
        assert 'Disallow: /messages' in body

    def test_api_not_disallowed(self):
        # Rendering crawlers need /api/ to see SPA content
        body = _get('/robots.txt').content.decode()
        assert 'Disallow: /api' not in body


@pytest.mark.django_db
class TestSitemapXml:
    def test_lists_static_pages(self):
        response = _get('/sitemap.xml')
        assert response.status_code == 200
        assert response['Content-Type'].startswith('application/xml')
        locs = _locs(response)
        assert 'https://junkbin.io/' in locs
        assert 'https://junkbin.io/products' in locs

    def test_only_approved_products(self, product_factory):
        approved = product_factory(is_approved=True)
        pending = product_factory(is_approved=False)
        locs = _locs(_get('/sitemap.xml'))
        assert f'https://junkbin.io/products/{approved.pk}' in locs
        assert f'https://junkbin.io/products/{pending.pk}' not in locs

    def test_components_link_to_their_product_list(self, component_factory):
        component = component_factory()
        locs = _locs(_get('/sitemap.xml'))
        assert f'https://junkbin.io/components/{component.pk}/products' in locs
