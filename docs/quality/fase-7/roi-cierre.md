# Cierre de entrega de Roí — Documentos, API y auditoría

**Estado:** evidencia técnica preparada; cierre humano y aceptación institucional pendientes.
**Responsable:** Roí.
**Revisores requeridos:** Estuardo (documentos/API) y Daniel (almacenamiento/recuperación).
**Base evaluada:** `develop` en `5ed5fd2`.
**Fecha de esta verificación:** 12 de octubre de 2026, `America/Guatemala`.

Este documento consolida la entrega individual de Roí descrita en
[`docs/planning/tests_plan.md`](../../planning/tests_plan.md). No convierte una
prueba automatizada en UAT, no inventa una revisión ajena y no declara aceptación
institucional sin constancia verificable.

## 1. Entregables realizados

| Obligación | Evidencia | Estado técnico |
| --- | --- | --- |
| Contratos API de documentos | `backend/tests/api/test_documents_api.py`; PR #569 | Completo en automatización |
| Autenticación y denegación por defecto | Casos parametrizados sobre endpoints documentales | Completo en automatización |
| Tokens de descarga | Ausencia, token inválido/alterado, expirado, portador ajeno y uso único | Completo en automatización |
| Validación de archivos | MIME, tamaño, carga directa y carga escaneada | Completo en automatización |
| Integridad documental | Checksum correcto, archivo faltante y archivo alterado | Completo en automatización |
| Historial documental | Reemplazo por nueva versión y conservación de registros previos | Completo en automatización |
| Auditoría transversal | `backend/tests/api/test_audit_api.py`; PR #570 | Completo en automatización |
| Manual de API e integraciones | [`docs/manuals/07-api-integrations-documentation.md`](../../manuals/07-api-integrations-documentation.md); PR #571 | Entregado |
| Recuperación documental | [`informe-recuperacion.md`](informe-recuperacion.md); PR #572 | Entregado con limitaciones declaradas |
| Pruebas de almacenamiento separado | `backend/tests/integration/test_backup_and_recovery.py` | Completo en automatización |

## 2. Ejecución reproducible

Comando ejecutado desde `backend`:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/api/test_documents_api.py tests/api/test_audit_api.py tests/integration/test_backup_and_recovery.py --no-cov -q
```

Resultado de la corrida sobre el candidato técnico:

```text
116 passed, 23 skipped, 5 warnings
```

Los 23 casos omitidos pertenecen a condiciones específicas de infraestructura o
simulacro de recuperación. No se cuentan como aprobados. Las advertencias son
`RemovedInDjango60Warning` y una advertencia de ordenamiento de paginación; no
alteran el resultado de esta corrida, pero deben conservarse para el seguimiento
general de calidad.

Controles de estilo sobre la prueba de recuperación:

```powershell
.\.venv\Scripts\ruff.exe check tests/integration/test_backup_and_recovery.py
.\.venv\Scripts\ruff.exe format --check tests/integration/test_backup_and_recovery.py
```

Resultado: `All checks passed` y `1 file already formatted`.

## 3. Relación con D1–D5

### D1 — Preparación y línea base

- Los criterios y casos documentales/API están cubiertos por las pruebas de los
  PR #569 y #570.
- Los datos usados por las pruebas son factories y archivos sintéticos.
- No se incorporan personas, documentos, respaldos ni secretos reales.
- La reconciliación final de cada criterio contra el candidato institucional debe
  ser confirmada por Pablo en la matriz consolidada.

### D2 — Funcional e integración

- Se verificaron contratos, autenticación, permisos, alcance, tokens, MIME,
  límites, integridad, versionado e impactos de auditoría.
- La integración documental con el flujo completo de usuario requiere una sesión
  QA/UAT registrada con Diana o Estuardo; las pruebas API no sustituyen esa sesión.

### D3 — Calidad transversal y recuperación

- Se verificaron faltantes, corrupción, checksums y separación entre base de datos
  y almacenamiento documental.
- El simulacro Cloud SQL `RUN-CQ-04` está documentado, pero no cubre restauración
  del bucket ni reapertura completa del tráfico; por eso no se presenta como RTO
  institucional completo.
- La confirmación de Daniel sobre la integración de almacenamiento/recuperación
  queda pendiente de registrar.

### D4 — Regresión y aceptación inicial

- La corrida focalizada de 116 casos sirve como regresión automatizada del área.
- Falta registrar una revisión independiente de Estuardo y repetir cualquier caso
  que resulte afectado por cambios posteriores al candidato evaluado.
- No se declara UAT aprobado por una corrida automatizada.

### D5 — Cierre y entrega

- El manual API y el aporte al manual/informe de recuperación están entregados.
- El video de documentos y auditoría no está versionado en este repositorio; debe
  adjuntarse o registrarse mediante un enlace controlado antes de marcarlo como
  entregado.
- La aceptación institucional, firmas y decisión final pertenecen a la autoridad
  designada; no pueden ser generadas por este cambio.

## 4. Acciones necesarias para marcar 100 %

| Acción | Responsable | Evidencia de cierre |
| --- | --- | --- |
| Revisar resultados y manual API | Estuardo | Comentario/revisión en PR o ficha firmada |
| Validar almacenamiento y recuperación | Daniel | Revisión de `informe-recuperacion.md` y corrida reproducida |
| Ejecutar flujo documental con usuario representativo | Estuardo + Diana | Registro UAT con candidato SHA, perfil, pasos y resultado |
| Completar video de documentos y auditoría | Roí/Estuardo | Índice, enlace controlado, versión y fecha |
| Ejecutar casos omitidos aplicables | Daniel/Roí | Nueva corrida con entorno y evidencia reproducibles |
| Actualizar matriz final | Pablo + Roí | Filas con ejecución, evidencia, incidencia y SHA final |
| Emitir aceptación institucional | Autoridad designada | Acta o reporte de aceptación verificable |

Hasta registrar esas evidencias, la clasificación correcta es **evidencia técnica
completa con cierre operativo pendiente**, no “100 % aceptado”.

