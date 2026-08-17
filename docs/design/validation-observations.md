# Bitacora de observaciones de validacion

Registro de lo que la institucion observa sobre wireframes, mapa de navegacion y
prototipo, y de que se hizo con cada observacion.

Metodo de la sesion: [`prototype-validation.md`](prototype-validation.md).

## Como usar esta bitacora

1. Durante la sesion se anota todo en la tabla de observaciones, sin filtrar.
2. Despues de la sesion se clasifica tipo y prioridad.
3. Al aplicar un cambio se anota el archivo modificado en la columna `Resolucion`
   y se pasa el estado a `Aplicada`.
4. Las observaciones sin definicion institucional pasan a
   [`pending-decisions`](../decisions/pending-decisions.md) y se marcan `Trasladada`.

Valores permitidos:

| Campo | Valores |
| --- | --- |
| Tipo | contenido, flujo, terminologia, permiso, alcance |
| Prioridad | alta, media, baja |
| Impacto | wireframe, navegacion, prototipo, requerimiento |
| Estado | abierta, aceptada, rechazada, aplicada, trasladada |

## Sesiones realizadas

| Sesion | Fecha | Modulos revisados | Participantes | Observaciones | Altas abiertas |
| --- | --- | --- | --- | --- | --- |
| S-01 | pendiente | | | | |
| S-02 | pendiente | | | | |

## Observaciones

| Id | Sesion | Pantalla | Observacion | Origen | Tipo | Prioridad | Impacto | Estado | Resolucion |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| OBS-001 | | | | | | | | abierta | |
| OBS-002 | | | | | | | | abierta | |
| OBS-003 | | | | | | | | abierta | |
| OBS-004 | | | | | | | | abierta | |
| OBS-005 | | | | | | | | abierta | |

Ejemplo de fila completada, solo como referencia de formato. Eliminar al
registrar la primera sesion real:

| Id | Sesion | Pantalla | Observacion | Origen | Tipo | Prioridad | Impacto | Estado | Resolucion |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| OBS-000 | S-01 | Asistente de matricula | "Aqui primero pedimos los papeles y despues asignamos seccion, no al reves." | Secretaria | flujo | alta | wireframe, prototipo | aplicada | Se invirtieron los pasos 2 y 3 en wireframes.md seccion 9 y en prototipo-siga.html |

## Cambios aplicados al diseno

Una fila por cambio, no por observacion.

| Version | Fecha | Archivo | Cambio | Observaciones que lo motivan |
| --- | --- | --- | --- | --- |
| v1 | 2026-08-08 | wireframes.md, navigation-map.md, prototipo-siga.html | Version inicial para validacion | — |

## Confirmacion por rol

Cada perfil institucional confirma que lo que ve su rol corresponde a lo que
necesita y que no ve informacion que no le corresponde.

| Rol del sistema | Confirma | Persona | Fecha | Estado |
| --- | --- | --- | --- | --- |
| Administrador del sistema | Informatica | | | pendiente |
| Director | Direccion | | | pendiente |
| Coordinador academico | Coordinacion | | | pendiente |
| Personal administrativo | Secretaria | | | pendiente |
| Docente | Representante docente | | | pendiente |
| Encargado o tutor | Direccion | | | pendiente |

## Preguntas abiertas trasladadas

Puntos sin definicion institucional. Nacen de la seccion `Pendientes de
definicion` de [`wireframes.md`](wireframes.md) y de la lista P1 a P12 de
[`prototype-validation.md`](prototype-validation.md).

| Id | Pregunta | Responde | Fecha comprometida | Estado |
| --- | --- | --- | --- | --- |
| P1 | Que indicadores deben ir en la parte superior del panel | Direccion | | abierta |
| P2 | Que campos son obligatorios al crear el expediente | Institucion | | abierta |
| P3 | Formato y regla del correlativo del codigo de estudiante | Institucion | | abierta |
| P4 | Quien autoriza el cierre de un ciclo escolar | Direccion | | abierta |
| P5 | Sedes, niveles, cursos y ciclos separados o agrupados en el menu | Institucion | | abierta |
| P6 | Lista oficial de requisitos documentales por tipo de ingreso | Institucion | | abierta |
| P7 | Si documentos incompletos permiten matricula provisional y quien la autoriza | Direccion | | abierta |
| P8 | Al exceder el cupo de una seccion, el sistema bloquea o solo advierte | Institucion | | abierta |
| P9 | Formato oficial y firma de la constancia de matricula | Institucion | | abierta |
| P10 | Formato oficial exigido por el Ministerio para la nomina | Institucion | | abierta |
| P11 | Quien registra y quien consulta datos de salud del estudiante | Direccion | | abierta |
| P12 | El portal de encargados entra en esta fase o se pospone | Direccion | | abierta |

## Estado general

| Indicador | Valor |
| --- | --- |
| Observaciones registradas | 0 |
| Abiertas de prioridad alta | 0 |
| Aplicadas al diseno | 0 |
| Preguntas abiertas sin definicion | 12 |
| Roles confirmados | 0 de 6 |

Criterio de cierre del bloque de diseno: sin observaciones de prioridad alta en
estado abierta, los seis roles confirmados y P1 a P12 resueltas o trasladadas
formalmente a `pending-decisions`.
