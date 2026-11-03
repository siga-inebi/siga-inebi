"""
Wireframe de la credencial estudiantil (RF-CRE-002).

Una sola fuente de verdad para el material imprimible: el PNG individual, cada
imagen del ZIP y cada tarjeta del PDF salen de ``render_card_image``. Antes la
tarjeta se armaba en el navegador con una ventana emergente y el encabezado y
pie de pagina del navegador; el tamano dependia de la impresora.

La tarjeta es deliberadamente un esqueleto: 96 x 54 mm (16:9) a 300 dpi, fondo
transparente y una guia de corte fina. Quien produce los carnes pone el diseno
encima; aqui solo se fija que datos van y donde. Los datos salen
exclusivamente de ``CredentialPrintContent`` (nombre, foto, grado, seccion,
ciclo e institucion): ni codigo estudiantil, ni salud, ni domicilio.

El cargador de foto y el generador de QR se inyectan para poder probar el
render sin base de datos ni almacenamiento.
"""

from dataclasses import dataclass
from io import BytesIO
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

from apps.common.qr import generate_qr_png

CARD_WIDTH_MM = 96
CARD_HEIGHT_MM = 54
CARD_DPI = 300
CARD_SIZE = (
    round(CARD_WIDTH_MM / 25.4 * CARD_DPI),
    round(CARD_HEIGHT_MM / 25.4 * CARD_DPI),
)  # (1134, 638)

#: Tarjetas por hoja carta: 2 columnas x 4 filas a tamano real.
PDF_COLUMNS = 2
PDF_ROWS = 4
CARDS_PER_PAGE = PDF_COLUMNS * PDF_ROWS
PDF_GAP_MM = 6
CROP_MARK_MM = 3
CROP_MARK_OFFSET_MM = 1

INK = (0, 0, 0, 255)
MUTED = (90, 90, 90, 255)
GUIDE = (150, 150, 150, 255)

_PADDING = 40
_PHOTO_BOX = (_PADDING, 150, _PADDING + 330, 150 + 396)  # 295 x 354 escalado
_QR_SIZE = 300
_QR_BOX = (CARD_SIZE[0] - _PADDING - _QR_SIZE, 170)
_TEXT_LEFT = _PHOTO_BOX[2] + 36
_TEXT_RIGHT = _QR_BOX[0] - 30

# Las imagenes slim de Python no traen fuentes del sistema. ReportLab (ya
# dependencia del proyecto) incluye Bitstream Vera, la base de DejaVu: se
# prefiere DejaVu si existe y, si no hay ninguna, la fuente integrada de Pillow.
_FONT_CANDIDATES = {
    False: ("DejaVuSans.ttf", "Vera.ttf"),
    True: ("DejaVuSans-Bold.ttf", "VeraBd.ttf"),
}
_FONT_DIRECTORIES = (
    Path("/usr/share/fonts/truetype/dejavu"),
    Path("/usr/share/fonts/TTF"),
)


def _font_paths(bold):
    directories = list(_FONT_DIRECTORIES)
    try:
        import reportlab

        directories.append(Path(reportlab.__file__).parent / "fonts")
    except ImportError:  # pragma: no cover - reportlab es dependencia base
        pass
    for directory in directories:
        for name in _FONT_CANDIDATES[bold]:
            candidate = directory / name
            if candidate.is_file():
                yield candidate


def load_font(size, *, bold=False):
    """A TrueType font of ``size`` px, degrading to Pillow's built-in font."""
    for path in _font_paths(bold):
        try:
            return ImageFont.truetype(str(path), size)
        except OSError:
            continue
    return ImageFont.load_default(size=size)


def load_student_photo(student):
    """Bytes of ``student.photo`` from storage, or ``None`` if absent or unreadable."""
    photo = getattr(student, "photo", None)
    if not photo:
        return None
    try:
        with photo.open("rb") as handle:
            return handle.read()
    except (OSError, ValueError):
        return None


@dataclass
class RenderedCard:
    """One rendered card: the PNG and the name it gets inside a ZIP."""

    filename: str
    png: bytes


def _text_width(draw, text, font):
    left, _top, right, _bottom = draw.textbbox((0, 0), text, font=font)
    return right - left


def _wrap(draw, text, font, width, max_lines):
    """Greedy word wrap to ``max_lines``; the last line is ellipsized if needed."""
    words = text.split()
    lines = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if _text_width(draw, candidate, font) <= width or not current:
            current = candidate
        else:
            lines.append(current)
            current = word
    if current:
        lines.append(current)
    if len(lines) > max_lines:
        lines = [*lines[: max_lines - 1], " ".join(lines[max_lines - 1 :])]
    last = lines[-1] if lines else ""
    while last and _text_width(draw, last, font) > width:
        last = last[:-2] + "…" if len(last) > 1 else ""
    if lines:
        lines[-1] = last
    return lines


def _fit(draw, text, sizes, width, max_lines, *, bold=False):
    """
    The largest of ``sizes`` at which ``text`` fits ``max_lines`` without being
    cut; at the smallest size it is wrapped and ellipsized as a last resort.
    """
    for size in sizes:
        font = load_font(size, bold=bold)
        lines = _wrap(draw, text, font, width, max_lines)
        if " ".join(lines) == " ".join(text.split()):
            return font, lines
    return font, lines


def _draw_dashed_rectangle(draw, box, *, dash=18, gap=12, width=3, fill=GUIDE):
    left, top, right, bottom = box
    for start in range(left, right, dash + gap):
        end = min(start + dash, right)
        draw.line([(start, top), (end, top)], fill=fill, width=width)
        draw.line([(start, bottom), (end, bottom)], fill=fill, width=width)
    for start in range(top, bottom, dash + gap):
        end = min(start + dash, bottom)
        draw.line([(left, start), (left, end)], fill=fill, width=width)
        draw.line([(right, start), (right, end)], fill=fill, width=width)


def _draw_photo(card, draw, photo_bytes):
    left, top, right, bottom = _PHOTO_BOX
    size = (right - left, bottom - top)
    photo = None
    if photo_bytes:
        try:
            photo = Image.open(BytesIO(photo_bytes))
            photo.load()
        except (OSError, ValueError):
            photo = None
    if photo is None:
        _draw_dashed_rectangle(draw, _PHOTO_BOX)
        font = load_font(44, bold=True)
        label = "FOTO"
        width = _text_width(draw, label, font)
        draw.text(
            (left + (size[0] - width) / 2, top + size[1] / 2),
            label,
            font=font,
            fill=GUIDE,
            anchor="lm",
        )
        return
    fitted = ImageOps.fit(photo.convert("RGBA"), size, method=Image.Resampling.LANCZOS)
    card.alpha_composite(fitted, (left, top))
    draw.rectangle(_PHOTO_BOX, outline=GUIDE, width=2)


def _draw_qr(card, qr_png):
    qr = Image.open(BytesIO(qr_png)).convert("RGBA")
    qr = qr.resize((_QR_SIZE, _QR_SIZE), Image.Resampling.NEAREST)
    card.alpha_composite(qr, _QR_BOX)


def render_card_image(content, qr_payload, *, qr_generator=generate_qr_png, photo_loader=None):
    """
    The card for ``content`` (a ``CredentialPrintContent``) as an RGBA image.

    ``qr_payload`` is the opaque identifier and nothing else (RNF-PRI-001):
    it goes straight to ``qr_generator`` and is never drawn as text.
    """
    photo_loader = photo_loader or load_student_photo
    card = Image.new("RGBA", CARD_SIZE, (0, 0, 0, 0))
    draw = ImageDraw.Draw(card)

    # Guia de corte: el borde exacto de 96 x 54 mm.
    draw.rectangle((0, 0, CARD_SIZE[0] - 1, CARD_SIZE[1] - 1), outline=GUIDE, width=2)

    institution_font, institution = _fit(
        draw, content.institution_name, (40, 34, 28), CARD_SIZE[0] - 2 * _PADDING, 1, bold=True
    )
    if institution:
        draw.text(
            (CARD_SIZE[0] / 2, 70),
            institution[0],
            font=institution_font,
            fill=INK,
            anchor="mm",
        )
    draw.line(
        [(_PADDING, 118), (CARD_SIZE[0] - _PADDING, 118)],
        fill=GUIDE,
        width=2,
    )

    _draw_photo(card, draw, photo_loader(content.student))

    text_width = _TEXT_RIGHT - _TEXT_LEFT
    y = _PHOTO_BOX[1] + 10
    name_font, name_lines = _fit(draw, content.full_name, (42, 36, 30), text_width, 3, bold=True)
    for line in name_lines:
        draw.text((_TEXT_LEFT, y), line, font=name_font, fill=INK)
        y += round(name_font.size * 1.28)
    y += 24
    detail_font = load_font(32)
    placement = f"{content.grade_name} · Sección {content.section_name}"
    for line in _wrap(draw, placement, detail_font, text_width, 2):
        draw.text((_TEXT_LEFT, y), line, font=detail_font, fill=MUTED)
        y += 44
    y += 12
    for line in _wrap(draw, f"Ciclo {content.academic_cycle_name}", detail_font, text_width, 2):
        draw.text((_TEXT_LEFT, y), line, font=detail_font, fill=MUTED)
        y += 44

    _draw_qr(card, qr_generator(data=qr_payload))
    return card


def render_card_png(content, qr_payload, *, qr_generator=generate_qr_png, photo_loader=None):
    """``render_card_image`` encoded as PNG, with the 300 dpi the size assumes."""
    image = render_card_image(
        content, qr_payload, qr_generator=qr_generator, photo_loader=photo_loader
    )
    output = BytesIO()
    image.save(output, format="PNG", dpi=(CARD_DPI, CARD_DPI), optimize=True)
    return output.getvalue()


def _crop_marks(pdf, x, y, width, height):
    """Short marks outside each corner, so cutting does not depend on the outline."""
    length = CROP_MARK_MM * mm
    offset = CROP_MARK_OFFSET_MM * mm
    for corner_x, direction_x in ((x, -1), (x + width, 1)):
        for corner_y, direction_y in ((y, -1), (y + height, 1)):
            pdf.line(
                corner_x + direction_x * offset,
                corner_y,
                corner_x + direction_x * (offset + length),
                corner_y,
            )
            pdf.line(
                corner_x,
                corner_y + direction_y * offset,
                corner_x,
                corner_y + direction_y * (offset + length),
            )


def render_cards_pdf(cards):
    """
    Carta, 2 x 4 tarjetas por hoja a tamano real (96 x 54 mm), con marcas de corte.

    ``cards`` are PNG bytes from ``render_card_png``; the PDF embeds them as
    they are so the PNG and the printed card can never drift apart.
    """
    cards = list(cards)
    output = BytesIO()
    pdf = canvas.Canvas(output, pagesize=LETTER)
    pdf.setTitle("Carnés estudiantiles")
    page_width, page_height = LETTER
    card_width = CARD_WIDTH_MM * mm
    card_height = CARD_HEIGHT_MM * mm
    gap = PDF_GAP_MM * mm
    grid_width = PDF_COLUMNS * card_width + (PDF_COLUMNS - 1) * gap
    grid_height = PDF_ROWS * card_height + (PDF_ROWS - 1) * gap
    left = (page_width - grid_width) / 2
    top = (page_height + grid_height) / 2

    for index, png in enumerate(cards):
        position = index % CARDS_PER_PAGE
        if index and position == 0:
            pdf.showPage()
        column = position % PDF_COLUMNS
        row = position // PDF_COLUMNS
        x = left + column * (card_width + gap)
        y = top - (row + 1) * card_height - row * gap
        pdf.drawImage(
            ImageReader(BytesIO(png)), x, y, width=card_width, height=card_height, mask="auto"
        )
        pdf.setLineWidth(0.3)
        pdf.setStrokeGray(0.3)
        _crop_marks(pdf, x, y, card_width, card_height)
    pdf.showPage()
    pdf.save()
    return output.getvalue()
