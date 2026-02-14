"""
Content filter for Junkbin.io

Lightweight word-boundary regex filter for slurs and hate speech.
Focused on severe/targeted language — this is an electronics repair
community, not a children's site, so mild profanity is allowed.
"""
import re

# Leet-speak substitution map
_LEET_MAP = str.maketrans({
    '@': 'a',
    '0': 'o',
    '1': 'i',
    '3': 'e',
    '4': 'a',
    '5': 's',
    '7': 't',
    '$': 's',
    '!': 'i',
})

# Blocked terms — slurs, hate speech, severe targeted language.
# Each entry is compiled as a case-insensitive word-boundary regex.
_BLOCKED_TERMS = [
    # Racial slurs
    r'n[i!1]gg[e3]r',
    r'n[i!1]gg[a@4]',
    r'sp[i!1]c',
    r'ch[i!1]nk',
    r'g[o0][o0]k',
    r'k[i!1]ke',
    r'w[e3]tb[a@4]ck',
    r'c[o0][o0]n',
    r'r[a@4]gh[e3][a@4]d',
    r't[o0]w[e3]lh[e3][a@4]d',
    r'b[e3][a@4]n[e3]r',
    # Anti-LGBTQ slurs
    r'f[a@4]gg[o0]t',
    r'f[a@4]g',
    r'tr[a@4]nny',
    r'd[y]ke',
    # Gendered slurs (severe)
    r'c[u]nt',
    # Hate-adjacent
    r'wh[i!1]t[e3]\s*p[o0]w[e3]r',
    r'h[e3][i!1]l\s*h[i!1]tl[e3]r',
    r'g[a@4]s\s*th[e3]\s*j[e3]ws',
    r's[i!1][e3]g\s*h[e3][i!1]l',
    # Calls to violence
    r'k[i!1]ll\s*y[o0][u]rs[e3]lf',
    r'kys',
]

_BLOCKED_PATTERNS = [
    re.compile(r'\b' + term + r'\b', re.IGNORECASE)
    for term in _BLOCKED_TERMS
]


def _normalize(text: str) -> str:
    """Normalize text for matching: lowercase + leet-speak substitution."""
    return text.lower().translate(_LEET_MAP)


def check_content(text: str) -> tuple[bool, str | None]:
    """
    Check text against the blocked word list.

    Returns:
        (is_clean, matched_term) — is_clean is True if no blocked terms found.
        matched_term is the pattern that matched (for logging), or None.
    """
    normalized = _normalize(text)

    for pattern in _BLOCKED_PATTERNS:
        match = pattern.search(normalized)
        if match:
            return False, match.group()

    return True, None
