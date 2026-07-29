# ADR-0006: Soft Delete and History

## Estado

Accepted

## Contexto

Requerimientos exigen conservar historia, evitar perdida de trazabilidad, persistir movimientos y no eliminar documentos.

## Decision

Preferir desactivacion, revocacion, versionado o estados antes que eliminacion fisica en registros historicos y auditables.

## Consecuencias

- Mejor trazabilidad y recuperacion de contexto.
- Requiere consultas conscientes de vigencia y estado.
- Necesita politicas claras para retencion y archivado.

## Alternativas consideradas

- Borrado fisico por defecto.
- Mezcla inconsistente de hard delete y soft delete.

## Condiciones que justificarian revisar decision

- Obligacion legal explicita de eliminacion definitiva por tipo de dato.
- Costos operativos desmedidos sin estrategia de archivado adecuada.
