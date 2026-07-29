# ADR-0004: REST API

## Estado

Accepted

## Contexto

Stack obligatorio y requerimientos apuntan a API JSON con frontend web separado.

## Decision

Exponer capacidades por API REST JSON construida con Django REST Framework.

## Consecuencias

- Contratos claros entre frontend y backend.
- Facilita pruebas, trazabilidad y futura integracion.
- Requiere convenciones de versionado y errores consistentes.

## Alternativas consideradas

- Renderizado servidor tradicional.
- GraphQL desde inicio.

## Condiciones que justificarian revisar decision

- Casos futuros con necesidades de consulta compuesta que REST no cubra razonablemente.
- Requerimiento confirmado de clientes heterogeneos con contrato distinto.
