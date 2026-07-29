# ADR-0002: Modular Monolith

## Estado

Accepted

## Contexto

Requerimientos cubren muchos dominios relacionados. Aun no hay evidencia que justifique microservicios. Se requiere evolucion sin sobrediseño.

## Decision

Implementar backend como monolito modular con apps Django separadas por dominio y contratos internos claros.

## Consecuencias

- Menor complejidad operativa inicial.
- Facilita transacciones y consistencia.
- Exige cuidar acoplamiento entre dominios.

## Alternativas consideradas

- Microservicios desde inicio.
- Monolito sin separacion de dominios.

## Condiciones que justificarian revisar decision

- Carga u organizacion del equipo que haga inviable despliegue unico.
- Necesidad demostrada de aislamiento fuerte por cumplimiento o escalado independiente.
