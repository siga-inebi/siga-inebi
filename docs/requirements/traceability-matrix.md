# Traceability Matrix

## Objetivo

Preparar relacion verificable entre `Requerimiento -> Issue -> Diseno -> Codigo -> Prueba -> Pull Request`.

## Convenciones

- Un requerimiento puede mapear a varios issues.
- Un issue puede cubrir varios requerimientos solo si alcance queda explicitado.
- Ningun requerimiento se marca `Implemented` sin referencia de prueba verificable.
- Pull Request debe citar IDs RF o RNF afectados.

## Columnas canonicas

| Requirement | Issue | Design | Code | Test | Pull Request | Status | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- |

## Estado inicial

La mayoria de requerimientos sigue en `Planned`. Las filas marcadas `Under Review`
o `Implemented` citan su codigo y pruebas; las referencias de issue y PR se
completan al abrir el pull request correspondiente.

## Seed Matrix

| Requirement | Issue | Design | Code | Test | Pull Request | Status | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- |
| RF-AUT-001 | TBD | docs/architecture/authorization-model.md | backend/config/api/views.py; frontend/src/pages/LoginPage.jsx; frontend/src/features/auth/AuthContext.jsx | backend/tests/api/test_auth_api.py; frontend/src/test/app.test.jsx | PR #3 | Under Review | Inicio de sesion institucional con sesion y CSRF |
| RF-AUT-004 | TBD | docs/architecture/authorization-model.md | backend/config/api/views.py; frontend/src/layouts/AppLayout.jsx | backend/tests/api/test_auth_api.py | PR #3 | Under Review | Cierre de sesion y anulacion de contexto autenticado |
| RF-PER-004 | TBD | docs/architecture/authorization-model.md | backend/apps/identity/models.py; backend/config/settings/base.py; backend/config/api/views.py | backend/tests/api/test_auth_api.py; frontend/src/test/app.test.jsx | PR #3 | Under Review | Denegacion por defecto con sesion anonima |
| RF-ALC-001 | TBD | docs/architecture/authorization-model.md | TBD | TBD | TBD | Planned | Permiso siempre con alcance |
| RF-CTA-001 | TBD | docs/architecture/authorization-model.md | backend/apps/identity/management/commands/seed_demo_data.py | backend/tests/integration/test_seed.py | PR #3 | Under Review | Provision administrativa inicial por seed en desarrollo |
| RF-CTA-002 | TBD | docs/architecture/initial-data-model.md | backend/apps/identity/management/commands/seed_demo_data.py; backend/apps/identity/serializers.py | backend/tests/integration/test_seed.py; backend/tests/api/test_auth_api.py | PR #3 | Under Review | Cuenta demo vinculada a persona institucional |
| RF-CTA-003 | TBD | docs/architecture/authorization-model.md | backend/apps/identity/management/commands/seed_demo_data.py; backend/docker-entrypoint.sh | backend/tests/integration/test_seed.py | PR #3 | Under Review | Activacion inicial guiada por seed y variables de entorno en desarrollo |
| RF-CTA-006 | TBD | docs/architecture/authorization-model.md; docs/architecture/audit-strategy.md | backend/apps/identity/services.py | backend/tests/permissions/test_identity_permissions.py | TBD | In Progress | Servicio interno de desactivacion administrativa sin borrado fisico; API y verificacion de dependencias quedan fuera de este corte |
| RF-CIC-001 | TBD | docs/architecture/domain-map.md | TBD | TBD | TBD | Planned | Registro de ciclo |
| RF-CIC-003 | TBD | docs/architecture/academic-catalogue.md | backend/apps/academics/models.py; backend/apps/academics/services.py; backend/apps/academics/api/ | backend/tests/unit/test_cycle_services.py; backend/tests/api/test_academics_catalog_api.py | TBD | Implemented | Apertura con unicidad de ciclo activo por institucion |
| RF-CIC-004 | TBD | docs/architecture/academic-catalogue.md | backend/apps/academics/models.py; backend/apps/academics/services.py; backend/apps/academics/api/ | backend/tests/unit/test_cycle_services.py; backend/tests/api/test_academics_catalog_api.py | TBD | Implemented | Cierre congela la estructura del ciclo |
| RF-EST-001 | TBD | docs/architecture/academic-catalogue.md | backend/apps/academics/models.py; backend/apps/academics/services.py; backend/apps/academics/api/ | backend/tests/unit/test_catalog_services.py; backend/tests/unit/test_catalog_update_services.py; backend/tests/api/test_academics_catalog_api.py | TBD | Implemented | Grados ligados a nivel, con orden pedagogico |
| RF-EST-002 | TBD | docs/architecture/academic-catalogue.md | backend/apps/academics/models.py; backend/apps/academics/services.py; backend/apps/academics/api/ | backend/tests/unit/test_campus_services.py; backend/tests/api/test_academics_catalog_api.py | TBD | Implemented | Jornadas por sede, con codigo unico por sede |
| RF-EST-007 | TBD | docs/architecture/academic-catalogue.md | backend/apps/academics/models.py; backend/apps/academics/services.py; backend/apps/academics/api/ | backend/tests/unit/test_offering_services.py; backend/tests/api/test_academics_catalog_api.py | TBD | Implemented | Secciones bajo la oferta de grado |
| RF-EST-008 | TBD | docs/architecture/academic-catalogue.md | backend/apps/academics/models.py; backend/apps/academics/services.py; backend/apps/academics/api/ | backend/tests/unit/test_offering_services.py; backend/tests/api/test_academics_catalog_api.py; backend/tests/integration/test_concurrency.py | TBD | Implemented | Cupo declarado y ocupacion consultable por seccion |
| RF-EST-011 | TBD | docs/architecture/academic-catalogue.md | backend/apps/academics/models.py; backend/apps/academics/services.py; backend/apps/academics/api/ | backend/tests/unit/test_cycle_services.py; backend/tests/unit/test_offering_services.py | TBD | Implemented | Estructura inmutable con ciclo cerrado |
| RF-EST-012 | TBD | docs/architecture/academic-catalogue.md | backend/apps/academics/models.py; backend/apps/academics/services.py; backend/apps/academics/api/ | backend/tests/unit/test_campus_services.py; backend/tests/unit/test_catalog_services.py; backend/tests/unit/test_offering_services.py | TBD | Implemented | Desactivacion en lugar de eliminacion |
| RF-EST-013 | TBD | docs/architecture/academic-catalogue.md | backend/apps/academics/models.py; backend/apps/academics/services.py; backend/apps/academics/api/ | backend/tests/unit/test_offering_services.py | TBD | Implemented | Oferta y secciones versionadas por ciclo |
| RF-MAT-001 | TBD | docs/architecture/academic-catalogue.md | backend/apps/enrolments/models.py; backend/apps/enrolments/services.py | backend/tests/unit/test_enrolment_services.py; backend/tests/api/test_enrolments_api.py | TBD | Implemented | Inscripcion como registro con vigencia (`effective_on`/`ends_on`) |
| RF-MAT-002 | TBD | docs/architecture/academic-catalogue.md | backend/apps/enrolments/models.py; backend/apps/enrolments/services.py; backend/apps/enrolments/api/ | backend/tests/unit/test_enrolment_services.py; backend/tests/api/test_enrolments_api.py | TBD | Implemented | Matricula de un estudiante en ciclo/grado/seccion |
| RF-MAT-003 | TBD | docs/architecture/academic-catalogue.md | backend/apps/enrolments/services.py; backend/apps/enrolments/api/ | backend/tests/unit/test_enrolment_services.py; backend/tests/api/test_enrolments_api.py | TBD | Implemented | Reinscripcion; rechaza si ya hay matricula activa en el ciclo destino |
| RF-MAT-004 | TBD | docs/architecture/academic-catalogue.md | backend/apps/enrolments/services.py | backend/tests/unit/test_enrolment_services.py | TBD | Implemented | Cupo de la seccion bloquea nuevas matriculas; fila bloqueada antes de contar |
| RF-MOV-001 | TBD | docs/architecture/academic-catalogue.md | backend/apps/enrolments/services.py; backend/apps/enrolments/api/ | backend/tests/unit/test_enrolment_services.py; backend/tests/api/test_enrolments_api.py | TBD | Implemented | Cambio de seccion distinto de retiro; misma matricula, otra seccion |
| RF-MOV-002 | TBD | docs/architecture/academic-catalogue.md | backend/apps/enrolments/services.py | backend/tests/unit/test_enrolment_services.py | TBD | Implemented | Cambio de seccion cierra la matricula previa como completed, sin borrarla |
| RF-MOV-004 | TBD | docs/architecture/academic-catalogue.md | backend/apps/enrolments/services.py; backend/apps/enrolments/api/ | backend/tests/unit/test_enrolment_services.py; backend/tests/api/test_enrolments_api.py | TBD | Implemented | Retiro solo de matriculas activas; ciclo cerrado lo bloquea; preserva historial |
| RF-CRE-001 | TBD | docs/architecture/file-storage-strategy.md | TBD | TBD | TBD | Planned | QR opaco |
| RF-ASI-010 | TBD | docs/architecture/audit-strategy.md | TBD | TBD | TBD | Planned | Idempotencia |
| RF-JOR-002 | TBD | docs/architecture/domain-map.md | TBD | TBD | TBD | Planned | Estado diario derivado |
| RF-JUS-004 | TBD | docs/architecture/data-classification.md | TBD | TBD | TBD | Planned | Resolucion auditable |
| RF-DOC-006 | TBD | docs/architecture/audit-strategy.md | TBD | TBD | TBD | Planned | Auditoria de lectura |
| RF-BIT-005 | TBD | docs/architecture/audit-strategy.md | TBD | TBD | TBD | Planned | Inmutabilidad |
| RF-CAL-002 | TBD | docs/architecture/initial-data-model.md | TBD | TBD | TBD | Planned | Validacion de nota |
| RF-RES-008 | TBD | docs/architecture/api-conventions.md | TBD | TBD | TBD | Planned | Boleta |
| RNF-AUD-001 | TBD | docs/architecture/audit-strategy.md | TBD | TBD | TBD | Planned | Eventos inmutables |
| RNF-SEG-003 | TBD | docs/architecture/authorization-model.md; docs/architecture/audit-strategy.md | backend/apps/identity/services.py | backend/tests/permissions/test_identity_permissions.py | TBD | In Progress | Auditoria del intento denegado de desactivacion de cuenta; otros intentos rechazados quedan fuera de este corte |
| RNF-PRI-001 | TBD | docs/architecture/system-context.md | TBD | TBD | TBD | Planned | QR sin PII |
| RNF-SEG-005 | TBD | docs/architecture/file-storage-strategy.md | TBD | TBD | TBD | Planned | Descarga segura |
| RNF-REN-003 | TBD | docs/architecture/system-context.md | TBD | TBD | TBD | Planned | Lotes en worker |
| RNF-RES-002 | TBD | docs/decisions/pending-decisions.md | TBD | TBD | TBD | Planned | RPO/RTO pendientes |

## Mantenimiento

- Actualizar fila por cada requerimiento implementado o afectado.
- Si requerimiento cambia, agregar nota de impacto.
- Si PR cubre varios requerimientos, repetir PR en cada fila correspondiente.
