# Docker Setup

## Modo recomendado

```bash
cp .env.example .env
docker compose up --build
```

## Servicios

- `db`: PostgreSQL 16 con volumen persistente y `pg_isready`.
- `backend`: Django con migraciones al arranque, wait-for-postgres y health check.
- `frontend`: Vite en modo desarrollo con hot reload y health check HTTP.

## Puertos por defecto

- Frontend: `5173`
- Backend: `8000`
- PostgreSQL: `5432`

## Comandos utiles

```bash
docker compose ps
docker compose logs -f
docker compose exec backend python manage.py check
docker compose exec backend python manage.py seed_demo_data
```

## Persistencia

- Base de datos: volumen `postgres_data`
- `node_modules` frontend en Docker: volumen `frontend_node_modules`

## Notas

- `compose.yml` define base portable.
- `compose.override.yml` agrega bind mounts, hot reload, puertos y variables de desarrollo.
- No usar `localhost` entre contenedores; backend usa host interno `db`.
