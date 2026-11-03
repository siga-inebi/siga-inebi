# Docker Testing

## Recomendado

Backend en contenedor de prueba aislado:

```bash
docker compose -f compose.yml -f compose.test.yml run --rm backend-test
```

Suite casi CI local:

```bash
make ci-local
```

## Garantias

- PostgreSQL de pruebas separado de desarrollo.
- Datos efimeros.
- Migraciones automaticas antes de pytest.
- Codigo de salida distinto de cero si falla test, lint, cobertura o seguridad.

## Frontend en Docker

```bash
docker compose run --rm frontend npm run test:coverage
docker compose run --rm frontend npm run build
```
