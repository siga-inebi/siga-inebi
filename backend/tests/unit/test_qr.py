"""
Codificacion del codigo QR de la credencial (RNF-PRI-001).

Sin base de datos a proposito: codificar un texto en un QR no depende de
ningun registro, y lo unico que hay que probar es la funcion pura.
"""

import base64

import pytest

from apps.common.qr import generate_qr_png, generate_qr_png_base64

pytestmark = [pytest.mark.unit]

PNG_MAGIC_BYTES = b"\x89PNG\r\n\x1a\n"


def test_generate_qr_png_returns_a_valid_png():
    image_bytes = generate_qr_png(data="opaque-token-abc123")

    assert image_bytes.startswith(PNG_MAGIC_BYTES)


def test_generate_qr_png_is_deterministic_for_the_same_input():
    first = generate_qr_png(data="opaque-token-abc123")
    second = generate_qr_png(data="opaque-token-abc123")

    assert first == second


def test_generate_qr_png_differs_for_different_input():
    """
    RNF-PRI-001: the encoded image is a pure function of what it's given.
    Two different opaque identifiers must never render into the same QR --
    if they did, scanning one could resolve to the wrong credential.
    """
    first = generate_qr_png(data="opaque-token-abc123")
    second = generate_qr_png(data="opaque-token-xyz789")

    assert first != second


def test_generate_qr_png_base64_decodes_to_the_same_png():
    image_bytes = generate_qr_png(data="opaque-token-abc123")

    encoded = generate_qr_png_base64(data="opaque-token-abc123")

    assert base64.b64decode(encoded) == image_bytes
