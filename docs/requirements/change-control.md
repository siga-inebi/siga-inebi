# Change Control

## Objetivo

Controlar evolucion de requerimientos sin perder trazabilidad.

## Reglas

1. Todo cambio debe conservar ID original del requerimiento afectado.
2. Si cambio altera significado material, registrar observacion y decision asociada.
3. Si aparece requerimiento nuevo, crear ID nuevo. No reciclar IDs.
4. No marcar requerimiento como implementado sin prueba verificable.
5. Todo cambio de alcance debe actualizar:
   - `requirements-catalogue.md`
   - `traceability-matrix.md`
   - ADR o `pending-decisions.md` si aplica

## Flujo

1. Solicitud de cambio.
2. Analisis de impacto en dominio, seguridad, datos y pruebas.
3. Decision explicita o ADR si cambia arquitectura.
4. Actualizacion de catalogo y trazabilidad.
5. Implementacion futura con referencia cruzada.

## Estados sugeridos

- `Proposed`
- `Approved`
- `Deferred`
- `Rejected`
- `Implemented`

## Causas tipicas de cambio

- Regla de negocio incompleta.
- Contradiccion entre RF y narrativa funcional.
- Politica institucional nueva.
- Restriccion tecnica o legal confirmada.

## Registro de cambios

| ID | Fecha | Requerimientos | Cambio | Decisión | Estado |
| --- | --- | --- | --- | --- | --- |
| CC-001 | 2026-10-23 | RF-CRE-001, RF-CRE-002, RF-CRE-003, RF-CRE-004; RNF-PRI-001 | El QR deja de mostrarse una sola vez. Una credencial vigente se reimprime sin revocarla mediante `POST /attendance/credentials/qr/`, con el permiso nuevo `attendance.credential.print` (migración `identity.0019`, sin concesiones automáticas a roles existentes) y el asiento `attendance.credential.qr_revealed`, que no guarda el token. Se agrega la exportación individual y por lote (PDF carta 2 × 4 con marcas de corte, PNG o ZIP) con un wireframe de 96 × 54 mm generado en el servidor; la vista previa no emite nada y la confirmación emite las faltantes solo con `attendance.credential.issue`. Revocar queda para extravío o retiro. | Aprobada por el responsable del producto en el plan de la entrega «Carnés exportables + importación CSV». El QR sigue codificando solo el identificador opaco. | Implemented |
| CC-002 | 2026-10-23 | RF-EXP-011 (nuevo); RF-EXP-001, RF-EXP-010 | Requerimiento nuevo: importación de estudiantes desde CSV, todo o nada, con plantilla, vista previa por fila y confirmación verificada por SHA-256 (409 si el archivo cambió, 422 si alguna fila falla, nada insertado). Cada fila pasa por `create_student`. Un CUI que ya pertenece a una persona registrada es un error: esa persona se da de alta desde «Convertir persona» (RF-EXP-010). | Aprobada en el mismo plan. **Decisión pendiente:** la plantilla aprobada no incluye nacionalidad, dirección, departamento ni municipio, que el alta individual exige (`validate_institutional_person`), y solo `nombres` y `apellidos` son obligatorios. Los estudiantes importados quedan en preinscripción con esos datos por completar. Si la institución exige el expediente completo desde la importación, la plantilla debe crecer en una entrega posterior. | Implemented |
| CC-003 | 2026-10-23 | RNF-COM-002 | El incremento máximo por ruta lazy pasa de 20.000 a 21.000 bytes gzip (`frontend/scripts/check-build-budget.mjs`). Motivo: `DocentesPage` estaba a 22 bytes del límite y agrupar las acciones del listado de Estudiantes en un menú «⋯» (que reutiliza la lógica de «Exportar CSV» sin el botón) lo deja en 20.031. Los límites de carga inicial (230.000) y de página en frío (250.000) no cambian, así que el peso total que paga el usuario sigue acotado por ellos. | Aprobada por el responsable del producto el 2026-10-23, frente a la alternativa de dejar «Exportar CSV» como botón visible. | Implemented |
