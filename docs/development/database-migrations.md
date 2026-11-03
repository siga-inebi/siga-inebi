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

## Estado actual

- Migraciones iniciales creadas para:
  - `people`
  - `academics`
  - `students`
  - `identity`
  - `audit`
  - `enrolments`

## Ejecucion

### Docker

```bash
docker compose exec backend python manage.py makemigrations --check --dry-run
docker compose exec backend python manage.py migrate
```

### Local con PostgreSQL

```bash
DATABASE_ENGINE=postgresql DATABASE_HOST=127.0.0.1 DATABASE_PORT=5432 python manage.py migrate
```

### Local con SQLite

```bash
DATABASE_ENGINE=sqlite python manage.py migrate
```
