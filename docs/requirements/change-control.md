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
