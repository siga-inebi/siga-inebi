# Database Strategy

## Motores por ambiente

| Ambiente | Motor | Estado |
| --- | --- | --- |
| Desarrollo rapido local | SQLite | Opcional |
| Desarrollo recomendado | PostgreSQL | Recomendado |
| Pruebas automatizadas | PostgreSQL | Obligatorio |
| Staging | PostgreSQL | Obligatorio |
| Produccion | PostgreSQL | Obligatorio |

## Motivo

- SQLite acelera arranque y exploracion local.
- PostgreSQL es referencia de comportamiento objetivo, integridad y compatibilidad.

## Reglas

- No depender de SQLite en CI.
- No usar SQLite en staging o produccion.
- Validar migraciones y pytest sobre PostgreSQL.
- Mantener modelos y consultas compatibles con ambos solo donde aplica a desarrollo.
