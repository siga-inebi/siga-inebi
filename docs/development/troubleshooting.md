# Troubleshooting

## `python3` sin SSL

Sintoma:

- `ModuleNotFoundError: No module named '_ssl'`

Accion:

- Crear `venv` con `/usr/bin/python3` en macOS si `python3` apunta a instalacion rota.

## Backend local no conecta a PostgreSQL

Sintoma:

- `connection to server at "127.0.0.1", port 5432 failed`

Accion:

1. Confirmar `docker compose ps`
2. Verificar `db` en estado `healthy`
3. Revisar variables `DATABASE_*`

## Frontend local no llama API correcta

Accion:

- Verificar `VITE_API_URL`
- Docker navegador host: `http://127.0.0.1:8000/api/v1`
- Frontend local contra backend local: `http://127.0.0.1:8001/api/v1`

## `pytest` falla por configuracion de test

Sintoma:

- `Test settings require DATABASE_ENGINE=postgresql.`

Accion:

- Ejecutar pruebas con PostgreSQL. Eso es comportamiento esperado, no bug.

## Vulnerabilidades npm

Estado actual:

- `npm install` y `npm ci` reportan 7 vulnerabilidades altas transitivas.

Accion:

- Revisar con `npm audit`
- Resolver en siguiente iteracion controlada para no introducir cambios grandes en fundacion
