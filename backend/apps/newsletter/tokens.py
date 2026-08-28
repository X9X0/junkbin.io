"""
Signed, non-expiring tokens for one-click email unsubscribe links (RFC 8058).

Tokens never expire - an old email in someone's inbox should still be able
to unsubscribe them years later - so this uses a plain Signer (not
TimestampSigner). The signature is keyed to SECRET_KEY, so a token can't be
forged or altered to target a different subscriber/user.
"""
from django.core import signing

UNSUBSCRIBE_SALT = 'newsletter.unsubscribe'


def make_unsubscribe_token(kind, identifier):
    """kind is 'subscriber' or 'user'; identifier is that row's UUID (as str)."""
    return signing.Signer(salt=UNSUBSCRIBE_SALT).sign(f'{kind}:{identifier}')


def parse_unsubscribe_token(token):
    """Returns (kind, identifier). Raises django.core.signing.BadSignature
    if the token is invalid or was tampered with."""
    value = signing.Signer(salt=UNSUBSCRIBE_SALT).unsign(token)
    kind, identifier = value.split(':', 1)
    return kind, identifier
