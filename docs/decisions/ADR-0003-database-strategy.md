# ADR-0003: Database Strategy

## Estado

Accepted

## Contexto

Stack obligatorio exige SQLite para desarrollo local inicial y PostgreSQL para pruebas, staging y produccion.

## Decision

Usar SQLite solo para desarrollo local temprano. Diseñar y validar comportamiento objetivo contra PostgreSQL en pruebas automatizadas y ambientes no locales.

## Consecuencias

- Arranque local simple.
- Riesgo de diferencias entre motores si no se prueba temprano en PostgreSQL.
- Requiere evitar dependencias no portables o documentarlas.

## Alternativas consideradas

- PostgreSQL en todos ambientes desde dia uno.
- SQLite en todos ambientes iniciales.

## Condiciones que justificarian revisar decision

- Complejidad local aceptable con PostgreSQL desde inicio.
- Reglas de concurrencia o consultas que hagan insuficiente SQLite incluso para desarrollo.
