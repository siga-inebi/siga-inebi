# Academic Catalogue

## Objetivo

Definir la estructura academica a la que se asignan las matriculas: sedes,
jornadas, niveles, grados, cursos y la oferta por ciclo.

## Forma del catalogo

```
Institution
  |
  +-- Campus ("sede")                      codigo unico por institucion
  |     +-- Shift ("jornada")              codigo unico por sede
  |
  +-- Level ("nivel")                      codigo y secuencia unicos por institucion
  |     +-- Grade ("grado")                codigo unico por institucion, secuencia unica en el nivel
  |     +-- LevelSubject                   vinculo curso <-> nivel, con obligatoriedad y carga horaria
  |
  +-- Subject ("curso")                    codigo unico por institucion
  |
  +-- AcademicCycle ("ciclo")
        +-- GradeOffering                  grado + jornada, unico por ciclo
              +-- Section                  nombre unico por oferta, con cupo declarado
```

`GradeOffering` es el nodo que responde la pregunta operativa: *que grado se
imparte, en que jornada, de que sede, en este ciclo*. La sede se deriva de la
jornada, no se duplica en la oferta.

`Section` no guarda ciclo, grado ni jornada: los expone como propiedades de su
oferta. Asi no existe forma de crear una seccion cuyo grado contradiga su ciclo.

## Reglas y por que existen

| Regla | Motivo |
| --- | --- |
| Codigos normalizados a mayusculas | Evita duplicados que solo difieren en capitalizacion |
| Codigo de sede/nivel/curso unico por institucion, incluso si esta inactivo | El codigo se conserva como historia; reutilizarlo debe ser deliberado |
| Codigo de jornada unico por sede | Dos sedes pueden tener su propia jornada `MAT` |
| Codigo de grado unico en toda la institucion | `G1` nunca significa dos grados distintos |
| La institucion de un grado siempre es la de su nivel | La columna derivada que hace posible la regla anterior no puede desviarse |
| `sequence` unica por institucion (nivel) y por nivel (grado) | El orden pedagogico debe ser inequivoco |
| Una sola sede principal por institucion | Promover una sede degrada la anterior en la misma operacion |
| Oferta y secciones se rechazan en ciclo cerrado | RF-EST-011: la estructura se congela al cerrar |
| Oferta permitida en ciclo borrador | El catalogo se arma antes de activar el ciclo |
| Ciclo, sede y nivel deben compartir institucion | Impide ofertas cruzadas entre instituciones |
| Elementos inactivos no pueden entrar en una oferta nueva | Desactivar significa "ya no se usa hacia adelante" |
| Desactivar en lugar de borrar | RF-EST-012 y ADR-0006 |
| No se desactiva lo que un ciclo no cerrado esta usando | Evita dejar matriculas apuntando a estructura retirada |
| Quitar una oferta exige quitar antes sus secciones | Ninguna seccion queda huerfana en silencio |
| La capacidad no baja de la ocupacion activa | RF-EST-008: el cupo declarado debe seguir siendo cierto |
| `capacity = 0` significa sin limite | Permite operar durante la configuracion inicial |
| Una seccion con matriculas activas no se desactiva | Primero se mueven o retiran los estudiantes |
| La seccion debe pertenecer al ciclo y grado de la matricula | Impide matriculas contradictorias |

Todas viven en `apps/academics/services.py`. Vistas y serializadores no repiten
ninguna (AGENTS.md #8).

## Comportamiento bajo concurrencia

Las reglas anteriores describen que se rechaza. Estas describen *como* se
sostienen cuando dos peticiones llegan a la vez.

- **La unicidad la impone la base de datos, no una lectura previa.** Comprobar
  y luego insertar deja una ventana donde dos peticiones pasan la comprobacion
  y la perdedora revienta con `IntegrityError` (500) en lugar del `DomainError`
  (400) que promete la API. Los servicios insertan directamente y
  `apps/common/db.unique_violation_as` traduce la violacion a `DomainError`
  usando el nombre de la constraint. Una constraint no mapeada se re-lanza: es
  un bug, y esconderlo tras un 400 lo volveria invisible.
- **Una sola sede principal**, garantizada por un indice unico parcial sobre
  `institution` con `is_main = true`. El degradar-luego-insertar del servicio no
  basta: dos transacciones pueden degradar antes de que cualquiera inserte.
- **El cupo se decide con la fila de la seccion bloqueada**
  (`select_for_update`). Es una decision leer-y-luego-escribir: sin el bloqueo,
  dos matriculas simultaneas leen la misma ocupacion y juntas superan el cupo
  declarado. Verificado con un test de hilos reales en
  `tests/integration/test_concurrency.py`.

- **El codigo de grado es unico en toda la institucion**, garantizado por un
  indice unico. Un indice no puede abarcar un join, asi que `Grade` lleva una
  columna `institution` derivada de su nivel. La copia no puede desviarse: se
  calcula en `save` y una clave foranea compuesta
  `(level_id, institution_id) -> level (id, institution_id)` vuelve
  irrepresentable cualquier desacuerdo con el nivel, tanto al cambiar la
  institucion como al mover el grado a un nivel ajeno. No es deferrable: el
  rechazo ocurre en la sentencia culpable, no despues en el commit.

## Contrato HTTP

Prefijo `/api/v1/academics/`. Todos los endpoints requieren sesion autenticada.
El esquema OpenAPI se publica en `/api/v1/schema/` y la UI en `/api/v1/docs/`.

| Recurso | Endpoints |
| --- | --- |
| Sedes | `GET POST campuses/` · `GET PATCH DELETE campuses/{id}/` |
| Jornadas | `GET POST campuses/{id}/shifts/` · `GET PATCH DELETE shifts/{id}/` |
| Niveles | `GET POST levels/` · `GET PATCH DELETE levels/{id}/` |
| Grados | `GET POST levels/{id}/grades/` · `GET PATCH DELETE grades/{id}/` |
| Cursos | `GET POST subjects/` · `GET PATCH DELETE subjects/{id}/` |
| Curso en nivel | `GET POST levels/{id}/subjects/` · `PATCH DELETE levels/{id}/subjects/{subject_id}/` |
| Ciclos | `GET POST cycles/` · `GET cycles/{id}/` · `POST cycles/{id}/open/` · `POST cycles/{id}/close/` |
| Oferta | `GET POST cycles/{id}/offerings/` · `GET DELETE offerings/{id}/` |
| Secciones | `GET POST offerings/{id}/sections/` · `GET PATCH DELETE sections/{id}/` |

Convenciones aplicadas:

- Identificadores opacos (`public_id`) hacia el cliente; los `id` internos no se
  exponen.
- `DELETE` desactiva, no borra.
- Los listados devuelven solo registros activos salvo `?include_inactive=true`.
- **Todos los listados van paginados** con el envoltorio de DRF
  (`{count, next, previous, results}`, `PAGE_SIZE = 25`, parametro `?page=`).
  El esquema OpenAPI declara el tipo `Paginated<X>List` correspondiente.
- **El detalle de ciclo no incrusta sus secciones**: expone `offering_count` y
  `section_count`, y las filas se consultan paginadas en
  `offerings/{id}/sections/`. Un ciclo puede tener cientos de secciones.
- Errores en un unico envoltorio: `{"error": {"status_code": ..., "detail": ...}}`.
  `DomainError` se traduce a 400 en `config/api/exception_handler.py`, de modo que
  las vistas no lo capturan.
- Una referencia inexistente en la **ruta** devuelve 404; en el **cuerpo**, 400.
- Un filtro con un public ID inexistente devuelve lista vacia; **mal formado
  devuelve 400**, no 500 (`apps/common/parsing.parse_uuid`).
- Los listados anotan los contadores que serializan, para no disparar consultas
  por fila.

## Forma del codigo HTTP

`apps/academics/api/views.py` no repite el ciclo peticion/respuesta por recurso.
`CatalogueListCreateView` y `CatalogueDetailView` contienen los handlers, y los
mixins `RetrieveMixin` / `UpdateMixin` / `DeactivateMixin` deciden que verbos
expone cada recurso, de modo que una vista sin `PATCH` simplemente no hereda ese
mixin. Cada vista concreta declara sus serializadores y las dos o tres lineas
propias: que queryset lista y a que servicio llama. La documentacion OpenAPI se
adjunta con `extend_schema_view`, asi que sigue siendo especifica por recurso
aunque los handlers sean heredados.

## Limitacion vigente

La institucion se resuelve en `apps/academics/api/queries.resolve_institution`,
que hoy devuelve la unica institucion configurada. Cuando se implemente el
alcance institucional (RF-ALC), ese es el unico punto a cambiar.

## Fuera de alcance de esta iteracion

- Autorizacion por permiso atomico y alcance: los endpoints solo exigen sesion.
- `CurriculumPlan` (plan de estudios por ciclo y grado, RF-EST-005) sigue como
  estaba; `LevelSubject` describe el catalogo del nivel, no el plan del ciclo.
- Bloques de horario por jornada (RF-HOR-001) y parametros de jornada de
  asistencia (RF-JOR-001), que son un concepto distinto de `Shift`.
