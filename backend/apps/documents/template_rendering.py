"""Validated template content and the shared PDF renderer for D4 (RF-PLA-009)."""

import html
import json
import re
from copy import deepcopy
from io import BytesIO

from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4, LEGAL, LETTER, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

from apps.common.exceptions import DomainError
from apps.documents.field_catalog import FIELD_TAG_CODES
from apps.documents.models import DocumentTemplate

_MARKER = re.compile(r"{{\s*([A-Za-z0-9_.-]+)\s*}}")
_PAGE_SIZES = {
    DocumentTemplate.PageSize.LETTER: LETTER,
    DocumentTemplate.PageSize.LEGAL: LEGAL,
    DocumentTemplate.PageSize.A4: A4,
}
_ALIGNMENTS = {
    "left": TA_LEFT,
    "center": TA_CENTER,
    "right": TA_RIGHT,
    "justify": TA_JUSTIFY,
}
_MARKS = {"bold", "italic", "underline"}


def _validate_markers(text):
    markers = _MARKER.findall(text)
    unknown = [marker for marker in markers if marker not in FIELD_TAG_CODES]
    if unknown:
        raise DomainError(f"El marcador '{unknown[0]}' no permitido.")
    return markers


def normalize_template_content(*, content_format, content):
    """Validate content and return its stable database representation."""
    if content_format == DocumentTemplate.ContentFormat.PLAIN:
        if not isinstance(content, str):
            raise DomainError("El contenido plain debe ser texto.")
        _validate_markers(content)
        return content.strip()
    if content_format != DocumentTemplate.ContentFormat.RICH:
        raise DomainError("El formato de contenido indicado no es valido.")
    if not isinstance(content, dict) or content.get("type") != "doc" or content.get("version") != 1:
        raise DomainError("El contenido rich debe ser un documento estructurado version 1.")
    blocks = content.get("content")
    if not isinstance(blocks, list):
        raise DomainError("El documento rich debe contener una lista de bloques.")
    normalized = deepcopy(content)
    for block in normalized["content"]:
        if not isinstance(block, dict) or block.get("type") not in {"paragraph", "heading"}:
            raise DomainError("El contenido rich contiene un bloque no permitido.")
        if block.get("align", "left") not in _ALIGNMENTS:
            raise DomainError("La alineacion del bloque no es valida.")
        if block["type"] == "heading" and block.get("level", 1) not in {1, 2, 3}:
            raise DomainError("El nivel del titulo no es valido.")
        nodes = block.get("content", [])
        if not isinstance(nodes, list):
            raise DomainError("El bloque rich debe contener una lista de texto.")
        for node in nodes:
            if (
                not isinstance(node, dict)
                or node.get("type") != "text"
                or not isinstance(node.get("text"), str)
            ):
                raise DomainError("El contenido rich contiene un nodo no permitido.")
            marks = node.get("marks", [])
            if not isinstance(marks, list) or any(mark not in _MARKS for mark in marks):
                raise DomainError("El texto rich contiene un formato no permitido.")
            _validate_markers(node["text"])
    return json.dumps(normalized, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


def public_template_content(*, content_format, stored_content):
    if content_format == DocumentTemplate.ContentFormat.RICH:
        try:
            return json.loads(stored_content or "{}")
        except json.JSONDecodeError as exc:
            raise DomainError("El contenido rich almacenado no es valido.") from exc
    return stored_content or ""


def _replace_markers(text, mapping):
    markers = _validate_markers(text)
    return _MARKER.sub(lambda match: str(mapping.get(match.group(1), "")), text), markers


def _inline_markup(nodes, mapping):
    parts = []
    markers = []
    for node in nodes:
        rendered, node_markers = _replace_markers(node["text"], mapping)
        markers.extend(node_markers)
        rendered = html.escape(rendered).replace("\n", "<br/>")
        for mark, tag in (("bold", "b"), ("italic", "i"), ("underline", "u")):
            if mark in node.get("marks", []):
                rendered = f"<{tag}>{rendered}</{tag}>"
        parts.append(rendered)
    return "".join(parts) or "&#160;", markers


def _flowables(*, content_format, stored_content, mapping, appendix_lines):
    styles = getSampleStyleSheet()
    flowables = []
    markers = []
    if content_format == DocumentTemplate.ContentFormat.PLAIN:
        rendered, markers = _replace_markers(stored_content or "", mapping)
        for paragraph in rendered.splitlines() or [""]:
            flowables.append(Paragraph(html.escape(paragraph) or "&#160;", styles["BodyText"]))
            flowables.append(Spacer(1, 8))
    else:
        document = public_template_content(
            content_format=content_format, stored_content=stored_content
        )
        for block in document.get("content", []):
            markup, block_markers = _inline_markup(block.get("content", []), mapping)
            markers.extend(block_markers)
            level = block.get("level", 1)
            base = styles[f"Heading{level}"] if block["type"] == "heading" else styles["BodyText"]
            style = ParagraphStyle(
                f"d4-{len(flowables)}",
                parent=base,
                alignment=_ALIGNMENTS[block.get("align", "left")],
            )
            flowables.extend([Paragraph(markup, style), Spacer(1, 8)])
    for line in appendix_lines or []:
        flowables.extend(
            [Paragraph(html.escape(str(line)) or "&#160;", styles["BodyText"]), Spacer(1, 5)]
        )
    return flowables, markers


def render_template_pdf(
    *,
    content_format,
    stored_content,
    mapping,
    institution_name,
    page_size,
    orientation,
    margins,
    footer_text="",
    signature_blocks=None,
    appendix_lines=None,
    title="",
):
    """Render preview and official issuance through the exact same engine."""
    size = _PAGE_SIZES.get(page_size)
    if size is None:
        raise DomainError("El tamano de pagina no es valido.")
    if orientation == DocumentTemplate.Orientation.LANDSCAPE:
        size = landscape(size)
    elif orientation != DocumentTemplate.Orientation.PORTRAIT:
        raise DomainError("La orientacion de pagina no es valida.")
    buffer = BytesIO()
    flowables, markers = _flowables(
        content_format=content_format,
        stored_content=stored_content,
        mapping=mapping,
        appendix_lines=appendix_lines,
    )
    if title:
        flowables[0:0] = [
            Paragraph(html.escape(title), getSampleStyleSheet()["Title"]),
            Spacer(1, 14),
        ]
    signatures = signature_blocks or []
    for signature in signatures:
        flowables.extend(
            [
                Spacer(1, 34),
                Paragraph("____________________________", getSampleStyleSheet()["BodyText"]),
                Paragraph(html.escape(signature["name"]), getSampleStyleSheet()["BodyText"]),
                Paragraph(html.escape(signature["title"]), getSampleStyleSheet()["BodyText"]),
            ]
        )

    def draw_page(canvas, _document):
        canvas.saveState()
        canvas.setFont("Helvetica-Bold", 10)
        canvas.drawString(margins["left"], size[1] - 30, institution_name)
        if footer_text:
            canvas.setFont("Helvetica", 8)
            canvas.drawString(margins["left"], 24, footer_text[:180])
        canvas.restoreState()

    document = SimpleDocTemplate(
        buffer,
        pagesize=size,
        pageCompression=0,
        topMargin=margins["top"],
        rightMargin=margins["right"],
        bottomMargin=margins["bottom"],
        leftMargin=margins["left"],
        title="Vista previa documental",
        author=institution_name,
    )
    document.build(flowables, onFirstPage=draw_page, onLaterPages=draw_page)
    return buffer.getvalue(), markers
