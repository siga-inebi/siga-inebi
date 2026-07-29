# Testing Strategy

## Principios

- Pruebas automatizadas son requisito de cierre por cambio funcional.
- PostgreSQL es referencia obligatoria para suite automatizada.
- SQLite puede usarse en desarrollo local temprano, no como unica validacion.

## Capas previstas

- Unitarias de dominio.
- Integracion API.
- Permisos y alcances.
- Persistencia y migraciones.
- Flujos criticos de asistencia y documentos.

## Prioridades iniciales

- Authn/authz.
- Matricula y vigencias.
- Idempotencia de asistencia.
- Auditoria sensible.
- Resultados academicos clave.
