# ADR-0007: Docker and Local Development Environments

## Estado

Accepted

## Contexto

Proyecto necesita entorno reproducible para equipo y tambien ruta local sin Docker obligatorio para desarrollo diario.

## Decision

Adoptar dos modos de trabajo:

- Docker Compose como modo recomendado de stack completo.
- Ejecucion local separada de frontend y backend como modo alterno.

## Consecuencias

- Onboarding y validacion integrados mas simples con Docker.
- Desarrollo puntual sin contenedores sigue siendo posible.
- Documentacion de URLs y variables debe ser muy clara para evitar confusion entre host navegador y red interna Docker.

## Alternativas consideradas

- Docker obligatorio para todo desarrollo.
- Solo modo local sin Compose.

## Condiciones que justificarian revisar decision

- Coste de mantenimiento dual demasiado alto.
- Necesidad de entornos adicionales mas cercanos a produccion con otro orquestador.
