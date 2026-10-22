import base64

import pytest

from apps.common.exceptions import DomainError
from apps.documents.models import DocumentTemplate
from apps.documents.services import create_document_template, preview_document_template
from apps.documents.template_rendering import normalize_template_content, render_template_pdf
from tests.factories.academic import InstitutionFactory

pytestmark = [pytest.mark.unit, pytest.mark.django_db]


RICH_CONTENT = {
    "type": "doc",
    "version": 1,
    "content": [
        {
            "type": "heading",
            "level": 1,
            "align": "center",
            "content": [{"type": "text", "text": "Constancia"}],
        },
        {
            "type": "paragraph",
            "align": "justify",
            "content": [
                {"type": "text", "text": "Se certifica a ", "marks": []},
                {
                    "type": "text",
                    "text": "{{student.full_name}}",
                    "marks": ["bold"],
                },
            ],
        },
    ],
}


def test_rich_template_keeps_layout_in_immutable_version():
    template = create_document_template(
        institution=InstitutionFactory(),
        name="Constancia rica",
        code="RICH",
        content_format=DocumentTemplate.ContentFormat.RICH,
        content=RICH_CONTENT,
        page_size=DocumentTemplate.PageSize.A4,
        orientation=DocumentTemplate.Orientation.LANDSCAPE,
        margin_top=36,
        margin_right=42,
        margin_bottom=48,
        margin_left=54,
        footer_text="Documento de prueba",
        signature_blocks=[{"name": "Dirección", "title": "Director(a)"}],
    )

    version = template.versions.get()
    assert version.content_format == "rich"
    assert version.page_size == "a4"
    assert version.orientation == "landscape"
    assert version.margin_top == 36
    assert version.footer_text == "Documento de prueba"
    assert version.signature_blocks == [{"name": "Dirección", "title": "Director(a)"}]


def test_preview_returns_real_pdf_from_rich_content():
    template = create_document_template(
        institution=InstitutionFactory(),
        name="Constancia rica",
        code="RICH",
        content_format="rich",
        content=RICH_CONTENT,
    )

    preview = preview_document_template(
        template=template, payload={"student.full_name": "Ana Pérez"}
    )

    assert preview["content_type"] == "application/pdf"
    assert base64.b64decode(preview["pdf_base64"]).startswith(b"%PDF-")
    assert preview["markers"] == ["student.full_name"]
    assert preview["content_format"] == "rich"


def test_rich_template_rejects_unknown_nodes_and_marks():
    invalid_node = {"type": "doc", "version": 1, "content": [{"type": "table"}]}
    with pytest.raises(DomainError, match="bloque no permitido"):
        normalize_template_content(content_format="rich", content=invalid_node)

    invalid_mark = {
        "type": "doc",
        "version": 1,
        "content": [
            {
                "type": "paragraph",
                "content": [{"type": "text", "text": "X", "marks": ["script"]}],
            }
        ],
    }
    with pytest.raises(DomainError, match="formato no permitido"):
        normalize_template_content(content_format="rich", content=invalid_mark)


def test_shared_renderer_honours_page_configuration():
    stored = normalize_template_content(content_format="rich", content=RICH_CONTENT)
    pdf, markers = render_template_pdf(
        content_format="rich",
        stored_content=stored,
        mapping={"student.full_name": "Ana Pérez"},
        institution_name="INEBI",
        page_size="letter",
        orientation="portrait",
        margins={"top": 54, "right": 54, "bottom": 54, "left": 54},
        footer_text="Pie institucional",
        signature_blocks=[{"name": "Dirección", "title": "Director(a)"}],
    )

    assert pdf.startswith(b"%PDF-")
    assert pdf.rstrip().endswith(b"%%EOF")
    assert markers == ["student.full_name"]
