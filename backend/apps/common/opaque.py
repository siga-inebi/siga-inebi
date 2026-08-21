"""
Opaque identifiers handed out to clients (``docs/architecture/api-conventions.md``).

An opaque identifier carries no meaning: it is not derived from the record it
points at, and holding one tells you nothing about the next. That is the whole
point of the QR credential — anyone can photograph a printed code, so what the
code encodes must not identify its bearer to whoever scans it.

``secrets`` is used instead of ``random`` on purpose. ``random`` is seeded
predictably and its sequence is reconstructible from a handful of observed
values, which for an identifier that grants a movement is the same as having
no protection at all.

Generation is deliberately a plain callable rather than a class: callers inject
it (``generate_identifier=``) so a test can pin the value it expects instead of
patching module globals, and a future domain that needs a different alphabet or
length can pass its own without this module knowing about it.
"""

import secrets

DEFAULT_ENTROPY_BYTES = 32


def generate_opaque_identifier(*, entropy_bytes=DEFAULT_ENTROPY_BYTES):
    """
    A URL-safe token carrying ``entropy_bytes`` bytes of entropy.

    The result is longer than ``entropy_bytes`` because base64 needs about
    four characters per three bytes: the default 32 bytes render as 43
    characters.
    """
    return secrets.token_urlsafe(entropy_bytes)
