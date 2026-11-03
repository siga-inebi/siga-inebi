# TDD Guide

## Regla base

Red -> Green -> Refactor.

## Usar TDD cuando

- Regla de negocio cambia.
- Permiso o alcance cambia.
- API cambia.
- Bug debe quedar bloqueado por regresion.
- Calculo o servicio cambia.

## No forzar TDD cuando

- Documento cambia.
- Config trivial cambia.
- Maquetacion sin comportamiento cambia.
- Migracion automatica simple sin logica cambia.

## Ejemplos

Crear prueba especifica backend:

```bash
cd backend
DATABASE_ENGINE=postgresql DATABASE_NAME=siga_inebi DATABASE_USER=siga_inebi DATABASE_PASSWORD=siga_inebi_dev_password DATABASE_HOST=127.0.0.1 DATABASE_PORT=5432 ./.venv/bin/pytest tests/permissions/test_identity_permissions.py -k self_assign
```

Crear prueba especifica frontend:

```bash
cd frontend
npm run test -- src/test/apiClient.test.js
```

## Regresion

- Reproducir bug con prueba roja.
- Corregir bug sin debilitar contrato previo.
- Verificar misma prueba falla si se revierte fix.
