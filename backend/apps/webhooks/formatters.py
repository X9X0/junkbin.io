"""
Platform-specific payload builders for Discord and Slack webhooks.
"""
from django.conf import settings
from django.utils import timezone

# Colour constants (Discord uses decimal int, Slack uses hex string)
COLORS = {
    'product.created':    {'discord': 0x22C55E, 'slack': '#22C55E'},   # green
    'schematic.uploaded': {'discord': 0x06B6D4, 'slack': '#06B6D4'},   # cyan
    'report.filed':       {'discord': 0xEF4444, 'slack': '#EF4444'},   # red
    'user.badge_earned':  {'discord': 0xEAB308, 'slack': '#EAB308'},   # yellow
    'recipe.created':     {'discord': 0xEC4899, 'slack': '#EC4899'},   # pink
}


def build_payload(platform, event_type, context):
    """Route to the correct platform formatter."""
    if platform == 'discord':
        return _build_discord(event_type, context)
    elif platform == 'slack':
        return _build_slack(event_type, context)
    raise ValueError(f'Unknown platform: {platform}')


# ── Discord ──────────────────────────────────────────────────────────

def _build_discord(event_type, ctx):
    color = COLORS.get(event_type, {}).get('discord', 0x888888)
    site_url = getattr(settings, 'SITE_URL', '')
    now = timezone.now().isoformat()

    title, description, url, fields = _common_parts(event_type, ctx, site_url)

    embed = {
        'title': title,
        'description': description,
        'color': color,
        'timestamp': now,
        'footer': {'text': 'Junkbin.io'},
    }
    if url:
        embed['url'] = url
    if fields:
        embed['fields'] = [
            {'name': f['name'], 'value': f['value'], 'inline': True}
            for f in fields
        ]

    return {
        'username': 'Junkbin',
        'embeds': [embed],
    }


# ── Slack ────────────────────────────────────────────────────────────

def _build_slack(event_type, ctx):
    color = COLORS.get(event_type, {}).get('slack', '#888888')
    site_url = getattr(settings, 'SITE_URL', '')

    title, description, url, fields = _common_parts(event_type, ctx, site_url)

    link_text = f'<{url}|{title}>' if url else title

    blocks = [
        {
            'type': 'header',
            'text': {'type': 'plain_text', 'text': title, 'emoji': True},
        },
        {
            'type': 'section',
            'text': {'type': 'mrkdwn', 'text': description},
        },
    ]

    if fields:
        blocks.append({
            'type': 'section',
            'fields': [
                {'type': 'mrkdwn', 'text': f'*{f["name"]}*\n{f["value"]}'}
                for f in fields[:10]
            ],
        })

    if url:
        blocks.append({
            'type': 'context',
            'elements': [
                {'type': 'mrkdwn', 'text': f':link: {link_text}'},
            ],
        })

    return {
        'text': f'{title}: {description}',
        'attachments': [{'color': color, 'blocks': blocks}],
    }


# ── Shared ───────────────────────────────────────────────────────────

def _common_parts(event_type, ctx, site_url):
    """Return (title, description, url, fields) for any event."""

    if event_type == 'product.created':
        name = ctx.get('name', ctx.get('model_number', 'Unknown'))
        manufacturer = ctx.get('manufacturer', '')
        slug = ctx.get('slug', '')
        user = ctx.get('created_by', 'Someone')
        url = f'{site_url}/products/{slug}' if slug else ''
        return (
            'New Product Added',
            f'**{manufacturer} {name}** was added by {user}.',
            url,
            [
                {'name': 'Manufacturer', 'value': manufacturer},
                {'name': 'Model', 'value': ctx.get('model_number', '')},
            ],
        )

    elif event_type == 'schematic.uploaded':
        title_text = ctx.get('title', 'Untitled')
        product_name = ctx.get('product_name', '')
        user = ctx.get('uploaded_by', 'Someone')
        slug = ctx.get('product_slug', '')
        url = f'{site_url}/products/{slug}' if slug else ''
        return (
            'Schematic Uploaded',
            f'**{title_text}** uploaded for {product_name} by {user}.',
            url,
            [
                {'name': 'Type', 'value': ctx.get('schematic_type', '')},
                {'name': 'Product', 'value': product_name},
            ],
        )

    elif event_type == 'report.filed':
        reason = ctx.get('reason', 'Unknown')
        content_type = ctx.get('content_type', '')
        reporter = ctx.get('reporter', 'Anonymous')
        return (
            'Report Filed',
            f'A **{reason}** report was filed by {reporter} on a {content_type}.',
            '',
            [
                {'name': 'Reason', 'value': reason},
                {'name': 'Content', 'value': content_type},
            ],
        )

    elif event_type == 'user.badge_earned':
        username = ctx.get('username', 'Someone')
        badges = ctx.get('badge_names', [])
        badge_str = ', '.join(badges) if badges else 'a badge'
        return (
            'Badge Earned',
            f'**{username}** earned: {badge_str}',
            '',
            [{'name': 'Badges', 'value': badge_str}],
        )

    elif event_type == 'recipe.created':
        name = ctx.get('name', 'Untitled')
        user = ctx.get('created_by', 'Someone')
        slug = ctx.get('slug', '')
        url = f'{site_url}/recipes/{slug}' if slug else ''
        return (
            'New Recipe',
            f'**{name}** was created by {user}.',
            url,
            [
                {'name': 'Difficulty', 'value': ctx.get('difficulty', '')},
                {'name': 'Category', 'value': ctx.get('category', '')},
            ],
        )

    return (event_type, str(ctx), '', [])
