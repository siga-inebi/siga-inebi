# Alcance y decisiones — Fase 7

## Línea base

| Campo | Valor |
| --- | --- |
| Fecha de consolidación | 8 de octubre de 2026 |
| Coordinador QA | Pablo |
| Fuente de requisitos | `docs/requirements/requirements.json` |
| Universo | 230 requisitos: 195 RF y 35 RNF |
| Fuente de estado de implementación | `docs/requirements/requirements-catalogue.md` |
| Matriz canónica | `docs/requirements/traceability-matrix.md` |
| Línea base local | 0c8f0d396231f46809b95cc088d5f2c557cb919f (2026-10-08T10:55:43-06:00) |
| Candidato de pruebas/entrega | Pendiente de fijar mediante SHA en manifiesto-version.md |
| Resultado de validación | Pendiente de ejecución; ningún requisito se considera aprobado aún. |

`catalogo-casos.csv` y `matriz-final.csv` se generan desde las fuentes anteriores para que los 230 IDs tengan una fila inicial. La clasificación es técnica y provisional: la decisión de alcance de entrega corresponde a la contraparte institucional.

## Criterio de clasificación inicial

| Clasificación | Regla usada | Efecto |
| --- | --- | --- |
| Incluido para validación | Catálogo con estado `Implemented`. | Requiere caso, ejecución y evidencia en candidato final. |
| Incluido condicionado | Catálogo con `In Progress` o `Under Review`. | No puede aceptarse sin cerrar brecha y repetir prueba. |
| Fuera del candidato actual | Catálogo con `Not implemented`. | Requiere exclusión institucional explícita o implementación antes de entrega. |
| Diferido | Catálogo con `Deferred`, o RNF-REN-003/004 por ADR-0009. | No se cuenta como aprobado; conservar decisión. |
| Pendiente de clasificación | Estado faltante o inconsistente. | Pablo y dueño de dominio deben resolverlo antes de D2. |

## Decisiones y bloqueos abiertos

| ID | Situación | Impacto en Fase 7 | Responsable de seguimiento | Estado |
| --- | --- | --- | --- | --- |
| DEC-QA-001 | Fijar SHA, rama/tag y ambiente del candidato. Existe línea base local, pero no candidato formal de entrega. | Sin versión formal no hay acta válida. | Daniel fija; Pablo verifica. | Pendiente |
| DEC-QA-002 | Confirmar alcance institucional de requisitos `Not implemented`, `In Progress` y `Under Review`. | Define exclusiones y criterios que bloquean aceptación. | Pablo + contraparte institucional. | Pendiente |
| PD-001 | Matrícula objetivo real no confirmada. | Rendimiento/capacidad solo puede usar referencia de ~500 estudiantes. | Pablo registra decisión; Daniel mide. | Open |
| PD-002 | RPO/RTO institucionales no confirmados; existen referencias de 24 h/4 h. | Recuperación no puede declararse aceptada contra una meta institucional sin confirmación. | Pablo solicita decisión. | Declarado, pendiente confirmación |
| PD-003 | Retención documental y de salud no definida. | Privacidad, almacenamiento y manuales pueden quedar sin criterio verificable. | Pablo + Roí/Diana. | Open |
| PD-004 | Acceso de encargados con múltiples estudiantes. | Autorización y UAT de encargados. | Pablo + Santiago/Diana. | Open |
| PD-005 | Política de observaciones disciplinarias. | Privacidad y permisos de expediente. | Pablo + Diana. | Open |
| PD-006 | Datos visibles en credencial. | Privacidad y flujo de credencial. | Pablo + Emilio. | Open |
| PD-007 | Reapertura de ciclo sobre documentos emitidos. | Integridad académica/documental. | Pablo + Josué/Roí. | Open |
| PD-008 | Foliado de reemisión por corrección. | Documentos oficiales. | Pablo + Roí. | Open |
| PD-010 | Operadores y tasa pico reales. | RNF-REN-002 no puede certificarse contra carga real. | Pablo + Emilio/Daniel. | Open |
| PD-011 | Guardia CI puede rechazar rutas legítimas con `backup`/`dump`. | Evidencia/documentación de recuperación puede bloquear CI. | Daniel verifica; Pablo registra decisión. | Open |
| DEC-QA-003 | RNF-REN-003/004 requieren worker, pero ADR-0009 difiere dicha arquitectura. | No se simula worker ni se declara conformidad. | Pablo + Daniel + autoridad de alcance. | Pendiente decisión de alcance |

## Controles de Pablo antes de cierre

1. Comparar las 230 filas generadas con `requirements.json`; prohibir IDs omitidos, nuevos sin registro o duplicados ambiguos.
2. Vincular cada requisito incluido con criterio, caso, responsable, ejecución, evidencia y resultado sobre SHA final.
3. Separar estado de implementación (`Implemented`, etc.) de resultado de validación (`Aprobado`, `Fallido`, `Bloqueado`, `No ejecutado` o `No aplica aprobado`).
4. Obtener decisión documentada para cada exclusión y cada pendiente material.
5. Reconciliar discrepancias de la matriz canónica sin reescribir historial.

Mientras DEC-QA-001 y DEC-QA-002 estén pendientes, el expediente solo es una línea base de calidad; no autoriza implementación.
