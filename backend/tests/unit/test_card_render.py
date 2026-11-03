"""
RF-CRE-002 — wireframe imprimible de la credencial (``apps.attendance.card_render``).

Sin base de datos: el contenido es un objeto plano y el cargador de foto y el
generador de QR se inyectan.
"""

import re
from io import BytesIO
from types import SimpleNamespace

import pytest
from PIL import Image

from apps.attendance import card_render
from apps.common.qr import generate_qr_png
from tests.pdf_assertions import assert_pdf_structurally_valid

pytestmark = pytest.mark.unit


def _content(**overrides):
    values = {
        "student": SimpleNamespace(photo=None),
        "full_name": "Ana Pérez",
        "grade_name": "Primero Básico",
        "section_name": "A",
        "academic_cycle_name": "2026",
        "institution_name": "Instituto Demo",
        "photo_url": None,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def _red_photo():
    buffer = BytesIO()
    Image.new("RGB", (295, 354), (255, 0, 0)).save(buffer, format="JPEG")
    return buffer.getvalue()


def _png(**kwargs):
    kwargs.setdefault("photo_loader", lambda _student: None)
    return card_render.render_card_png(_content(), "token-opaco", **kwargs)


def _page_count(pdf):
    return len(re.findall(rb"/Type /Page(?!s)", pdf))


def test_card_is_96_by_54_mm_at_300_dpi_with_a_transparent_background():
    image = Image.open(BytesIO(_png()))

    assert image.format == "PNG"
    assert image.mode == "RGBA"
    assert image.size == (1134, 638) == card_render.CARD_SIZE
    assert image.info["dpi"] == pytest.approx((300, 300), abs=0.01)
    # Fondo transparente: lejos de cualquier texto, la tarjeta no tiene tinta.
    assert image.getpixel((card_render.CARD_SIZE[0] // 2, 600))[3] == 0
    # Guia de corte en el borde exacto.
    assert image.getpixel((0, card_render.CARD_SIZE[1] // 2))[3] == 255


def test_without_photo_the_box_is_a_dashed_placeholder():
    image = Image.open(BytesIO(_png()))
    left, top, _right, _bottom = card_render._PHOTO_BOX

    assert image.getpixel((left + 20, top + 20))[3] == 0
    assert image.getpixel((left + 5, top))[3] == 255  # trazo
    assert image.getpixel((left + 24, top))[3] == 0  # hueco entre trazos


def test_with_photo_the_box_shows_it():
    image = Image.open(BytesIO(_png(photo_loader=lambda _student: _red_photo())))
    left, top, _right, _bottom = card_render._PHOTO_BOX

    red, green, blue, alpha = image.getpixel((left + 20, top + 20))
    assert alpha == 255
    assert red > 200 and green < 60 and blue < 60


def test_an_unreadable_photo_falls_back_to_the_placeholder():
    image = Image.open(BytesIO(_png(photo_loader=lambda _student: b"no es una imagen")))
    left, top, _right, _bottom = card_render._PHOTO_BOX

    assert image.getpixel((left + 20, top + 20))[3] == 0


def test_the_qr_encodes_only_the_payload_it_is_given():
    seen = []

    def qr_generator(*, data):
        seen.append(data)
        return generate_qr_png(data=data)

    _png(qr_generator=qr_generator)

    assert seen == ["token-opaco"]


def test_photo_loader_receives_the_student():
    student = SimpleNamespace(photo=None)
    received = []

    card_render.render_card_png(
        _content(student=student),
        "token",
        photo_loader=lambda value: received.append(value),
    )

    assert received == [student]


@pytest.mark.parametrize(("cards", "pages"), [(1, 1), (8, 1), (9, 2)])
def test_pdf_places_eight_cards_per_letter_page(cards, pages):
    png = _png()

    pdf = card_render.render_cards_pdf([png] * cards)

    assert_pdf_structurally_valid(pdf)
    assert _page_count(pdf) == pages
    assert b"/MediaBox [ 0 0 612 792 ]" in pdf


def test_file_stem_is_ascii_code_and_name():
    from apps.attendance.card_export import card_file_stem

    assert (
        card_file_stem(student_code="EST-2026-0001", full_name="Ána Pérez Ñúñez")
        == "EST-2026-0001_Ana-Perez-Nunez"
    )
