"""Tests for the requirement card parser, mapping tables and traceability backfill.

Standard library only, so it runs without the backend virtualenv:

    python3 -m unittest discover -s scripts/requirements -v
"""

import importlib.util
import os
import unittest

import implementation
import mapping
import parser
import scenarios


def _load_hyphenated(module_name, filename):
    """Import a CLI script whose filename is not a valid module name."""
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), filename)
    spec = importlib.util.spec_from_file_location(module_name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


backfill = _load_hyphenated("backfill_traceability", "backfill-traceability.py")

# A card exactly as pdftotext renders it, including the wrapped criterion.
SINGLE_CARD = """\
            Campo                                   Detalle

Código del requerimiento   RF-ASI-001

Nombre                     Captura mediada por operador

Fuente                     Documento de Especificación de Requerimientos

Usuario relacionado        Personal de control de ingreso y salida / Operador de
                           control

Historia de usuario        HU-17

Regla de negocio           RN-JOR-001

Prioridad                  Debe

Criterio de aceptación     El sistema debe determinar la ventana operativa diaria
                           habilitada para la recepción de eventos según el
                           calendario institucional.

Módulo                     Jornada Diaria y Estados

Estado                     Pendiente
"""

# Two cards separated by a form feed, with the second one's fields split across
# the page boundary. This is the shape that breaks a naive page-by-page parser.
CARD_ACROSS_PAGE_BREAK = """\
Código del requerimiento   RF-ASI-006

Nombre                     Autorización por tipo de movimiento
\f
            Campo                                   Detalle

Fuente                     Documento de Especificación de Requerimientos

Prioridad                  Debe

Criterio de aceptación     El sistema valida que el operador tenga permiso
\f
                           explícito para el tipo de movimiento solicitado.

Módulo                     Asistencia y Escaneo

Estado                     Pendiente
"""

CATALOGUE = """\
# Requirements Catalogue

## Functional Requirements

| ID | Descripcion original | Prioridad | Dominio | Estado de implementacion | Issue relacionado |
| --- | --- | --- | --- | --- | --- |
| RF-ASI-001 | Captura mediada por operador | Debe | attendance-capture | Not implemented | TBD |
| RF-JOR-005 | Deteccion de inconsistencias entre fuentes | Deberia | attendance-governance | Not implemented | TBD |

## Non-functional Requirements

| RNF-SEG-001 | Cookie de sesion con HttpOnly, Secure y SameSite | Debe | security-compliance | Not implemented | TBD |
"""


class ParseCardsTest(unittest.TestCase):
    def test_reads_every_field_of_a_card(self):
        (card,) = parser.parse_cards(SINGLE_CARD)

        self.assertEqual(card["id"], "RF-ASI-001")
        self.assertEqual(card["name"], "Captura mediada por operador")
        self.assertEqual(card["priority"], "Debe")
        self.assertEqual(card["user_story"], "HU-17")
        self.assertEqual(card["business_rule"], "RN-JOR-001")
        self.assertEqual(card["module"], "Jornada Diaria y Estados")
        self.assertEqual(card["status"], "Pendiente")

    def test_joins_wrapped_continuation_lines(self):
        (card,) = parser.parse_cards(SINGLE_CARD)

        self.assertEqual(
            card["acceptance_criteria"],
            "El sistema debe determinar la ventana operativa diaria habilitada "
            "para la recepción de eventos según el calendario institucional.",
        )
        self.assertEqual(
            card["actor"],
            "Personal de control de ingreso y salida / Operador de control",
        )

    def test_reassembles_a_card_split_across_page_breaks(self):
        (card,) = parser.parse_cards(CARD_ACROSS_PAGE_BREAK)

        self.assertEqual(card["id"], "RF-ASI-006")
        self.assertEqual(card["module"], "Asistencia y Escaneo")
        self.assertEqual(
            card["acceptance_criteria"],
            "El sistema valida que el operador tenga permiso explícito para el "
            "tipo de movimiento solicitado.",
        )

    def test_discards_the_repeated_campo_detalle_header(self):
        (card,) = parser.parse_cards(SINGLE_CARD)

        for value in card.values():
            self.assertNotIn("Campo", value)
            self.assertNotIn("Detalle", value)

    def test_skips_fragments_without_a_well_formed_id(self):
        self.assertEqual(parser.parse_cards("Código del requerimiento   RF-ASI\n"), [])


class SplitIdTest(unittest.TestCase):
    def test_splits_functional_and_non_functional_ids(self):
        self.assertEqual(parser.split_id("RF-ASI-001"), ("RF", "ASI", "001"))
        self.assertEqual(parser.split_id("RNF-SEG-001"), ("RNF", "SEG", "001"))

    def test_rejects_a_malformed_id(self):
        with self.assertRaises(ValueError):
            parser.split_id("RF-ASISTENCIA-1")


class ChooseCanonicalTest(unittest.TestCase):
    def test_a_lone_card_is_canonical(self):
        card, matched = parser.choose_canonical([{"name": "Cualquiera"}], "Otra cosa")

        self.assertEqual(card["name"], "Cualquiera")
        self.assertTrue(matched)

    def test_prefers_the_card_whose_name_matches_the_catalogue(self):
        cards = [
            {"name": "Cierre automático de jornada"},
            {"name": "Detección de inconsistencias entre fuentes"},
        ]

        card, matched = parser.choose_canonical(
            cards, "Deteccion de inconsistencias entre fuentes"
        )

        self.assertEqual(card["name"], "Detección de inconsistencias entre fuentes")
        self.assertTrue(matched)

    def test_falls_back_to_the_last_card_and_reports_no_match(self):
        cards = [
            {"name": "Cifrado de Datos en Tránsito y Reposo"},
            {"name": "Directivas de seguridad en cookies de sesión"},
        ]

        card, matched = parser.choose_canonical(
            cards, "Cookie de sesion con HttpOnly, Secure y SameSite"
        )

        self.assertEqual(card["name"], "Directivas de seguridad en cookies de sesión")
        self.assertFalse(matched)


class ParseCatalogueTest(unittest.TestCase):
    def test_reads_id_description_priority_and_domain(self):
        entries = parser.parse_catalogue(CATALOGUE)

        self.assertEqual(set(entries), {"RF-ASI-001", "RF-JOR-005", "RNF-SEG-001"})
        self.assertEqual(entries["RF-JOR-005"]["priority"], "Deberia")
        self.assertEqual(entries["RF-JOR-005"]["domain"], "attendance-governance")
        self.assertEqual(entries["RNF-SEG-001"]["domain"], "security-compliance")


class MappingTest(unittest.TestCase):
    def test_every_catalogue_prefix_has_a_scope(self):
        rf_prefixes = {p for kind, p in mapping.SCOPES if kind == "RF"}
        rnf_prefixes = {p for kind, p in mapping.SCOPES if kind == "RNF"}

        self.assertEqual(len(rf_prefixes), 23)
        self.assertEqual(len(rnf_prefixes), 14)

    def test_every_functional_prefix_belongs_to_exactly_one_epic(self):
        rf_prefixes = sorted(p for kind, p in mapping.SCOPES if kind == "RF")
        owned = [p for epic in mapping.EPICS for p in epic["prefixes"]]

        self.assertEqual(sorted(owned), rf_prefixes)
        self.assertEqual(len(owned), len(set(owned)), "a prefix is claimed twice")

    def test_res_prefix_means_different_things_per_kind(self):
        self.assertEqual(mapping.scope_for("RF", "RES"), "resultados")
        self.assertEqual(mapping.scope_for("RNF", "RES"), "respaldo")

    def test_non_functional_requirements_land_in_the_platform_epic(self):
        self.assertEqual(mapping.epic_key_for("RNF", "SEG"), "plataforma")
        self.assertEqual(mapping.epic_key_for("RF", "ASI"), "asistencia")

    def test_both_priority_vocabularies_map_to_labels(self):
        self.assertEqual(mapping.priority_label_for("Debe"), "priority:high")
        self.assertEqual(mapping.priority_label_for("Alta"), "priority:high")
        self.assertEqual(mapping.priority_label_for("Debería"), "priority:medium")
        self.assertEqual(mapping.priority_label_for("Deberia"), "priority:medium")
        self.assertEqual(mapping.priority_label_for("Podría"), "priority:low")

    def test_unknown_priority_is_loud(self):
        with self.assertRaises(KeyError):
            mapping.priority_label_for("Urgentisimo")

    def test_domain_drives_the_area_label(self):
        self.assertEqual(mapping.area_label_for("identity-access"), "area:security")
        self.assertEqual(mapping.area_label_for("frontend-platform"), "area:frontend")
        self.assertEqual(mapping.area_label_for("platform"), "area:devops")
        self.assertEqual(mapping.area_label_for("attendance-capture"), "area:backend")

    def test_a_security_prefix_overrides_the_domain(self):
        # RNF-SEG-004 is filed under document-generation but is still security.
        self.assertEqual(
            mapping.area_label_for("document-generation", "SEG"), "area:security"
        )
        self.assertEqual(
            mapping.area_label_for("attendance-capture", "PRI"), "area:security"
        )
        self.assertEqual(
            mapping.area_label_for("security-compliance", "LEG"), "area:security"
        )
        # A non-security prefix leaves the domain in charge.
        self.assertEqual(
            mapping.area_label_for("document-generation", "EMI"), "area:backend"
        )

    def test_labels_for_a_complete_functional_requirement(self):
        record = {
            "kind": "RF",
            "domain": "attendance-capture",
            "priority": "Debe",
            "acceptance_criteria": "El sistema registra el movimiento.",
        }

        self.assertEqual(
            mapping.labels_for(record),
            ["type:feature", "area:backend", "priority:high"],
        )

    def test_a_requirement_without_criteria_is_marked_blocked(self):
        record = {
            "kind": "RF",
            "domain": "school-cycle",
            "priority": "Debe",
            "acceptance_criteria": "",
        }

        self.assertIn("status:blocked", mapping.labels_for(record))

    def test_a_capability_spec_unblocks_a_requirement_with_no_criterion(self):
        record = {
            "kind": "RF",
            "domain": "identity-access",
            "priority": "Debe",
            "acceptance_criteria": "",
            "spec": {"statement": "El sistema DEBE...", "scenarios": []},
        }

        self.assertNotIn("status:blocked", mapping.labels_for(record))

    def test_titles_follow_the_conventional_commit_convention(self):
        self.assertEqual(
            mapping.title_for(
                {
                    "kind": "RF",
                    "prefix": "ASI",
                    "id": "RF-ASI-001",
                    "name": "Captura mediada por operador",
                }
            ),
            "feat(asistencia): RF-ASI-001 Captura mediada por operador",
        )
        self.assertEqual(
            mapping.title_for(
                {
                    "kind": "RNF",
                    "prefix": "SEG",
                    "id": "RNF-SEG-001",
                    "name": "Cookie de sesion segura",
                }
            ),
            "chore(seguridad): RNF-SEG-001 Cookie de sesion segura",
        )


CATALOGUE_TABLE = """\
| ID | Descripcion original | Prioridad | Dominio | Estado | Issue relacionado | Pruebas |
| --- | --- | --- | --- | --- | --- | --- |
| RF-ASI-001 | Captura mediada por operador | Debe | attendance-capture | Not implemented | TBD | TBD |
| RF-ASI-002 | Registro de movimiento | Debe | attendance-capture | Not implemented | TBD | TBD |
| RF-ASI-003 | Confirmacion visual | Debe | attendance-capture | Not implemented | #999 | TBD |
| RF-ASI-004 | Supresion de duplicados | Debe | attendance-capture | Not implemented | ver #7 y #8 | TBD |
"""

MATRIX_TABLE = """\
| Requirement | Issue | Design | Code | Test | Pull Request | Status | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- |
| RF-ASI-001 | TBD | docs/x.md | TBD | TBD | TBD | Planned | Nucleo |
| RF-BIT-005 | TBD | docs/y.md | TBD | TBD | TBD | Planned | Inmutabilidad |
"""


class BackfillTest(unittest.TestCase):
    def test_fills_the_issue_column_of_the_catalogue(self):
        created = {"RF-ASI-001": "42", "RF-ASI-002": "43"}

        patched, changed, skipped = backfill.patch_table(
            CATALOGUE_TABLE, created, id_column=0, issue_column=5
        )

        self.assertEqual(changed, 2)
        self.assertIn("| RF-ASI-001 | Captura mediada por operador | Debe | attendance-capture | Not implemented | #42 |", patched)
        self.assertIn("| #43 |", patched)
        self.assertEqual(skipped, ["RF-ASI-003", "RF-ASI-004"])

    def test_fills_the_issue_column_of_the_matrix(self):
        created = {"RF-ASI-001": "42"}

        patched, changed, _ = backfill.patch_table(
            MATRIX_TABLE, created, id_column=0, issue_column=1
        )

        self.assertEqual(changed, 1)
        self.assertIn("| RF-ASI-001 | #42 | docs/x.md |", patched)
        self.assertIn("| RF-BIT-005 | TBD | docs/y.md |", patched)

    def test_is_idempotent(self):
        created = {"RF-ASI-001": "42", "RF-ASI-002": "43"}

        once, first_changed, _ = backfill.patch_table(
            CATALOGUE_TABLE, created, id_column=0, issue_column=5
        )
        twice, second_changed, _ = backfill.patch_table(
            once, created, id_column=0, issue_column=5
        )

        self.assertEqual(first_changed, 2)
        self.assertEqual(second_changed, 0)
        self.assertEqual(once, twice)

    def test_overwrites_a_number_this_script_wrote_before(self):
        created = {"RF-ASI-003": "50"}

        patched, changed, _ = backfill.patch_table(
            CATALOGUE_TABLE, created, id_column=0, issue_column=5
        )

        self.assertEqual(changed, 1)
        self.assertIn("| #50 |", patched)

    def test_never_touches_a_hand_written_cell(self):
        created = {"RF-ASI-004": "51"}

        patched, changed, _ = backfill.patch_table(
            CATALOGUE_TABLE, created, id_column=0, issue_column=5
        )

        self.assertEqual(changed, 0)
        self.assertIn("| ver #7 y #8 |", patched)

    def test_leaves_prose_and_headers_alone(self):
        created = {"RF-ASI-001": "42"}
        text = "# Titulo\n\nTexto con RF-ASI-001 mencionado.\n\n" + MATRIX_TABLE

        patched, changed, _ = backfill.patch_table(
            text, created, id_column=0, issue_column=1
        )

        self.assertEqual(changed, 1)
        self.assertIn("Texto con RF-ASI-001 mencionado.", patched)
        self.assertTrue(patched.startswith("# Titulo"))

    def test_preserves_a_trailing_newline(self):
        patched, _, _ = backfill.patch_table(
            MATRIX_TABLE, {"RF-ASI-001": "42"}, id_column=0, issue_column=1
        )

        self.assertTrue(patched.endswith("\n"))

    def test_epic_rows_are_not_loaded_as_requirements(self):
        import tempfile

        with tempfile.NamedTemporaryFile("w", suffix=".tsv", delete=False, encoding="utf-8") as handle:
            handle.write("epic:asistencia\t8\thttps://example.test/issues/8\n")
            handle.write("RF-ASI-001\t42\thttps://example.test/issues/42\n")
            path = handle.name

        try:
            created = backfill.load_created(path)
        finally:
            os.unlink(path)

        self.assertEqual(created, {"RF-ASI-001": "42"})


CAPABILITY_SPEC = """\
# identidad-cuentas

## ADDED Requirements

### Requirement: Creación exclusivamente administrativa

El sistema DEBE permitir la creación de cuentas únicamente a usuarios con permiso de
administración de cuentas. NO DEBE existir autorregistro.

#### Scenario: No hay autorregistro

- **GIVEN** una persona sin cuenta en el sistema
- **WHEN** intenta acceder a un formulario de creación de cuenta propia
- **THEN** el sistema no ofrece ninguna vía de autorregistro

### Requirement: Política de contraseñas

El sistema DEBE exigir una longitud mínima configurable.

#### Scenario: Contraseña común rechazada

- **GIVEN** un titular definiendo su contraseña
- **WHEN** introduce una contraseña presente en la lista de contraseñas
  comunes
- **THEN** el sistema la rechaza

#### Scenario: Contraseña aceptada

- **GIVEN** un titular definiendo su contraseña
- **THEN** el sistema la acepta
"""


class ScenariosTest(unittest.TestCase):
    def test_splits_requirements_and_their_scenarios(self):
        requirements = scenarios.parse_capability(CAPABILITY_SPEC)

        self.assertEqual(len(requirements), 2)
        self.assertEqual(
            requirements[0]["title"], "Creación exclusivamente administrativa"
        )
        self.assertEqual(len(requirements[0]["scenarios"]), 1)
        self.assertEqual(len(requirements[1]["scenarios"]), 2)

    def test_collapses_the_wrapped_statement(self):
        requirements = scenarios.parse_capability(CAPABILITY_SPEC)

        self.assertEqual(
            requirements[0]["statement"],
            "El sistema DEBE permitir la creación de cuentas únicamente a usuarios "
            "con permiso de administración de cuentas. NO DEBE existir autorregistro.",
        )

    def test_keeps_the_given_when_then_steps_in_order(self):
        requirements = scenarios.parse_capability(CAPABILITY_SPEC)

        self.assertEqual(
            requirements[0]["scenarios"][0]["steps"],
            [
                "**GIVEN** una persona sin cuenta en el sistema",
                "**WHEN** intenta acceder a un formulario de creación de cuenta propia",
                "**THEN** el sistema no ofrece ninguna vía de autorregistro",
            ],
        )

    def test_unwraps_a_step_that_spans_two_lines(self):
        requirements = scenarios.parse_capability(CAPABILITY_SPEC)
        steps = requirements[1]["scenarios"][0]["steps"]

        self.assertEqual(
            steps[1],
            "**WHEN** introduce una contraseña presente en la lista de "
            "contraseñas comunes",
        )

    def test_statement_excludes_the_scenarios(self):
        requirements = scenarios.parse_capability(CAPABILITY_SPEC)

        self.assertNotIn("GIVEN", requirements[0]["statement"])
        self.assertNotIn("Scenario", requirements[0]["statement"])

    def test_every_capability_maps_to_a_known_prefix(self):
        prefixes = set(scenarios.CAPABILITY_PREFIXES.values())
        rf_prefixes = {p for kind, p in mapping.SCOPES if kind == "RF"}

        self.assertTrue(prefixes.issubset(rf_prefixes))
        self.assertEqual(len(scenarios.CAPABILITY_PREFIXES), 13)

    def test_load_joins_titles_onto_catalogue_ids(self):
        import tempfile

        catalogue = {
            "RF-CTA-001": {
                "description": "Creacion exclusivamente administrativa",
                "priority": "Debe",
                "domain": "identity-access",
            },
            "RF-CTA-004": {
                "description": "Politica de contrasenas",
                "priority": "Debe",
                "domain": "identity-access",
            },
        }

        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "identidad-cuentas.md")
            with open(path, "w", encoding="utf-8") as handle:
                handle.write(CAPABILITY_SPEC)

            matched, unmatched = scenarios.load(
                directory, catalogue, parser.normalise
            )

        self.assertEqual(set(matched), {"RF-CTA-001", "RF-CTA-004"})
        self.assertEqual(unmatched, [])
        self.assertEqual(matched["RF-CTA-001"]["capability"], "identidad-cuentas")
        self.assertEqual(len(matched["RF-CTA-004"]["scenarios"]), 2)

    def test_load_reports_a_title_with_no_catalogue_match(self):
        import tempfile

        catalogue = {
            "RF-CTA-001": {
                "description": "Otra cosa distinta",
                "priority": "Debe",
                "domain": "identity-access",
            }
        }

        with tempfile.TemporaryDirectory() as directory:
            with open(
                os.path.join(directory, "identidad-cuentas.md"), "w", encoding="utf-8"
            ) as handle:
                handle.write(CAPABILITY_SPEC)

            matched, unmatched = scenarios.load(
                directory, catalogue, parser.normalise
            )

        self.assertEqual(matched, {})
        self.assertEqual(len(unmatched), 2)

    def test_a_missing_specs_directory_is_not_an_error(self):
        matched, unmatched = scenarios.load("/nonexistent", {}, parser.normalise)

        self.assertEqual(matched, {})
        self.assertEqual(unmatched, [])


class ImplementationTest(unittest.TestCase):
    def test_every_catalogue_domain_is_mapped(self):
        catalogue_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "..",
            "..",
            "docs",
            "requirements",
            "requirements-catalogue.md",
        )
        with open(catalogue_path, encoding="utf-8") as handle:
            catalogue = parser.parse_catalogue(handle.read())

        domains = {entry["domain"] for entry in catalogue.values()}
        missing = domains - set(implementation.DOMAINS)

        self.assertEqual(missing, set(), f"unmapped domains: {sorted(missing)}")

    def test_an_existing_app_is_reported_as_extendable(self):
        note = implementation.app_status_note("identity-access")

        self.assertIn("backend/apps/identity", note)
        self.assertIn("ya existe", note)

    def test_a_missing_app_is_flagged_for_creation(self):
        note = implementation.app_status_note("attendance-capture")

        self.assertIn("todavia no existe", note)
        self.assertIn("backend/apps/attendance", note)

    def test_a_transversal_domain_gets_no_app(self):
        self.assertEqual(implementation.backend_paths("platform"), [])
        self.assertIn("transversal", implementation.app_status_note("platform"))

    def test_backend_paths_cover_the_repo_layers(self):
        paths = [path for path, _ in implementation.backend_paths("student-records")]

        self.assertIn("backend/apps/students/models.py", paths)
        self.assertIn("backend/apps/students/services.py", paths)
        self.assertIn("backend/apps/students/api/views.py", paths)

    def test_security_domains_require_a_permissions_test(self):
        paths = [
            path for path, _ in implementation.test_paths("identity-access", "area:security")
        ]

        self.assertIn("backend/tests/permissions/test_identity_permissions.py", paths)

    def test_a_frontend_requirement_gets_frontend_paths(self):
        paths = [path for path, _ in implementation.frontend_paths("platform", "area:frontend")]

        self.assertTrue(any("frontend/src" in path for path in paths))

    def test_a_backend_requirement_gets_no_frontend_paths(self):
        self.assertEqual(
            implementation.frontend_paths("attendance-capture", "area:backend"), []
        )

    def test_domains_without_dependencies_skip_the_integration_test(self):
        paths = [path for path, _ in implementation.test_paths("people-registry", "area:backend")]

        self.assertFalse(any("integration" in path for path in paths))


if __name__ == "__main__":
    unittest.main()
