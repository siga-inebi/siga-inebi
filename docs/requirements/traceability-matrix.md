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
| RF-AUT-001 | TBD | docs/architecture/authorization-model.md | TBD | TBD | TBD | Planned | Inicio de sesion |
| RF-PER-004 | TBD | docs/architecture/authorization-model.md | TBD | TBD | TBD | Planned | Denegacion por defecto |
| RF-ALC-001 | TBD | docs/architecture/authorization-model.md | TBD | TBD | TBD | Planned | Permiso siempre con alcance |
| RF-CTA-002 | TBD | docs/architecture/initial-data-model.md | TBD | TBD | TBD | Planned | Cuenta vinculada a persona |
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
| RNF-PRI-001 | TBD | docs/architecture/system-context.md | TBD | TBD | TBD | Planned | QR sin PII |
| RNF-SEG-005 | TBD | docs/architecture/file-storage-strategy.md | TBD | TBD | TBD | Planned | Descarga segura |
| RNF-REN-003 | TBD | docs/architecture/system-context.md | TBD | TBD | TBD | Planned | Lotes en worker |
| RNF-RES-002 | TBD | docs/decisions/pending-decisions.md | TBD | TBD | TBD | Planned | RPO/RTO pendientes |

## Mantenimiento

- Actualizar fila por cada requerimiento implementado o afectado.
- Si requerimiento cambia, agregar nota de impacto.
- Si PR cubre varios requerimientos, repetir PR en cada fila correspondiente.
