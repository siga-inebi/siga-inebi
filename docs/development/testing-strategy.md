# Testing Strategy

## Principios

- Docker es metodo reproducible recomendado.
- Desarrollo local sigue habilitado para velocidad.
- TDD aplica por defecto a reglas de negocio, permisos, alcances, calculos, servicios, APIs y bugs.
- Cada bug corregido debe dejar prueba de regresion.
- PostgreSQL es obligatorio para backend automatizado.
- SQLite solo sirve para desarrollo rapido, nunca para validar suite final.

## Flujo TDD

1. Escribir prueba roja.
2. Implementar cambio minimo para verde.
3. Refactorizar con suite en verde.

## Estructura backend

- `tests/unit/`
- `tests/integration/`
- `tests/api/`
- `tests/permissions/`
- `tests/migrations/`
- `tests/factories/`

## Marcadores backend

- `unit`
- `integration`
- `api`
- `permissions`
- `slow`
- `postgres`
- `migration`
- `security`

## Cobertura minima

- Backend: 70 %
- Frontend: 60 %

## Comandos clave

```bash
make test-backend
make test-backend-unit
make test-backend-integration
make test-frontend
make coverage
make ci-local
```

## Prioridades iniciales

- Authn y authz.
- Alcances por rol.
- Matricula y vigencias.
- Auditoria sensible.
- Seeds idempotentes.
