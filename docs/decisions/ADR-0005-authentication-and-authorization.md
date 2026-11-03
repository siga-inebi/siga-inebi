# ADR-0005: Authentication and Authorization

## Estado

Accepted

## Contexto

Requerimientos obligan multiples roles, permisos atomicos, alcances obligatorios, denegacion por defecto y vinculo de cuenta con persona institucional.

## Decision

Usar autenticacion de sesion web y autorizacion basada en `RBAC + scoped grants`, con evaluacion por operacion.

## Consecuencias

- Modelo expresivo para docentes, encargados y personal multiple.
- Mayor complejidad que roles fijos simples.
- Debe evitarse duplicar reglas de autorizacion en UI.

## Alternativas consideradas

- Roles fijos sin permisos atomicos.
- ACL ad hoc por modulo.
- Politicas globales sin alcance contextual.

## Condiciones que justificarian revisar decision

- Requerimientos regulatorios que exijan modelo distinto.
- Evidencia de complejidad excesiva que pueda simplificarse sin romper RF.
