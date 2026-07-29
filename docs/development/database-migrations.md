# Database Migrations

## Principios

- Migraciones pequenas y revisables.
- Compatibles con PostgreSQL.
- No mezclar refactor grande de datos sin plan de rollback.
- Preservar historia y vigencias.

## Reglas futuras

- Una migracion por cambio coherente.
- Validar datos historicos sensibles.
- Documentar efectos sobre indices, locks y tiempo de ejecucion.
