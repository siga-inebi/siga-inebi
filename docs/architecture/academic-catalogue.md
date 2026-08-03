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
- Errores en un unico envoltorio: `{"error": {"status_code": ..., "detail": ...}}`.
  `DomainError` se traduce a 400 en `config/api/exception_handler.py`, de modo que
  las vistas no lo capturan.
- Una referencia inexistente en la **ruta** devuelve 404; en el **cuerpo**, 400.
- Los listados anotan los contadores que serializan, para no disparar consultas
  por fila.

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
