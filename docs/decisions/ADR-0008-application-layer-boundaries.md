# ADR-0008: Application Layer Boundaries

## Estado

Accepted

## Contexto

Las vistas de distintos dominios consultaban modelos directamente y algunos modulos de consulta
ubicados bajo `api/` importaban excepciones de Django REST Framework. Ademas, reglas de
autorizacion podian emitir excepciones Django o DRF desde servicios de dominio. Esta mezcla hace
que la capa de datos dependa de HTTP, repite filtros de visibilidad y permite respuestas de error
distintas para la misma condicion funcional.

## Decision

Cada app Django organiza su codigo de aplicacion en los siguientes limites:

- `api/`: adaptadores HTTP; reciben solicitudes, invocan consultas o servicios y serializan
  respuestas. No acceden al ORM de forma directa.
- `queries.py`: operaciones de lectura del dominio. Dependen de modelos y ORM Django, nunca de
  DRF, HTTP o `Request`.
- `services.py`: casos de uso de escritura, invariantes, transacciones y auditoria.
- `apps.common.exceptions`: excepciones independientes de framework para reglas de dominio,
  inexistencia de recursos y denegaciones de autorizacion.

El manejador central de excepciones mapea esas excepciones a los codigos HTTP existentes y conserva
el sobre de error documentado. La inyeccion de dependencias se aplica por limites de modulo:
vistas dependen de las interfaces de consulta y servicio de su dominio, no de modelos. No se
introduce un contenedor de inyeccion de dependencias, porque agregaria complejidad sin una necesidad
demostrada en el monolito modular actual.

## Consecuencias

- Las reglas de visibilidad, estado institucional y alcance pueden concentrarse en consultas o
  servicios reutilizables.
- Las vistas se reducen a adaptadores delgados y son mas faciles de probar.
- Los errores de dominio, recurso y autorizacion tienen una unica ruta de serializacion.
- Cada dominio incorpora un archivo de consultas adicional; el equipo debe mantenerlo cohesionado y
  no usarlo como repositorio generico entre dominios.
- Los contratos de error se documentan y se prueban para evitar regresiones al mover codigo entre
  capas.

## Alternativas consideradas

- Mantener consultas ORM dentro de las vistas.
- Usar excepciones DRF directamente desde consultas y servicios.
- Crear repositorios genericos y un contenedor de inyeccion de dependencias para todos los modelos.
- Migrar inmediatamente a microservicios.

## Condiciones que justificarian revisar decision

- Una necesidad medida de sustituir implementaciones de consulta en tiempo de ejecucion.
- Multiples adaptadores de entrada que requieran composicion mas avanzada de casos de uso.
- Un requisito de integracion que exija separar un dominio del monolito modular.
