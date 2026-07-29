# AGENTS.md

Este archivo aplica a agentes de IA y desarrolladores humanos.

## Reglas de trabajo

1. Leer requerimientos y ADR antes de modificar dominio.
2. No implementar funcionalidades no solicitadas.
3. No cambiar contratos publicos sin documentarlo.
4. Anadir pruebas antes o junto con cada cambio.
5. No incluir secretos.
6. No usar datos reales.
7. Mantener compatibilidad con PostgreSQL.
8. No acoplar reglas de negocio a vistas, serializadores, componentes o templates.
9. Mantener modulos independientes y cohesionados por dominio.
10. Actualizar trazabilidad cuando se implemente un RF o RNF.
11. No marcar RF como completado sin pruebas verificables.
12. No eliminar historial auditable.
13. Solicitar decision explicita ante ambiguedad material.

## Expectativas de arquitectura

- Monorepo.
- Monolito modular.
- Apps Django separadas por dominio.
- React/Vite en frontend.
- Django REST Framework para API JSON.
- ORM Django como via principal de acceso a datos.
- Binarios fuera de base de datos.

## Expectativas de autorizacion

- Denegacion por defecto.
- Multiples roles por usuario.
- Permisos atomicos con alcance obligatorio.
- Cuenta siempre vinculada a persona institucional.
- Lecturas y escrituras sensibles auditables segun requerimientos.

## Higiene de cambios

- Preferir cambios pequenos y trazables.
- Conservar historia y estados antes que eliminacion fisica.
- Documentar decision pendiente si requerimiento no cierra regla.
