# Contributing to SIGA-INEBI

## Alcance de esta fase

Este repositorio esta en fase de fundacion documental y estructural. Antes de proponer codigo, leer:

- [AGENTS.md](AGENTS.md)
- [functional scope](docs/requirements/functional-scope.md)
- [requirements catalogue](docs/requirements/requirements-catalogue.md)
- [ADR index](docs/decisions/README.md)

## Reglas de contribucion

1. Trabajar desde rama dedicada.
2. Mantener trazabilidad entre requerimiento, diseno, codigo y prueba.
3. No implementar funcionalidad no solicitada.
4. No cambiar contratos publicos sin documentacion.
5. Agregar pruebas antes o junto con cada cambio funcional.
6. No usar secretos ni datos reales.
7. No eliminar historial auditable.

## Flujo esperado

1. Confirmar requerimiento o decision pendiente.
2. Revisar ADR y documentacion de dominio.
3. Definir alcance pequeno y verificable.
4. Implementar cambio con pruebas.
5. Actualizar trazabilidad y documentacion.
6. Abrir Pull Request para revision.

## Checklist minima para Pull Request

- Requerimiento referenciado por ID.
- Decision arquitectonica respetada o actualizada.
- Pruebas agregadas o ajustadas.
- Impacto en seguridad y datos revisado.
- Sin secretos ni datos reales.
- Documentacion actualizada cuando aplique.
