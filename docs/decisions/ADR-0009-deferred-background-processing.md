# ADR-0009: Deferred Background Processing

## Estado

Accepted

## Contexto

RNF-REN-003 requiere que las operaciones pesadas no bloqueen la solicitud web y
que los lotes se procesen fuera del ciclo sincrono. El monolito actual dispone de
Django, PostgreSQL, React/Vite y Docker Compose; no dispone de un contrato de
trabajos durables, una politica de reintentos, observabilidad de ejecuciones ni
un proceso trabajador reproducible.

Introducir una cola o un proceso trabajador sin esos elementos trasladaria el
riesgo a operaciones invisibles: trabajos perdidos, reintentos no idempotentes,
secretos adicionales o una instalacion Docker que no representa produccion.

## Decision

Se difiere la implementacion de procesamiento en segundo plano. Hasta que exista
una decision posterior aprobada, SIGA-INEBI no incorporara Redis, Celery, Kafka,
Kubernetes, servicios externos ni otro mecanismo de cola.

Las operaciones actuales permanecen sincrónicas, acotadas y trazables. No se
simulara una cola con hilos, tareas en memoria ni respuestas que prometan una
ejecucion futura sin persistencia verificable.

El issue #288 es la continuacion tecnica de esta decision y no puede iniciarse
sin cumplir las condiciones de revision definidas en este ADR.

## Consecuencias

- Las funciones que puedan exceder el presupuesto de una solicitud web deben
  limitar su entrada, paginar o declararse fuera de alcance hasta contar con un
  mecanismo aprobado.
- Los contratos HTTP no expondran estados de trabajo inexistentes.
- Docker Compose conserva un conjunto reducido y reproducible de servicios.
- RNF-REN-003 queda en estado `Deferred`; esta decision no afirma que exista un
  worker ni que el requisito de rendimiento este implementado.

## Condiciones para revisar la decision

Antes de implementar #288 se debe aprobar una propuesta que incluya:

- casos de uso medidos que justifiquen salir del ciclo sincrono;
- contrato persistido e idempotente de trabajo, estado e historial;
- reintentos, manejo de fallos, apagado ordenado y observabilidad;
- permisos, auditoria y proteccion de datos para cada trabajo;
- una configuracion Docker reproducible, sin secretos dentro del repositorio;
- pruebas automatizadas de exito, fallo, reintento y recuperacion.

## Alternativas consideradas

- Agregar Redis y Celery inmediatamente.
- Ejecutar tareas en hilos dentro del proceso web.
- Usar un servicio externo de colas.
- Introducir Kafka o Kubernetes antes de validar la necesidad operativa.

Todas se descartan por ahora: agregan infraestructura y superficie operativa sin
una necesidad medida ni las garantias de recuperacion exigidas.
