from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest
from django.db import close_old_connections

from apps.common.exceptions import DomainError
from apps.documents.models import DocumentTemplate
from apps.documents.services import create_document_template
from tests.factories.academic import InstitutionFactory


@pytest.mark.postgres
@pytest.mark.integration
@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize("replacing", [False, True])
def test_concurrent_publication_keeps_one_active_use(replacing):
    institution = InstitutionFactory()
    original = create_document_template(
        institution=institution,
        name="Setup",
        code="SETUP",
        issuance_use="study_certificate" if replacing else "none",
    )
    start = Barrier(2)

    def publish(code):
        close_old_connections()
        try:
            start.wait(timeout=10)
            try:
                create_document_template(
                    institution=institution,
                    name=code,
                    code=code,
                    issuance_use="study_certificate",
                    replaces_template_id=original.public_id if replacing else None,
                )
                return "created"
            except DomainError:
                return "conflict"
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(publish, ["ONE", "TWO"]))
    assert sorted(outcomes) == ["conflict", "created"]
    assert (
        DocumentTemplate.objects.filter(
            institution=institution, issuance_use="study_certificate", is_active=True
        ).count()
        == 1
    )
