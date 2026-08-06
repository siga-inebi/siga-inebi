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

Todos requerimientos estan en estado `Planned`. Referencias de issue, diseno detallado, codigo, pruebas y PR quedan pendientes.

## Seed Matrix

| Requirement | Issue | Design | Code | Test | Pull Request | Status | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- |
| RF-AUT-001 | TBD | docs/architecture/authorization-model.md | backend/config/api/views.py; frontend/src/pages/LoginPage.jsx; frontend/src/features/auth/AuthContext.jsx | backend/tests/api/test_auth_api.py; frontend/src/test/app.test.jsx | PR #3 | Under Review | Inicio de sesion institucional con sesion y CSRF |
| RF-AUT-002 | TBD | docs/architecture/authorization-model.md | backend/apps/identity/services.py; backend/apps/identity/serializers.py; backend/config/settings/base.py | backend/tests/api/test_auth_api.py | PR #25 | In Progress | Bloqueo configurable al alcanzar 5 intentos fallidos durante 10 minutos |
| RF-AUT-004 | TBD | docs/architecture/authorization-model.md | backend/config/api/views.py; frontend/src/layouts/AppLayout.jsx | backend/tests/api/test_auth_api.py | PR #3 | Under Review | Cierre de sesion y anulacion de contexto autenticado |
| RF-PER-004 | TBD | docs/architecture/authorization-model.md | backend/apps/identity/models.py; backend/config/settings/base.py; backend/config/api/views.py | backend/tests/api/test_auth_api.py; frontend/src/test/app.test.jsx | PR #3 | Under Review | Denegacion por defecto con sesion anonima |
| RF-ALC-001 | TBD | docs/architecture/authorization-model.md | TBD | TBD | TBD | Planned | Permiso siempre con alcance |
| RF-CTA-001 | TBD | docs/architecture/authorization-model.md; docs/architecture/api-conventions.md | backend/apps/identity/services.py; backend/apps/identity/api/views.py; backend/apps/identity/management/commands/seed_demo_data.py | backend/tests/permissions/test_identity_permissions.py; backend/tests/api/test_identity_account_provisioning_api.py; backend/tests/integration/test_seed.py | PR #3; PR #41; TBD | In Progress | Provision administrativa expuesta por API; activacion final fuera de este corte |
| RF-CTA-002 | TBD | docs/architecture/initial-data-model.md; docs/architecture/authorization-model.md | backend/apps/identity/services.py; backend/apps/identity/api/serializers.py; backend/apps/identity/management/commands/seed_demo_data.py | backend/tests/permissions/test_identity_permissions.py; backend/tests/api/test_identity_account_provisioning_api.py; backend/tests/integration/test_seed.py | PR #3; PR #41; TBD | In Progress | La provision exige una persona institucional existente y unica por cuenta |
| RF-CTA-003 | TBD | docs/architecture/authorization-model.md; docs/architecture/api-conventions.md | backend/apps/identity/models.py; backend/apps/identity/services.py; backend/apps/identity/api/views.py | backend/tests/api/test_identity_account_provisioning_api.py | PR #3; TBD | In Progress | Emision y reemision segura implementadas; consumo del codigo y activacion final quedan fuera de este corte |
| RF-CTA-006 | TBD | docs/architecture/authorization-model.md; docs/architecture/audit-strategy.md | backend/apps/identity/services.py | backend/tests/permissions/test_identity_permissions.py | TBD | In Progress | Servicio interno de desactivacion administrativa sin borrado fisico; API y verificacion de dependencias quedan fuera de este corte |
| RF-CIC-001 | TBD | docs/architecture/domain-map.md | TBD | TBD | TBD | Planned | Registro de ciclo |
| RF-EST-007 | TBD | docs/architecture/initial-data-model.md | TBD | TBD | TBD | Planned | Secciones |
| RF-MAT-002 | TBD | docs/architecture/initial-data-model.md | TBD | TBD | TBD | Planned | Matricula |
| RF-CRE-001 | TBD | docs/architecture/file-storage-strategy.md | TBD | TBD | TBD | Planned | QR opaco |
| RF-ASI-010 | TBD | docs/architecture/audit-strategy.md | TBD | TBD | TBD | Planned | Idempotencia |
| RF-JOR-002 | TBD | docs/architecture/domain-map.md | TBD | TBD | TBD | Planned | Estado diario derivado |
| RF-JUS-004 | TBD | docs/architecture/data-classification.md | TBD | TBD | TBD | Planned | Resolucion auditable |
| RF-DOC-006 | TBD | docs/architecture/audit-strategy.md | TBD | TBD | TBD | Planned | Auditoria de lectura |
| RF-BIT-005 | TBD | docs/architecture/audit-strategy.md | TBD | TBD | TBD | Planned | Inmutabilidad |
| RF-CAL-002 | TBD | docs/architecture/initial-data-model.md | TBD | TBD | TBD | Planned | Validacion de nota |
| RF-RES-008 | TBD | docs/architecture/api-conventions.md | TBD | TBD | TBD | Planned | Boleta |
| RNF-AUD-001 | TBD | docs/architecture/audit-strategy.md | TBD | TBD | TBD | Planned | Eventos inmutables |
| RNF-SEG-003 | TBD | docs/architecture/authorization-model.md; docs/architecture/audit-strategy.md | backend/apps/identity/services.py | backend/tests/permissions/test_identity_permissions.py; backend/tests/api/test_identity_account_provisioning_api.py | TBD | In Progress | Auditoria de rechazos de desactivacion, provision, login y reemision de desafios; otros intentos quedan fuera de este corte |
| RNF-PRI-001 | TBD | docs/architecture/system-context.md | TBD | TBD | TBD | Planned | QR sin PII |
| RNF-SEG-005 | TBD | docs/architecture/file-storage-strategy.md | TBD | TBD | TBD | Planned | Descarga segura |
| RNF-REN-003 | TBD | docs/architecture/system-context.md | TBD | TBD | TBD | Planned | Lotes en worker |
| RNF-RES-002 | TBD | docs/decisions/pending-decisions.md | TBD | TBD | TBD | Planned | RPO/RTO pendientes |

## Mantenimiento

- Actualizar fila por cada requerimiento implementado o afectado.
- Si requerimiento cambia, agregar nota de impacto.
- Si PR cubre varios requerimientos, repetir PR en cada fila correspondiente.
