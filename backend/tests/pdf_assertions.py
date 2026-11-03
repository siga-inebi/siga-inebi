"""
Structural checks for the PDFs the documents domain generates.

QA4-PDF-01 (PR #595): a strict reader must find the cross-reference table at
``startxref`` and every object at the byte offset the table advertises,
otherwise it "repairs" the file or refuses to open it. The boleta test used to
carry these checks inline; they live here so every generated document is held
to the same bar.
"""


def assert_pdf_structurally_valid(pdf):
    assert pdf.startswith(b"%PDF-1."), "missing PDF header"
    assert pdf.rstrip().endswith(b"%%EOF"), "missing %%EOF marker"

    xref_offset = int(pdf.rsplit(b"startxref\n", 1)[1].splitlines()[0])
    assert pdf[xref_offset : xref_offset + 5] == b"xref\n", "startxref does not point at xref"

    xref_rows = pdf[xref_offset:].split(b"trailer\n", 1)[0].splitlines()
    first, count = (int(value) for value in xref_rows[1].split())
    assert first == 0
    entries = xref_rows[2:]
    assert len(entries) == count, "xref entry count does not match its header"
    assert entries[0].strip() == b"0000000000 65535 f"

    for number, row in enumerate(entries[1:], start=1):
        offset = int(row.split()[0])
        marker = f"{number} 0 obj".encode()
        assert pdf[offset : offset + len(marker)] == marker, f"object {number} not at its offset"

    trailer = pdf.rsplit(b"trailer\n", 1)[1]
    assert f"/Size {count}".encode() in trailer, "trailer /Size does not match xref"
