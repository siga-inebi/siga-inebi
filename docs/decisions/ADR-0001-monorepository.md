# ADR-0001: Monorepository

## Estado

Accepted

## Contexto

Proyecto inicia con equipo pequeno, requerimientos cambiantes, stack web y backend distintos pero estrechamente acoplados por negocio y trazabilidad.

## Decision

Usar monorepositorio con carpetas separadas para `frontend/`, `backend/`, `docs/`, `scripts/` y configuracion compartida minima.

## Consecuencias

- Trazabilidad y onboarding mas simples.
- Cambios transversales en un solo historial.
- Requiere disciplina para limites de dominio y tooling.

## Alternativas consideradas

- Repositorios separados para frontend y backend.
- Repositorio solo documental en fase inicial.

## Condiciones que justificarian revisar decision

- Equipos totalmente independientes con ciclos de despliegue desacoplados.
- Requisitos regulatorios o de seguridad que exijan aislamiento de repositorios.
