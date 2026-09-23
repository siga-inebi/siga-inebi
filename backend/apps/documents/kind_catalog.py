"""
Seed values for the institutional document-type catalogue (RNF-MAN-001).

These are the three types the product shipped with while they lived in a
``TextChoices`` enum on ``DocumentTemplate``. They are kept here only so an
institution starts with a usable catalogue instead of an empty one: they are
ordinary rows once created, and an administrator may relabel, deactivate or
extend them without touching this file or redeploying. Nothing in the domain
reads a type from here at runtime -- ``apps.documents.services`` always reads
``DocumentKind`` rows.
"""

DEFAULT_DOCUMENT_KINDS = (
    ("certificate", "Certificado"),
    ("report", "Reporte"),
    ("other", "Otro"),
)

DEFAULT_DOCUMENT_KIND_CODE = "other"
