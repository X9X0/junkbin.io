"""
robots.txt and sitemap.xml for the React SPA.

Served by Django (nginx proxies the two exact paths here) rather than as static
files so URLs follow the request host instead of being hardcoded. Not using
django.contrib.sitemaps: it builds URLs from the Sites framework, and the Site
row is still the default example.com.
"""
from django.http import HttpResponse
from django.utils.xmlutils import SimplerXMLGenerator
from django.views.decorators.cache import cache_page
from django.views.decorators.http import require_GET

from apps.components.models import Component
from apps.products.models import Product
from apps.recipes.models import Recipe

# Public, indexable SPA pages that aren't tied to a database row.
STATIC_PAGES = [
    '/', '/products', '/components', '/schematics', '/recipes', '/swap',
    '/community', '/about', '/guidelines', '/docs', '/news', '/contact',
]

# SPA routes that are per-user, auth-gated or one-shot token links - nothing
# worth indexing. /api/ is deliberately NOT disallowed: crawlers that render
# JavaScript need it to see any page content at all.
DISALLOWED = [
    '/messages', '/notifications', '/profile', '/my-junkbin',
    '/my-submissions', '/moderation', '/analytics', '/submit',
    '/recipes/submit', '/login', '/register', '/reset-password',
    '/verify-email/', '/unsubscribe/', '/auth/', '/accounts/',
    '/grafana/', '/prometheus/',
]

CACHE_SECONDS = 60 * 60


def _base_url(request):
    return f'{request.scheme}://{request.get_host()}'


@require_GET
@cache_page(CACHE_SECONDS)
def robots_txt(request):
    lines = ['User-agent: *']
    lines += [f'Disallow: {path}' for path in DISALLOWED]
    lines += ['', f'Sitemap: {_base_url(request)}/sitemap.xml', '']
    return HttpResponse('\n'.join(lines), content_type='text/plain; charset=utf-8')


def _sitemap_entries():
    """Yield (path, lastmod) for every public page, matching the SPA's links."""
    for path in STATIC_PAGES:
        yield path, None
    for pk, updated in (Product.objects.filter(is_approved=True)
                        .order_by('-updated_at').values_list('pk', 'updated_at')):
        yield f'/products/{pk}', updated
    for pk, updated in (Recipe.objects.filter(is_approved=True)
                        .order_by('-updated_at').values_list('pk', 'updated_at')):
        yield f'/recipes/{pk}', updated
    for pk, updated in (Component.objects.order_by('-updated_at')
                        .values_list('pk', 'updated_at')):
        yield f'/components/{pk}/products', updated


@require_GET
@cache_page(CACHE_SECONDS)
def sitemap_xml(request):
    base = _base_url(request)
    response = HttpResponse(content_type='application/xml; charset=utf-8')
    xml = SimplerXMLGenerator(response, 'utf-8')
    xml.startDocument()
    xml.startElement('urlset', {'xmlns': 'http://www.sitemaps.org/schemas/sitemap/0.9'})
    for path, lastmod in _sitemap_entries():
        xml.startElement('url', {})
        xml.addQuickElement('loc', base + path)
        if lastmod:
            xml.addQuickElement('lastmod', lastmod.date().isoformat())
        xml.endElement('url')
    xml.endElement('urlset')
    xml.endDocument()
    return response
