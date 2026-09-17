"""
QR encoding for opaque identifiers (RNF-PRI-001).

The QR a credential carries must encode nothing but the opaque token itself
(``docs/requirements/openspec/credencial-estudiantil.md``): no name, no
student code, no academic or health data. The one way to guarantee that is to
never let this module see anything but the string to encode -- it takes a
plain value, never a model or a serialized payload, so there is nothing here
that could leak a field its caller forgot to strip.
"""

import base64
import io

import qrcode


def generate_qr_png(*, data):
    """The QR code for ``data``, as PNG bytes."""
    image = qrcode.make(data)
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def generate_qr_png_base64(*, data):
    """``generate_qr_png``, base64-encoded for embedding in a JSON response."""
    return base64.b64encode(generate_qr_png(data=data)).decode("ascii")
