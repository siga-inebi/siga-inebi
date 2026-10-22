# API Conventions

## Estilo

- API REST con JSON.
- Versionado inicial por prefijo cuando exista implementacion, por ejemplo `/api/v1/`.
- Nombres tecnicos en ingles.
- Mensajes funcionales y documentacion visible en espanol cuando aplique.

## Convenciones base

- Recursos en plural.
- Identificadores opacos hacia cliente cuando convenga seguridad.
- Fechas y horas en ISO 8601.
- Interpretacion de fecha efectiva y eventos en zona horaria local del establecimiento.
- Errores consistentes con codigo, mensaje y detalles validables.

## Campos aditivos de cierre UX #632

- `GET /documents/types/` agrega `template_count` y `active_template_count`. Ambos conteos
  incluyen únicamente plantillas de la misma institución; el primero conserva el total
  histórico y el segundo cuenta las vigentes.
- Las respuestas de alertas institucionales agregan `student_name` y `student_code`. El
  identificador canónico para navegar y autorizar continúa siendo `student_id` (UUID público).
- Estos campos son aditivos. No cambian filtros, paginación, cuerpos de escritura ni códigos de
  estado.

## Paginacion y listados (docs/ux-ui.md 1.1)

- `apps.common.pagination.StandardPagination` es la clase por defecto
  (`DEFAULT_PAGINATION_CLASS`): `page_size = 25`, `page_size_query_param = "page_size"`,
  `max_page_size = 100`. Todo listado paginado responde `count`, `next`, `previous` y
  `results` y acepta `page` y `page_size`; un `page_size` invalido usa el valor por defecto
  y uno mayor a 100 se acota.
- Parametros uniformes de listado: `page`, `page_size`, `search`, `ordering`,
  `include_inactive` y los filtros propios del dominio. Cada dominio adopta `search`,
  `ordering` e `include_inactive` en sus listados al migrar sus pantallas.
- `apps.common.listing.search_and_order` aplica `search` y `ordering` sobre el queryset que ya
  construyó la consulta del dominio. `search` busca sin distinguir mayúsculas, como subcadena, en
  los campos que declara cada listado; vacío no filtra. `ordering` acepta solo las llaves de una
  lista blanca (`"name"`, `"-name"`, …, generadas con `descending_too`); un valor desconocido
  conserva el orden por omisión en vez de fallar. En `academics`, `CatalogueListCreateView`
  declara `search_fields` y `orderings` por vista y lo aplica antes de paginar; se combina con
  `include_inactive` y los filtros propios (#631).
- Una exportacion completa recorre paginas de 100 o usa un endpoint `/export/` del
  backend (por ejemplo `GET /api/v1/audit/events/export/`), nunca un tope silencioso.

## Limites de capa y errores

Cada dominio separa las responsabilidades de lectura, caso de uso y transporte HTTP:

- Las vistas y serializadores bajo `apps/<domain>/api/` traducen la solicitud y la respuesta HTTP.
  No construyen consultas ORM ni contienen reglas de negocio.
- Las consultas de lectura viven en `apps/<domain>/queries.py`. Pueden usar el ORM de Django, pero
  no importan DRF, objetos `Request`, respuestas HTTP ni excepciones de transporte.
- Los servicios bajo `apps/<domain>/services.py` coordinan escrituras, invariantes, transacciones y
  auditoria. No dependen de vistas ni serializadores.
- Las excepciones de aplicacion viven en `apps.common.exceptions`: `DomainError` representa una
  regla de negocio (HTTP 400), `ResourceNotFoundError` un recurso inexistente (HTTP 404) y
  `AuthorizationError` una denegacion de permiso o alcance (HTTP 403).

`FieldValidationError` (subclase de `DomainError`) es el rechazo de reglas sobre campos concretos:
responde HTTP 400 con `error.detail` igual a `{"campo": ["mensaje", ...]}`, la misma forma que
los errores de serializador de DRF (por ejemplo, cada regla de contraseña incumplida).

`config.api.exception_handler.api_exception_handler` es el unico punto que serializa estas
excepciones. El sobre de error se conserva como `error.status_code` y `error.detail`. Para errores
404 y 403, `detail` mantiene la forma `{"detail": "..."}` usada por DRF; asi el traslado de una
consulta o una regla fuera de una vista no rompe a los consumidores existentes.

## Resúmenes de matrícula (#632, M1)

Las respuestas que utilizan `EnrolmentSerializer` agregan cuatro objetos de solo lectura.
Se conservan `student_id`, `academic_cycle_id`, `grade_id` y `section_id`, los campos de
vigencia/estado y el sobre paginado existente.

| Objeto | Campos publicados |
| --- | --- |
| `student` | `public_id`, `full_name`, `student_code` |
| `academic_cycle` | `public_id`, `name` |
| `grade` | `public_id`, `name` |
| `section` | `public_id`, `name`, `grade_name`, `shift_name` |

Aplica a `GET /api/v1/enrolments/active/`, `GET /api/v1/enrolments/history/?student_id=...`
y las respuestas de alta/movimientos que reutilizan el serializador, incluida su variante
`MatriculationSerializer`. Los payloads de escritura mantienen sus UUID existentes; los
resúmenes no son entradas de esos endpoints. No se agregan CUI, domicilio, correo, teléfono,
salud ni datos del expediente de persona a los resúmenes.

Los nombres provienen de las entidades vinculadas actuales; no son una instantánea de sus
etiquetas al momento de matricular. Se preservan las referencias históricas aunque los perfiles
o secciones estén desactivados. El orden, la vigencia y la autorización de cada operación no
cambian. Los listados vigentes e históricos mantienen sus controles de sesión existentes.

Las lecturas precargan estudiante/persona, ciclo, grado y oferta de sección con grado/jornada:
serializar una página de 1 o 25 matrículas requiere una consulta, sin consultas adicionales por
fila. Esto se verifica en `backend/tests/api/test_enrolment_summaries_api.py`.

La tabla de Matrículas usa estos nombres sin pedir padrones para traducir UUID. El filtro de
estudiante reutiliza la búsqueda remota existente (dos caracteres como mínimo, espera de
300 ms, primera página y sugerencia de afinar la búsqueda). Solicita `include_inactive=true`
para consultar historial de perfiles desactivados; su soporte explícito se entrega en #635.
No recupera todas las páginas de coincidencias ni promete un catálogo completo.

Detalles y límites: [entrega M1](../development/632-enrolment-summaries.md).
## Listados de comunidad educativa (#632)

`GET /api/v1/people/`, `/teachers/`, `/students/` y `/students/guardians/`
aplican búsqueda y filtros antes de contar y paginar. Mantienen el sobre
`{count, next, previous, results}`, los identificadores y los campos de respuesta existentes.

| Parámetro | Contrato |
| --- | --- |
| `include_inactive` | Por defecto `false`: solo `is_active=true` del recurso listado. `true` incluye activos y desactivados, sin reactivar ni eliminar filas. |
| `search` | Búsqueda parcial sin distinguir mayúsculas mediante DRF `SearchFilter`. Todos los términos deben coincidir con alguno de los campos habilitados. Omitir o enviar vacío conserva el listado sin búsqueda. |
| `status` | Solo estudiantes: valor exacto de `Student.StudentStatus`, independiente de `is_active`. |
| `position` | Solo docentes: valor exacto de `Teacher.Position`, combinado con búsqueda y actividad. |
| `page` | Paginación existente de 25 elementos. `page_size`, orden configurable y exportación completa se entregan mediante #630 y la posterior migración de pantallas. |

Campos de búsqueda:

- Personas: nombre, apellido, CUI e identificador institucional.
- Estudiantes: nombre y apellido de persona, CUI y código estudiantil.
- Docentes: nombre y apellido de persona, CUI y código de empleado.
- Encargados: nombre y apellido de persona y CUI.

Valores publicados de `status`: `pre_enrolled`, `active`, `inactive`, `withdrawn`,
`graduated`, `transferred`. Valores de `position`: `Docente Titulado`, `Docente Interino`,
`Orientador/a`, `Administrativo`. Son valores del catálogo del modelo, no etiquetas traducidas
por el cliente. Los filtros deben omitirse cuando el selector representa «Todos».

`include_inactive` acepta las representaciones booleanas de DRF (incluidos `true/false`,
`1/0`, `yes/no`). Un booleano inválido o vacío, un estado o puesto desconocido o vacío
devuelve HTTP 400 con el nombre del parámetro en `error.detail`. Un filtro válido sin
coincidencias devuelve HTTP 200 con `count=0` y `results=[]`.

Compatibilidad: antes los cuatro endpoints mezclaban activos y desactivados aun sin parámetro.
Los consumidores que necesiten esa mezcla deben enviar `include_inactive=true`. El filtro afecta
al recurso listado, no al estado de su persona vinculada; la baja de una persona no se propaga
a sus perfiles. La consulta individual y los servicios conservan el acceso histórico existente.
En particular, un estudiante con `status=inactive` e `is_active=true` sigue apareciendo en el
listado normal: estado del expediente y baja lógica son dimensiones distintas.

La búsqueda no amplía autorización. Estudiantes conserva `student_view_basic` y su queryset de
alcance efectivo. Los otros tres endpoints conservan sus controles de sesión existentes; este
cambio no agrega permisos ni redefine su política de alcance. No se añaden campos sensibles a
las respuestas ni se guarda el término de búsqueda en auditoría de aplicación.

Personas desempata nombres iguales por `id`; Estudiantes y Docentes conservan sus códigos únicos
como orden, y Encargados su orden por apellidos, nombres e `id`. `select_related("person")` evita
consultas adicionales por fila en los perfiles. La paginación no ofrece una instantánea ante
escrituras concurrentes.

Implementación, pruebas, compatibilidad y pendientes: [entrega de comunidad educativa](../development/632-community-lists.md).

## Disponibilidad de aulas (RF-AUL-005)

- Las respuestas de aulas agregan `service_status`: `available` (Disponible),
  `unavailable` (Temporalmente inhabilitada) o `maintenance` (En mantenimiento).
- `PATCH /api/v1/academics/classrooms/{public_id}/` acepta ese campo opcional.
  Un valor invalido devuelve HTTP 400. Omitirlo conserva el estado actual.
- Las aulas nuevas y las existentes al migrar reciben `available`. La migracion
  conserva `is_active`: un aula dada de baja no se reactiva.
- El estado de servicio es independiente de la baja logica. Solo aulas activas y
  disponibles admiten nuevas sesiones o nuevas asignaciones como aula habitual.
  El rechazo ocurre en servicios de dominio y se expone como HTTP 400.
- Decision confirmada para #103: cambiar la disponibilidad conserva las sesiones
  y referencias existentes, incluso futuras. No se cancelan ni reasignan clases.
  Conservar la misma aula habitual al editar una seccion no es una nueva asignacion.
- Volver a `available` habilita nuevas asignaciones si el aula sigue activa.
  El cambio registra actor y valores anterior/posterior en la auditoria existente.
- Se conservan los controles de autenticacion e institucion del catalogo.
  Los servicios bloquean la fila del aula durante la asignacion y el cambio de
  disponibilidad para serializar ambas operaciones concurrentes.

## Advertencia de capacidad de aulas (RF-AUL-004)

- Las respuestas de seccion y sesion agregan `capacity_warning`, de solo lectura. Es `null`
  cuando no hay aula, alguna capacidad vale `0` o el aula puede alojar la capacidad declarada
  de la seccion.
- Cuando el aula es menor, el campo contiene `code=classroom_capacity_below_section`, un mensaje
  y los valores `classroom_capacity` y `section_capacity`.
- La advertencia aplica al aula habitual de la seccion y al aula concreta de una sesion. Es
  informativa: la asignacion se guarda y conserva las validaciones independientes de sede,
  disponibilidad y cruces.
- El valor se deriva al serializar y no se persiste; cambiar cualquiera de las capacidades se
  refleja en la siguiente lectura sin migracion ni sincronizacion adicional.

## Seguridad

- Sesion via cookie segura para frontend web.
- No exponer rutas directas a archivos.
- Endpoints sensibles requieren auditoria.
- Autorizacion evaluada por operacion, no solo por menu.

## Operaciones asincronas

- Procesos largos responden con estado aceptado o recurso de job cuando aplique.
- Generacion por lote no debe bloquear request sincrono.

## Borrado

- Evitar delete fisico en recursos historicos.
- Preferir estados, revocacion o desactivacion.

## Provision administrativa de cuentas

- `POST /api/v1/identity/accounts/` provisiona una cuenta pendiente vinculada a una persona,
  identificada por `person_public_id` (ADR-0011).
- La respuesta incluye el codigo de activacion inicial una sola vez y no debe almacenarse en cache.
- `POST /api/v1/identity/accounts/{public_id}/activation-challenges/` revoca el desafio anterior y
  emite uno nuevo.
- Ambos endpoints requieren sesion; los servicios de dominio exigen respectivamente
  `account.create` y `account.activate`.
- `POST /api/v1/identity/accounts/activate/` permite al titular canjear sin sesion previa el codigo
  mediante `username`, `activation_code` y `password`.
- La activacion devuelve una respuesta uniforme ante cuenta inexistente, codigo incorrecto,
  vencido, revocado, agotado o ya utilizado.

## Catalogo de permisos atomicos

- `GET /api/v1/identity/permissions/` devuelve el catalogo paginado de permisos atomicos.
- Requiere sesion y el permiso administrativo logico `role.assign`, representado en Django por
  `role_assign`; los superusuarios tambien pueden consultarlo.
- La respuesta publica usa codigos con punto, por ejemplo `attendance.record_entry`.
- La consulta exitosa y el intento autenticado denegado generan eventos de auditoria.
## Relaciones estudiante-encargado

- `GET /api/v1/students/guardian-relations/` lista solo relaciones de estudiantes dentro del
  alcance `student.view_basic`. Cada elemento conserva `guardian` como identificador y agrega
  `guardian_detail` de solo lectura con los datos necesarios para presentar al encargado.
- El filtro opcional `student_id` recibe el `public_id` UUID del estudiante y se aplica en el
  servidor antes de paginar, junto al filtro de alcance. Un UUID desconocido o fuera del alcance
  devuelve una colección vacía; un valor mal formado o vacío devuelve HTTP 400. Omitir el parámetro
  conserva el listado autorizado anterior. Las relaciones históricas se conservan.
- Relaciones, salud, observaciones y contactos devuelven el sobre paginado estándar
  (`count`, `next`, `previous`, `results`). Sus clientes solicitan cada página al navegar.
  Salud y observaciones desempatan fechas iguales por identificador descendente, conservando
  el orden por fecha más reciente y los controles de lectura sensible y auditoría por solicitud.
- `POST /api/v1/students/guardian-relations/` crea una asociacion; `is_primary` es calculado por
  el servicio y no se acepta en el payload.
- `POST /api/v1/students/guardian-relations/{id}/make-primary/` designa una relacion vigente como
  principal.
- `POST /api/v1/students/guardian-relations/{id}/end/` conserva el registro y termina el acceso.
  Debe incluir `replacement_relation` al terminar la relacion principal.
- `PATCH /api/v1/students/guardian-relations/{id}/` permite corregir exclusivamente
  `relationship_label`, con `student.edit_basic` y alcance. No modifica identidades,
  fechas, principal o actividad; campos adicionales se rechazan con 400. Antes era 405.
  El cambio se audita con valor anterior/nuevo y se revierte si falla la auditoria.
- El listado del expediente `/students/records/{public_id}/guardians/` agrega
  capacidades `actions` calculadas en servidor y acepta `replacement_for={id}` para
  consultar reemplazos validos del mismo estudiante por paginas. Ver
  [contratos y evidencia E5](guardian-relation-actions-ui.md).

## Observaciones del estudiante

E6 incorpora `PATCH /students/observations/{public_id}/` (`description`) y
`PATCH /students/health-notes/{public_id}/` (`content`), antes 405. Exigen lectura
sensible y edicion con alcance, conservan autor/fecha/estudiante y rechazan campos
adicionales. `DELETE` conserva la desactivacion 204; `include_inactive=true` permite
consultar su historial paginado. Los tres listados sensibles agregan `actions`
de presentacion y conservan POST y sus respuestas anteriores. Ver
[contratos, privacidad y evidencia E6](student-record-actions-ui.md).

- `GET /api/v1/students/{public_id}/observations/` exige `student.view_sensitive` y alcance sobre
  estudiante. Las observaciones viven fuera del resumen general.
- `POST` sobre misma ruta exige ademas `student.edit_basic`; autor se deriva de sesion y fecha no
  puede ser futura.
- `GET` y `DELETE /api/v1/students/observations/{public_id}/` conservan mismos controles. `DELETE`
  desactiva sin borrar historia.
- `PD-005` mantiene pendiente qué roles reciben permiso sensible; API no hardcodea roles.
## Notas de salud del estudiante

- `GET /api/v1/students/{public_id}/health-notes/` exige `student.view_sensitive` y alcance sobre
  el estudiante; cada consulta genera auditoria de lectura sensible.
- `POST` sobre la misma ruta exige ademas `student.edit_basic`; registra contenido no vacio, fecha
  no futura y autor autenticado. El contenido medico nunca se copia a la bitacora.
- `GET` y `DELETE /api/v1/students/health-notes/{public_id}/` conservan el mismo control. `DELETE`
  desactiva la nota sin borrar historia.
## Expediente estudiantil basico

- `POST /api/v1/students/` registra persona y expediente en una transaccion. Requiere
  `student.edit_basic` con alcance de modulo `students`; permiso sin alcance se deniega.
- `PATCH /api/v1/students/{id}/` modifica codigo, estado o fotografia mediante servicio de
  dominio y genera auditoria. Los datos de `Person` mantienen su endpoint propio.
- Estados publicados: `pre_enrolled`, `active`, `inactive`, `withdrawn`, `graduated` y
  `transferred`.
- Semantica del expediente: `pre_enrolled` conserva al estudiante para matricula o rematricula
  del siguiente ciclo; `active` habilita interacciones ordinarias; `withdrawn` conserva la salida
  por desercion; `graduated` conserva la salida tras completar el pensum; `transferred` indica
  salida hacia otra institucion; `inactive` representa una baja administrativa logica. Matricular,
  rematricular o registrar un traslado de ingreso cambia el expediente a `active`.
- `DELETE /api/v1/students/{id}/` desactiva el expediente; no elimina el registro ni su persona.
- La fotografia se clasifica `Restricted`; modificarla exige `student.edit_basic` y alcance sobre
  el estudiante. La carga admite hasta 5 MB y se valida por contenido; antes de almacenarla se
  corrige orientacion, recorta y normaliza con Pillow a JPEG de 295 x 354 pixeles.

## Ciclos escolares

- `GET /api/v1/academics/cycles/` lista ciclos de la institucion configurada.
- `GET /api/v1/academics/cycles/{public_id}/` devuelve el detalle historico del ciclo con ofertas
  de grado, jornadas, secciones, planes de estudio, asignaciones docentes y resumen agregado de
  matriculas. Incluye registros inactivos y no expone identidades estudiantiles.
- `POST /api/v1/academics/cycles/` registra un ciclo en preparacion con ano, identificacion,
  descripcion institucional y fechas no solapadas.
- `POST /api/v1/academics/cycles/{public_id}/activate/` activa un ciclo preparado solo cuando no
  existe otro ciclo activo. RF-CIC-003 ampliara este contrato con validacion de estructura completa.
- `POST /api/v1/academics/cycles/{public_id}/clone/` crea un ciclo independiente en preparacion a
  partir de un ciclo activo o cerrado (ADR-0011 D2, #631; un borrador se rechaza). Copia ofertas, jornadas referenciadas, secciones y planes; el campo
  `include_teaching_assignments` decide si tambien copia las asignaciones docentes vigentes.
  existe otro ciclo activo y la estructura disponible contiene grados ofertados, secciones y plan
  de estudios por grado. La validacion de unidades de evaluacion queda pendiente hasta que exista
  el modelo del dominio `academic-evaluation`.
- Todos requieren sesion autenticada. La definicion de permisos atomicos para Directora,
  Administrador y Secretario queda como decision pendiente del modelo de autorizacion.
- Las escrituras academicas consultan una politica compartida de estado del ciclo. Un ciclo cerrado
  rechaza creacion de matricula, cambio de seccion, asignacion y reasignacion docente y devuelve
  HTTP 400. El mensaje de error nombra la operacion denegada. Las consultas historicas permanecen
  disponibles y no se eliminan. La auditoria transversal de denegaciones corresponde a RF-BIT-004 y
  RNF-SEG-003 y no se declara implementada en este cambio.
- El cambio de seccion evalua la politica sobre el ciclo de la matricula de origen, por lo que la
  seccion destino debe pertenecer a ese mismo ciclo y grado. Una seccion de otro ciclo se rechaza
  con HTTP 400 y no puede usarse para escribir sobre un ciclo cerrado por la puerta de atras.
- Crear o reasignar una asignacion docente de un ciclo cerrado devuelve HTTP 400. El historial de
  asignaciones permanece consultable y no se elimina.

## Ciclo escolar y estructura académica (#631)

Cambios de contrato de la entrega 1 de #631. Todos son **aditivos**: ningún campo existente
cambia de nombre ni de forma, y los endpoints anteriores siguen respondiendo igual salvo el
cambio de regla de clonado (D2) y la caché de catálogos. Decisiones en el
[aporte D1–D3/D6 al ADR-0011](../decisions/ADR-0011-ciclo-escolar-d1-d2-d3-d6.md). Los mensajes
de error viajan en `error.detail` con el sobre habitual.

### Cambios de regla

- `POST /api/v1/academics/cycles/{public_id}/clone/` acepta un origen **activo o cerrado**
  (antes solo cerrado) y rechaza un borrador con HTTP 400: «No se puede clonar un ciclo en
  borrador; active o cierre el ciclo antes de clonarlo.». Con origen activo se copian solo las
  asignaciones vigentes. El clonado corre en una única transacción.
- Sedes, jornadas, niveles, cursos y secciones responden `Cache-Control: private, max-age=0`
  con `ETag` (antes `max-age=300`): el navegador revalida siempre y recibe 304 si nada cambió.
- El error de activación conserva su forma («La estructura del ciclo escolar está incompleta:
  …; ….»), ahora con tildes y con el faltante de ofertas en español.

### Ciclo escolar

| Método y ruta | Cuerpo | Respuesta | Permiso |
| --- | --- | --- | --- |
| `PATCH /academics/cycles/{id}/` | `{year?, name?, description?, starts_on?, ends_on?}` | 200 `AcademicCycle` (`public_id, year, name, description, starts_on, ends_on, status`). 400 si no está en borrador, si el año no coincide con `starts_on`, si las fechas se invierten, traslapan u ocupan nombre/año de otro ciclo | `scope.assign` sobre la institución |
| `POST /academics/cycles/{id}/revert-to-draft/` | `{reason}` (obligatorio, máx. 500) | 200 `AcademicCycle` con `status: "draft"`. 400 sin motivo, si no está activo o si tiene actividad (el detalle lista «Tiene N …») | `academic_cycle.revert` sobre la institución |
| `GET /academics/cycles/{id}/readiness/` | — | 200, ver forma abajo | Sesión (igual que el detalle del ciclo) |
| `GET /academics/cycles/{id}/non-computable-days/` | `page`, `page_size` | 200 paginado de `{public_id, academic_cycle_id, day, reason}` por fecha; solo días vigentes | Sesión |
| `POST /academics/cycles/{id}/non-computable-days/` | `{day, reason}` | 201 con la misma forma. 400 si la fecha está fuera del ciclo, si el motivo está vacío o si el día ya está declarado | `scope.assign` sobre la institución |
| `DELETE /academics/non-computable-days/{id}/` | — | 204. Desactiva el día (no lo borra) y audita `academics.non_computable_day.removed`; 400 si el ciclo está cerrado; 404 si ya fue retirado. Volver a declarar la fecha reactiva la misma fila | `scope.assign` sobre la institución |

`GET /academics/cycles/{id}/` (detalle histórico) no cambia. Auditoría nueva:
`academics.cycle.updated` (con `changes` antes/después), `academics.cycle.reverted_to_draft`
(con `reason` y `previous_status`) y `academics.non_computable_day.removed`.

Forma de `readiness`:

```json
{
  "activation": {
    "ready": false,
    "gaps": [
      {
        "code": "missing_teacher",
        "message": "Falta asignar docente para 'Matemática' en la sección 'A' del grado 'Primero'.",
        "grade": {"public_id": "…", "name": "Primero"},
        "section": {"public_id": "…", "name": "A"},
        "subject": {"public_id": "…", "name": "Matemática"}
      }
    ]
  },
  "revert": {
    "allowed": false,
    "blockers": [{"code": "enrolments", "count": 312, "message": "Tiene 312 matrículas."}]
  },
  "close": {"ready": false, "gaps": [{"code": "evaluation_unit_open", "message": "…"}]},
  "active_cycle": {"public_id": "…", "name": "Ciclo 2026"}
}
```

- `activation.gaps[].code`: `active_cycle_exists` (D1, hay otro ciclo activo),
  `no_grade_offerings`, `missing_sections`, `missing_curriculum_plan`, `missing_teacher` o
  `invalid_status` (el ciclo no está en borrador). `grade`, `section` y `subject` son `null`
  cuando no aplican.
- `revert.blockers[].code`: `enrolments`, `grades`, `attendance_events`,
  `closed_evaluation_units`, `issued_documents` o `invalid_status` (no está activo; `count`
  es `null`).
- `close.gaps[].code`: `evaluation_unit_open`, `recovery_window_open` o `invalid_status`.
- `active_cycle`: el otro ciclo activo de la institución, o `null`.

### Asignaciones docentes

`TeachingAssignmentSerializer` (creación, reasignación, historial, detalle histórico del ciclo
y los listados nuevos) agrega, sin quitar los `*_id`:
`section: {public_id, name, grade_name}`, `subject: {public_id, name, code}` y
`teacher: {public_id, name}` (el `public_id` es el del perfil Teacher, igual que `teacher_id`).

| Método y ruta | Parámetros o cuerpo | Respuesta | Permiso |
| --- | --- | --- | --- |
| `GET /academics/teaching-assignments/` | `academic_cycle_id`, `section_id`, `subject_id`, `teacher_id` (perfil Teacher), `current` (`true` vigentes, `false` finalizadas), `page`, `page_size` | 200 paginado de `TeachingAssignment`, ordenado por ciclo, grado, sección y curso. 400 si un identificador no existe | `scope.assign` (igual que el historial) |
| `GET /academics/cycles/{id}/assignment-matrix/` | `grade_id?`, `page`, `page_size` (por sección) | 200 paginado de `{section: {public_id, name, grade: {public_id, name}, shift: {public_id, name}}, cells: [{subject: {public_id, name}, assignment: {public_id, teacher: {public_id, name}, starts_on} \| null}]}`. Una fila por sección activa; las columnas son los cursos del plan del ciclo para su grado, por nombre | `scope.assign` |
| `GET /academics/cycles/{id}/teaching-assignments/clone-preview/` | `source_cycle_id` (obligatorio, otro ciclo de la institución) | 200 `{source_cycle: {public_id, name}, target_cycle: {public_id, name}, suggested_starts_on, summary: {total, pending, already_assigned, unmatched}, results: [{source_assignment_id, section, subject, teacher, target_section \| null, status}]}` con `section`/`target_section` como `{public_id, name, grade_name}`. No pagina ni escribe | `scope.assign` |
| `POST /academics/cycles/{id}/teaching-assignments/batch/` | `{starts_on?, items: [{section_id, subject_id, teacher_id}]}` | 201 `{created: [TeachingAssignment], failed: [{index, section_id, subject_id, teacher_id, detail}]}`. Cada elemento se guarda por separado: uno rechazado no cancela los demás. 400 si `items` viene vacío o mal formado | `scope.assign` |

La vista previa empareja secciones por grado, jornada y nombre (los identificadores cambian al
clonar la estructura) y marca cada fila `pending`, `already_assigned` (el destino ya tiene
docente vigente para esa sección y curso) o `unmatched` (no hay sección activa equivalente).
Solo considera asignaciones vigentes del origen.

### Horarios y secciones

- Sesión de clase (`/sections/{id}/class-sessions/`, `/class-sessions/{id}/`) agrega
  `teacher: {public_id, name} | null` (derivado de la asignación vigente, RF-HOR-004) y
  `classroom: {public_id, name} | null`, además de `teacher_id` y `classroom_id`. El listado
  calcula el docente en la misma consulta, sin una consulta por fila.
- Sección (`/sections/`, `/sections/{id}/`) agrega `default_classroom: {public_id, name} | null`
  junto a `default_classroom_id`.

### Búsqueda y orden en catálogos

| Listado | `search` en | `ordering` |
| --- | --- | --- |
| `/academics/campuses/`, `/campuses/{id}/shifts/`, `/subjects/` | nombre, código | `name`, `code` |
| `/academics/classrooms/` | nombre, código | `name`, `code`, `campus`, `capacity` |
| `/academics/levels/` (también con `expand=grades`), `/levels/{id}/grades/` | nombre, código | `sequence`, `name`, `code` |
| `/academics/sections/` | nombre de la sección, nombre y código del grado | `grade`, `name`, `shift`, `capacity` |
| `/academics/curriculum-plans/` | nombre y código del curso y del grado | `subject`, `grade` |

Cada llave admite su versión descendente con `-`. Se mantiene `include_inactive`.

## Evaluación (#631)

Contratos de la entrega de Evaluación de #631 (hallazgos V1–V8 de docs/ux-ui.md 2.11). Los
campos nuevos son **aditivos**. Cambian dos cosas: los endpoints de configuración que solo
pedían sesión ahora exigen permiso (ver la tabla y
[permisos-en-ui.md](../development/permisos-en-ui.md), #643) y la carga CSV responde
`{created, updated}` en vez de `{created}`, donde `created` cuenta solo las notas nuevas. Las
rutas cuelgan de `/api/v1/academics/cycles/{cycle_id}`; `…/units/{u}` abrevia
`…/evaluation-units/{unit_id}`.

### Notas de la unidad y planilla

`GradeSerializer` se publica como componente `UnitGrade` (antes chocaba con el `Grade` de
academics) y agrega, sin cambiar `enrolment`, `subject` ni `evaluation_unit` (pk interno):
`student: {public_id, student_code, full_name}`, `subject_detail: {public_id, name}` (se llama
así porque `subject` ya es el public_id) y `evaluation_unit_id` (public_id). Aplica al listado,
al alta y a la boleta `GET …/enrolments/{id}/grades/`. El listado y la boleta precargan
estudiante, subárea y unidad: el número de consultas no crece con las filas.

| Método y ruta | Parámetros o cuerpo | Respuesta | Permiso |
| --- | --- | --- | --- |
| `GET …/units/{u}/grades/` | `section_id?`, `student_id?`, `subject_id?` (public_id), `page`, `page_size` | 200 paginado de `UnitGrade`, por apellido, nombre y subárea. Un identificador inexistente deja la lista vacía; uno mal formado responde 400 | Sesión; el docente ve solo sus asignaciones (RF-CAL-006, sin cambio) |
| `POST …/units/{u}/grades/` | `{enrolment, subject, value, teacher?}` | 201 `UnitGrade`. Sin `teacher` se toma la persona de la asignación vigente de la sección y la subárea; si no hay, 400 «La sección «…» no tiene docente asignado en «…». …» | `grade.write` sobre sección y subárea |
| `POST …/units/{u}/grades/bulk/` | multipart: `file` (CSV `student_code,value`), `subject`, `section`, `teacher?` | 200 `{created, updated}`; 400 `{errors: [{row, field, message}], created: 0}` | `grade.write` sobre sección y subárea |
| `GET …/units/{u}/sheet/` | `section_id`, `subject_id` (obligatorios) | 200 `{unit: {public_id, name, status, window_open, can_capture, capture_exception_expires_at}, section: {public_id, name}, subject: {public_id, name}, teacher: {public_id, name} \| null, rows: [{enrolment_id, student: {public_id, student_code, full_name}, grade: {public_id, value} \| null}]}`. Una fila por matrícula activa de la sección, por apellido y nombre. `can_capture` aplica la misma regla que el guardado: ventana abierta y unidad abierta, o un permiso excepcional vigente (RF-EVC-004) del docente al que se atribuye la captura, cuyo vencimiento va en `capture_exception_expires_at` (null si no aplica). 404 si la sección no es del ciclo de la unidad | `grade.write` sobre sección y subárea, o `evaluation.configure_units` sobre la institución (solo lectura) |
| `POST …/units/{u}/grades/sheet/` | `{section_id, subject_id, teacher_id?, grades: [{enrolment_id \| student_code, value}]}` (1 a 200) | 200 `{created, updated}`; 400 `{errors: [{index, student_code, field, message}]}` | `grade.write` sobre sección y subárea |

- La planilla responde en **una sola página** con tope de 200 filas (una sección real tiene
  unas 35). Una sección con más responde 400 en vez de cortar: no hay tope silencioso.
- `teacher` del `GET` es la persona docente (`Person.public_id`), la misma que acepta
  `teacher_id`; no es el perfil `Teacher` que usa `teacher_id` en las asignaciones.
- Guardado: la carga CSV y la planilla usan el mismo servicio, `bulk_register_unit_grades`.
  Es **todo o nada**: se validan todas las filas (matrícula activa en la sección, entero de 0 a
  100 sin decimales ni booleanos, sin estudiantes repetidos) y si alguna falla no se escribe
  nada. `index` empieza en 0, en el orden recibido; la carga CSV conserva su `row` (desde 1).
  Las condiciones de lote (sección de otro ciclo, sin docente, ventana cerrada) responden 400
  con el sobre habitual (`error.detail`).
- **Correcciones**: una fila de un estudiante que ya tiene nota la corrige (RF-CAL-005) por la
  misma vía que una corrección individual, `register_unit_grade`: exige ventana de captura
  abierta y unidad abierta, o brecha excepcional vigente, y la bitácora registra
  `evaluation.grade_updated` con el valor anterior y el nuevo. No pide motivo porque RF-CAL-005
  no lo exige; `grade.correct` con motivo sigue siendo solo para resultados congelados.
  `updated` cuenta esas correcciones. El evento resumen `evaluation.grades_bulk_registered`
  lleva `teacher_id`, `created` y `updated`.

### Avance, recuperación y resultados

| Método y ruta | Parámetros o cuerpo | Respuesta | Permiso |
| --- | --- | --- | --- |
| `GET …/units/{u}/capture-progress/` | — | Sin cambio de forma | `evaluation.configure_units` sobre la institución ve todas las filas; con `grade.write` y asignaciones vigentes en el ciclo, solo las propias (y `overall_progress_pct` sobre ellas); si no, 403 |
| `GET …/enrolments/{e}/recovery-eligibility/` | — | Sin cambio de forma | `student.view_basic` sobre el estudiante (mismo criterio que la boleta) |
| `POST …/enrolments/{e}/recovery-grades/` | Sin cambio | Sin cambio | `grade.write` sobre la sección de la matrícula y la subárea; denegación auditada `evaluation.grade_write_denied` |
| `GET …/sections/{s}/recovery-eligibility/` | `page`, `page_size` | 200 paginado de `{enrolment_id, student, eligible, reasons, attendance_percentage, failed_count, failed_limit, recovery_already_used, failed_subjects: [{public_id, name, final_grade}]}` por apellido y nombre | `student.view_basic` con alcance sobre la sección |
| `GET …/enrolments/{e}/frozen-results/` | — | 200 lista sin paginar de `FrozenSubjectResult` (la fila vigente de cada subárea, por nombre de subárea); vacía antes del cierre | Sesión, igual que `…/subjects/{s}/frozen-result/` (hueco seguido en #643) |

- En el listado por sección `failed_subjects` es la **lista** de subáreas reprobadas y
  `failed_count` el conteo; en el endpoint por matrícula `failed_subjects` sigue siendo el
  conteo. Cada fila reutiliza `assess_recovery_eligibility`: no se repiten reglas. Su costo
  es de una evaluación por matrícula de la página (asistencia y nota final de cada subárea
  del plan), acotado por `page_size` (25 por omisión, 100 como máximo).
- El avance de captura lee siempre cuatro consultas (plan, secciones con su conteo de
  matrículas activas, notas agrupadas por sección y subárea, asignaciones vigentes).

### Configuración

| Método y ruta | Cambio | Permiso |
| --- | --- | --- |
| `POST …/evaluation-units/` | Acepta `recovery_starts_on` y `recovery_ends_on` opcionales (las dos o ninguna; con una sola, 400 y no se crea la unidad). Responde `academic_cycle_id` (public_id) además de `academic_cycle` | `evaluation.configure_units` sobre la institución del ciclo (antes solo sesión) |
| `PATCH …/units/{u}/recovery-window/` | — | ídem (antes solo sesión) |
| `GET`/`POST …/units/{u}/capture-exceptions/` | — | ídem para listar y otorgar (antes solo sesión) |
| `PATCH /academics/evaluation-config/` | — | ídem sobre la institución del sistema (antes solo sesión); el `GET` sigue con sesión |
| `PATCH …/evaluation-config/` (del ciclo) | — | ídem sobre la institución del ciclo (antes solo sesión); el `GET` sigue con sesión |

Cierre de unidad y clonado de configuración ya exigían el permiso; no cambian. Las acciones de
configuración registran ahora al actor en la bitácora.

## Asistencia (#631)

Contratos de la entrega de Asistencia de #631 (hallazgos AS1–AS6 de docs/ux-ui.md 2.12). Todo
es **aditivo** salvo un cambio de regla: `GET …/manual-registration-reasons/` lista por omisión
solo los motivos vigentes (antes también los retirados, que el registro manual rechaza de todos
modos). Las rutas cuelgan de `/api/v1/attendance/`. Las bandejas paginan con la paginación
estándar (`page`, `page_size`, 25 por omisión) y aceptan `search` y `ordering` con
`apps.common.listing`: un `ordering` desconocido conserva el orden propio.

### Bandejas de justificaciones y permisos (AS3, AS4)

| Método y ruta | Parámetros | Respuesta | Permiso |
| --- | --- | --- | --- |
| `GET justifications/` | `status` (`pending`, `approved`, `rejected`), `student_id`, `date_from`, `date_to` (sobre `absence_date`), `search` (código o nombre del estudiante), `ordering` (`absence_date`, `submitted_at`, `status`, `student`, con `-`) | 200 paginado de justificaciones. Por omisión, pendientes primero y luego de la más reciente a la más antigua. Un rango de fechas invertido o un `status` desconocido responde 400 | `attendance.justification.resolve` ve las de los estudiantes dentro de su alcance para ese permiso; cada actor ve además las que presentó. Sin `attendance.justification.request` ni `…resolve`, 403 |
| `GET justifications/{id}/` | — | 200 una justificación; 404 si está fuera de lo que el actor puede ver | Igual que el listado |
| `GET permits/` | `status`, `permit_type` (`early_exit`, `late_arrival`), `student_id`, `date_from`, `date_to` (sobre `permit_date`), `search`, `ordering` (`permit_date`, `submitted_at`, `status`, `student`) | 200 paginado de permisos con el mismo orden por omisión | `attendance.permit.resolve` con alcance ve los de su alcance; cada actor, los que solicitó. Sin `attendance.permit.request` ni `…resolve`, 403 |
| `GET permits/{id}/` | — | 200 un permiso; 404 fuera de lo visible | Igual que el listado |

Campos de cada fila. Los `*_id` anteriores no cambian (`submitted_by_id` y `resolved_by_id`
siguen siendo el pk interno, por compatibilidad); lo nuevo se agrega también a las respuestas
de alta y de resolución:

- Justificación: `student: {public_id, student_code, full_name}`, `situation_type_display`,
  `reason_catalog: {public_id, name} | null`, `status_display`, `has_attachment`,
  `submitted_by: {public_id, name}`, `submitted_at`, `resolved_by: {public_id, name} | null`.
- Permiso: `student`, `permit_type_display`, `status_display`, `submitted_by`, `submitted_at`,
  `resolved_by`.
- `submitted_by` y `resolved_by` son la cuenta (`UserAccount.public_id`) con el nombre de su
  persona; no llevan datos de contacto.
- El número de consultas no crece con las filas: estudiante, motivo y cuentas se precargan y
  `has_attachment` sale de una subconsulta.
- Un revisor sin ningún alcance vigente para el permiso de resolución solo ve lo que presentó:
  el permiso no abre por sí solo toda la institución. La resolución (`POST …/resolve/`) no
  cambia de regla.
- Las bandejas no auditan la lectura. El documento adjunto, que puede traer información de
  salud, sigue leyéndose solo por `GET justifications/{id}/attachment/`, que sí la audita
  (RF-JUS-007).

### Estado de la credencial (AS2)

| Método y ruta | Parámetros | Respuesta | Permiso |
| --- | --- | --- | --- |
| `GET credentials/status/` | `student_id` (obligatorio) | 200 `{student_id, status: "active" \| "revoked" \| "none", public_id \| null, issued_at \| null, revoked_at \| null, revocation_reason \| null}` de la credencial más reciente | `attendance.credential.issue` con alcance sobre el estudiante, como la emisión |

- Nunca devuelve `opaque_identifier` ni el QR. Solo la respuesta de emisión los trae, una vez.
- **Reimpresión**: no hay endpoint para volver a generar el QR. Aunque el identificador se
  guarda, exponerlo de nuevo convertiría cualquier lectura en una copia del pase. Para
  reimprimir se revoca la credencial (`POST credentials/revoke/`) y se emite una nueva
  (`POST credentials/`), que trae su QR; la anterior queda como historia (RF-CRE-003/004). El
  contenido imprimible sin QR sigue en `GET credentials/print-content/`.
- `revoked_at` es la última actualización de la credencial revocada: la revocación es su última
  escritura. No hay campo propio ni migración.

### Turno de captura, motivos y cobertura (AS1, AS5)

- `GET capture-batches/current/` ya devolvía `expires_at` en `capture_batch`; sin cambio.
- `GET manual-registration-reasons/` acepta `is_active` (`true` por omisión; `false` lista los
  retirados). El alta de un movimiento `manual` sigue exigiendo `manual_reason_id` de un motivo
  vigente.
- `GET section-closures/coverage-ratio/` no cambia (`attendance.jornada.configure`).

### Nombre del estudiante en las filas (AS6)

- `GET events/`, `GET alerts/`, `GET presence/` y los `events` de
  `GET capture-batches/current/` agregan `student: {public_id, student_code, full_name}`
  junto a `student_id`, que no cambia. Así la interfaz nombra al estudiante de cada fila sin
  descargar el padrón completo. Es aditivo: las respuestas de escritura y los movimientos
  anidados (escaneo, estado del día, cierre de jornada) no cambian.
- Estudiante, persona y demás referencias se precargan: el número de consultas no crece con
  las filas.
- **Notificaciones de inasistencia**: `GET absence-notifications/` sigue siendo solo para la
  cuenta de encargado (al personal le responde 403 y queda auditado). Por D9 de
  [ADR-0011](../decisions/ADR-0011-decisiones-ux-ui.md) el portal de encargados está fuera del
  alcance actual, así que la interfaz del personal no las muestra ni se agrega una vista para
  el personal hasta que exista un requerimiento de portal de encargados (PD-004).

## Inscripciones activas

- `GET /api/v1/enrolments/active/` expone las inscripciones con estado `active` y registro
  vigente; acepta `student_id` para consultar un estudiante concreto.
- La respuesta es paginada y constituye la fuente común de estudiantes habilitados para
  asistencia, evaluación de notas y horarios. No duplica reglas en esos consumidores.

## Historial de movimientos estudiantiles

- `GET /api/v1/enrolments/movements/?student_id={public_id}` devuelve el historial paginado del
  estudiante y separa `section_change`, `transfer_in` y `transfer_out`.
- Cada movimiento conserva `effective_on` como fecha oficial independiente de `created_at`, que
  representa el momento real de registro en el sistema.
- Las matrículas de origen y destino son referencias históricas: cambio de sección exige ambas,
  traslado de ingreso solo destino y traslado de egreso solo origen.
- Los movimientos son inmutables y no admiten borrado físico. RF-MOV-008 agrega una anulación
  separada y no reescribe el asiento existente.
- La consulta requiere sesión autenticada. Este contrato es de solo lectura; cada operación
  académica concreta registra su movimiento desde el servicio de dominio correspondiente.
- La ejecución anticipada de movimientos con fecha futura permanece como decisión pendiente: el
  modelo puede representar la fecha, pero ningún endpoint aplica por adelantado sus efectos.

- `POST /api/v1/enrolments/transfers/in/` crea la matricula de un expediente ya registrado y
  agrega un movimiento `transfer_in` que referencia solo la matricula destino.
- `POST /api/v1/enrolments/{enrolment_id}/transfer-out/` cierra la matricula activa, cambia el
  expediente a `transferred`, revoca acceso y credencial y agrega `transfer_out` con origen.
- Ambos endpoints exigen `enrollment_update` y alcance efectivo. Rechazan fechas futuras hasta
  que RF-MOV-003 defina su ejecucion; no registran datos externos no declarados.
- La UI de ambos traslados, la revisión obligatoria, el selector paginado y la
  cobertura conjunta de M3 se detallan en [Traslados de estudiantes](student-transfers-ui.md).

### Anulacion de movimientos

- `POST /api/v1/enrolments/movements/{movement_id}/annulment/` exige `enrollment_update` y un
  `reason` no vacio. La anulacion es un registro separado y nunca reescribe el movimiento original.
- Retiro restaura matricula, estudiante y la credencial revocada por cierre de permanencia; cambio
  de seccion cancela la matricula destino y reactiva la de origen.
- Solo retiro y cambio de seccion admiten anulacion mientras coincidan con su estado resultante y
  el ciclo permita escrituras. Traslados se rechazan hasta que sus casos de uso conserven estado
  reversible. La doble anulacion tambien se rechaza.
- El historial incluye `annulment` como campo aditivo, nulo para movimientos vigentes.
- El historial agrega `supports_annulment`, booleano de solo lectura que indica
  soporte de anulación para el tipo (retiro/cambio de sección). No acredita
  permiso, alcance ni elegibilidad del estado actual; se revalidan al escribir.
- La captura, revisión y evidencia de la UI están documentadas en
  [Movimientos de matrícula](enrolment-movements-ui.md). Las escrituras conservan
  sus endpoints y payloads existentes.
## Requisitos documentales de matrícula

- `GET /api/v1/enrolments/{enrolment_id}/documents/` lista los requisitos documentales activos
  de una matrícula, con el envoltorio paginado estandar (`count`, `next`, `previous`, `results`).
- `POST` sobre la misma ruta crea o actualiza por `code` el requisito, con `name`, `is_required`
  y `status` (`pending` o `delivered`). El codigo se normaliza a mayusculas.
- `is_required` y `status` son opcionales. Al crear toman `true` y `pending`; al actualizar solo
  se sobrescriben si vienen en el payload, de modo que corregir el `name` no borra el estado de
  entrega ya registrado.
- Registrar un documento sobre un requisito desactivado lo reactiva, para que la escritura quede
  visible en el listado.
- Requiere sesion autenticada y el permiso atomico `enrollment_create` o `enrollment_update`;
  los cambios generan auditoria. La ruta registra estado de entrega, no archivos ni validacion
  del contenido.
- Registrar o modificar documentos de una matricula de un ciclo cerrado devuelve HTTP 400.

## Elegibilidad de emisión oficial

- `GET /api/v1/documents/official-issuance/eligibility/` consulta si una matrícula puede
  continuar con la emisión de un documento oficial.
- Recibe la matrícula en el parámetro de consulta `enrolment_id` y responde `200` con
  `{ "eligible": true, "blocking_document_codes": [] }` cuando no existen requisitos
  obligatorios pendientes.
- Si existen pendientes responde `200` con `eligible` en `false` y los códigos bloqueantes
  en `blocking_document_codes`; la consulta informa, no ejecuta la emisión.
- Un `enrolment_id` que no corresponde a ninguna matrícula devuelve `404`.
- Requiere sesión autenticada y el permiso atómico `document.issue`, validado antes de
  resolver la matrícula; los intentos permitidos, bloqueados y denegados generan auditoría.

## Emisión individual de constancia y certificado (RF-EMI-001)

- `POST /api/v1/documents/official-issuance/individual/` recibe `enrolment_id` y `document_type`
  (`enrolment_certificate` o `study_certificate`) y responde `201` con el PDF adjunto. Folio,
  SHA-256, código de verificación e id de emisión viajan en cabezales `X-Document-*`.
- El PDF no se almacena (RF-DOC-008); se registra un `DocumentIssuance` inmutable. Requiere
  `document.issue`, validado antes de resolver la matrícula, y alcance sobre el estudiante.
- `POST /api/v1/documents/issuances/{public_id}/verify/` compara el SHA-256 de una copia (`204`/`400`).

## Expediente documental del docente (RF-DOC-001)

- `GET` y `POST /api/v1/documents/teachers/{teacher_id}/records/` listan y cargan documentos del
  docente. Lectura: `document.read` y ser el propio docente o tener alcance `module_key=teachers`;
  carga: `document.upload` con alcance `module_key=teachers`.
- Las respuestas de registros documentales agregan `student_id` y `teacher_id` (uno siempre nulo).
- `POST /api/v1/documents/records/{public_id}/download-tokens/` emite el token breve de descarga.

## Filtros de matriculas vigentes

- `GET /api/v1/enrolments/active/` admite `student_id`, `academic_cycle_id`,
  `grade_id` y `section_id` como UUID opcionales. Se combinan por interseccion
  antes de contar y paginar; no cambia la forma de respuesta.
- UUID academico mal formado devuelve 400; un UUID academico valido sin
  coincidencias o una combinacion contradictoria devuelve 200 con lista vacia.
- Se conservan el requisito de sesion y la seleccion de registros activos del
  endpoint existente. Esta entrega no modifica autorizacion ni vigencias.
- M5 usa ese contrato desde la interfaz; es el mismo preparado en PR #638.
  Detalle de dependencias, pruebas e historial en
  [filtros de matriculas](enrolment-filters-ui.md).

## Historial de inscripciones

- `GET /api/v1/enrolments/history/?student_id={public_id}` devuelve todas las inscripciones
  registradas del estudiante, sin filtrar por estado ni por `is_active`.
- La respuesta es paginada y se ordena desde la vigencia más reciente hacia la más antigua.
  Los estados y fechas se conservan para mantener la trazabilidad histórica.

## Cupo contextual al matricular

- La UI de M7 consume `GET /api/v1/enrolments/sections/occupancy/` con
  `academic_cycle_id` y `section_id` para una sola seccion. No cambia el endpoint.
- Se conservan `capacity`, `occupied_seats` y `available_seats`:
  `capacity=0` / `available_seats=null` indica sin limite declarado;
  `available_seats=0` indica ausencia de vacantes.
- Consultar no reserva cupo ni garantiza una inscripcion posterior. La escritura
  mantiene la validacion transaccional y puede rechazar un cupo que se lleno
  despues de consultar. La UI relee al terminar un envio que deja la ventana
  abierta. Detalle y pruebas en [M7](enrolment-capacity-ui.md).

## Altas iniciales masivas

- `GET /api/v1/enrolments/matriculations/candidates/?section_id={uuid}&search=texto&page=1`
  devuelve candidatos paginados con UUID, nombre y código. Aplica permiso/alcance de
  lectura de estudiantes y autorización de matrícula sobre sección destino.
- `POST /api/v1/enrolments/matriculations/bulk/` recibe `section_id`, `effective_on`,
  `student_ids` (1–100 UUID distintos) y `preview` (por defecto `true`). Deriva ciclo,
  grado y jornada de la sección. Exige `enrollment_create` y alcance destino.
- Devuelve 200 con `preview`, `total`, `succeeded`, `failed` y `results` por alumno:
  `student_id`, `status` (`ready`/`created`/`existing`/`error`), `enrolment_id`, `error`.
  Preview valida ocupación acumulada y revierte; confirmar permite errores de dominio
  por fila. Un fallo técnico inesperado revierte toda la solicitud.
- Reintentar reconoce solo la matrícula activa con igual sección y fecha; no modifica
  historia ni repite auditoría de alta. Consultar/revisar no reserva cupo.
- Contratos y evidencia en [altas iniciales por lote](bulk-initial-matriculation-ui.md).

## Alta individual unificada

- `POST /api/v1/enrolments/registrations/` recibe `student_id`, `academic_cycle_id`,
  `grade_id`, `shift_id`, `section_id` (UUID públicos) y `effective_on` (fecha).
- El servicio elige reinscripción si existe matrícula no anulada en otro ciclo;
  en otro caso usa matrícula inicial. No decide por estado manual del expediente.
- Respuesta 201: los campos de matrícula/jornada existentes más `registration_mode`
  (`matriculation` o `reenrolment`). Las rutas explícitas previas se conservan.
- Exige sesión, `enrollment_create` y alcance sobre sección destino. Conserva
  validaciones y auditoría; errores de dominio/validación 400, autorización 403 y
  referencias inexistentes 404. Un fallo no cierra la matrícula de origen.
- Comportamiento, pruebas e integración en [alta unificada](unified-matriculation-ui.md).

## Matricula masiva del ciclo siguiente

- `GET /api/v1/enrolments/re-enrolments/candidates/` consulta el ciclo de origen
  obligatorio con búsqueda, filtros académicos y alcance antes de paginar. Expone
  nombres y códigos mínimos junto al UUID de matrícula para seleccionar el lote.
- `GET /api/v1/enrolments/active/` admite filtros UUID opcionales por
  `academic_cycle_id`, `grade_id` y `section_id`, además de `student_id`.
- El contrato completo de candidatos, la secuencia de revisión/confirmación y
  sus límites están en [Reinscripción por lotes](bulk-reenrolment-ui.md).
- `POST /api/v1/enrolments/re-enrolments/bulk/` recibe `effective_on`, `preview` y una lista
  explicita de pares `source_enrolment_id` / `target_section_id`.
- `preview=true` aplica las mismas validaciones sin persistir. La confirmacion procesa cada
  elemento de forma independiente y devuelve exito o error por estudiante.
- La seccion destino debe pertenecer al ano inmediatamente siguiente y a la misma institucion.
  El endpoint no decide promocion ni repitencia.
- Repetir una confirmacion identica devuelve la matricula existente y no crea duplicados.
- Requiere `enrollment_create` y alcance efectivo sobre cada estudiante. El resumen del lote
  queda auditado.

### Promocion, repitencia y graduacion

- `GET /api/v1/enrolments/{enrolment_id}/promotion/` conserva los campos de RF-RES-006 y agrega
  `progression`, `eligible_grade_id`, `eligible_grade_name` y `result_source`.
- `progression` es `promoted` cuando existe un grado inmediato superior, `repeating` cuando el
  resultado es no promovido y `graduated` cuando se aprueba el ultimo grado configurado.
- La repitencia devuelve el mismo grado como elegible; la graduacion devuelve grado elegible
  nulo. La consulta no crea una reinscripcion.
- Si existe un resultado congelado al cierre del ciclo, ese snapshot es la fuente autoritativa;
  solo ciclos sin snapshot usan el calculo vigente como compatibilidad.
- La lectura exige `enrollment_create` o `enrollment_update` y alcance administrativo vigente
  sobre la seccion de la matricula, tambien para ciclos cerrados. Una sesion por si sola no
  autoriza la consulta: sin permiso o alcance devuelve 403 y audita la denegacion antes de
  determinar el resultado. Ruta y campos JSON no cambian. Vease
  [consulta de promocion](enrolment-promotion-ui.md) para la UI de M4 (#632).

## Administracion de roles

- `GET /api/v1/identity/roles/` devuelve roles y su composicion atomica.
- `POST /api/v1/identity/roles/` crea un rol configurable.
- `PATCH /api/v1/identity/roles/{role_id}/` modifica nombre, descripcion o permisos; el `slug`
  permanece estable despues de crear el rol.
- `POST /api/v1/identity/accounts/{public_id}/role-assignments/` asigna un rol con vigencia;
  `GET` en la misma ruta lista todas las asignaciones de la cuenta, vigentes e historicas.
- `DELETE /api/v1/identity/role-assignments/{assignment_id}/` finaliza la vigencia sin borrar
  historial.
- Todos requieren sesion y `role.assign`, o condicion de superusuario.
- Permisos de entrada y salida usan codigos publicos con punto.
- Cambios de composicion y vigencia generan eventos auditables y aplican en la siguiente
  evaluacion de permisos de cualquier sesion activa.
- Crear una asignacion requiere el objeto `scope` con al menos una dimension soportada:
  institucion, ciclo, grado, seccion, curso, asignacion docente, estudiante (todas por
  `public_id`), modulo (`module_key` de una lista cerrada) o `teaching_assignments: true`.
- Una invocacion directa sin permiso o scope devuelve HTTP 403 y genera auditoria.

## Credencial estudiantil

- `POST /api/v1/attendance/credentials/` emite la credencial de un estudiante y devuelve el
  identificador opaco que codifica el codigo QR. Requiere sesion, el permiso atomico
  `attendance.credential.issue` y alcance sobre el estudiante.
- El codigo QR codifica unicamente ese identificador. Se genera aleatoriamente con `secrets` y no
  se deriva del codigo estudiantil, del numero de identificacion ni de ningun otro dato personal,
  de modo que un lector externo obtiene una cadena sin significado.
- La respuesta de emision es la unica que expone `opaque_identifier`. Ningun listado lo publica:
  una pagina de tokens vigentes es una pagina de pases utilizables.
- Solo un estudiante con inscripcion activa recibe credencial, y solo puede tener una vigente a
  la vez. Un segundo intento devuelve HTTP 400 sin crear nada.
- La emision genera auditoria con el estudiante y la fecha, nunca con el identificador.
- Las credenciales no se borran ni se reescriben: la revocacion y la reposicion conservan las
  anteriores como historia del expediente.

## Resolucion de identificador de credencial

- `POST /api/v1/attendance/credentials/resolve/` resuelve el identificador opaco leido del codigo
  QR y devuelve identidad y ubicacion del estudiante para mostrarlas en el punto de control.
- Es un POST aunque sea una lectura. Un GET dejaria el identificador en la URL, y con ella en el
  log de acceso, la cache del proxy y el historial del navegador de una terminal compartida.
- Requiere sesion y el permiso atomico `attendance.credential.resolve`. El alcance es modular, no
  por estudiante: el operador del punto de control escanea a quien entra, y exigir alcance sobre
  cada estudiante negaria el unico caso para el que existe el endpoint.
- Un identificador desconocido, una credencial revocada o un estudiante sin inscripcion activa
  devuelven HTTP 400 indicando la causa. El mensaje habla de la credencial, nunca de un
  estudiante, de modo que sondear el endpoint no revela quien existe.
- La respuesta no repite el identificador: quien llama ya lo tiene, y devolverlo solo amplia los
  lugares donde puede quedar registrado.
- Cada resolucion exitosa genera auditoria de lectura sensible.
- La captura por escaneo (`POST /api/v1/attendance/scan/`) acepta `credential_identifier` o
  `student_code` en cada elemento, exactamente uno. El primero es la via real; el segundo se
  conserva como alternativa manual. El rechazo de un elemento no aborta el resto del lote.
- Las dos vias exigen inscripcion activa: quien esta retirado del establecimiento no registra
  asistencia, y por cual de las dos puertas entro el escaneo no es un dato de su matricula. Los
  origenes `manual` y `declared` quedan fuera de esa regla a proposito: un operador autorizado
  registrando a mano un movimiento de un estudiante recien retirado puede ser correccion legitima
  de historia.

## Idioma de los mensajes

- El producto es monolingue: `LANGUAGE_CODE` es `es-gt` y `LANGUAGES` declara ese unico idioma.
  `LocaleMiddleware` solo puede activar un idioma declarado, asi que un `Accept-Language: en` no
  cambia los mensajes propios de DRF ni de Django. Sin ese cierre, la garantia dependia de la
  configuracion del navegador de cada usuario.
- Los mensajes de dominio se escriben en espanol. El cliente los muestra literales
  (`frontend/src/shared/api/apiClient.js` toma `error.detail` y lo pone en pantalla), asi que un
  mensaje en ingles en el backend es texto en ingles frente a quien opera el sistema.
- La convencion de nombres tecnicos en ingles no cambia: aplica a identificadores, codigos,
  acciones de auditoria y campos del contrato, no al texto que alguien lee.
- Las etiquetas que se interpolan en un mensaje viajan en espanol y con su articulo
  (`"la jornada"`, `"el estudiante"`), y los mensajes se redactan sin depender del genero del
  sustantivo interpolado.
- `RuntimeError` queda fuera de esta regla: los guardias de inmutabilidad protegen contra un error
  de programacion, salen como HTTP 500 y no son mensajes destinados a leerse.
- `backend/tests/api/test_localization_messages.py` recorre `apps/` y falla si reaparece un mensaje
  visible en ingles, incluidos los mapas de `unique_violation_as`.

## Cambio de seccion

- `POST /api/v1/enrolments/{enrolment_id}/section-change/` exige `enrollment.update`, recibe
  `new_section_id` y `effective_on`, cierra la matricula de origen y crea una nueva en la seccion
  destino. Ambas quedan enlazadas por un movimiento `section_change` con la misma fecha efectiva.
- El cambio no copia ni reasigna calificaciones o asistencias: conserva la matricula anterior y
  sus relaciones historicas. La seccion destino debe ser distinta, pertenecer al mismo ciclo y
  grado y tener cupo disponible.

## Retiro del estudiante

- `POST /api/v1/enrolments/{enrolment_id}/withdrawal/` exige `enrollment.update` y recibe
  `reason` y `effective_on`. La causa es texto obligatorio mientras no exista un catalogo
  institucional aprobado.
- La operacion cambia la matricula y el expediente a `withdrawn`, fija `ends_on` y registra un
  movimiento `withdrawal` inmutable. No desactiva ni elimina el expediente historico.
- Un estudiante retirado deja de aparecer en `GET /api/v1/enrolments/active/` y, por tanto, en
  las listas operativas que consumen esa fuente comun.
- La causa se conserva en el movimiento, pero no se duplica en el contexto de auditoria para
  reducir exposicion de texto potencialmente sensible.
- El cierre emite un evento de dominio sincronico dentro de la misma transaccion. Si existe una
  credencial estudiantil vigente, `attendance-capture` la revoca inmediatamente; si no existe,
  el retiro continua sin crear datos artificiales. Los eventos de asistencia previos no cambian.
- La cuenta vinculada al estudiante no se deshabilita: mientras el expediente no este `active`,
  sus permisos dejan de ser efectivos. Un encargado conserva su cuenta y otros estudiantes
  vigentes, pero pierde el alcance derivado sobre el estudiante retirado.

## Cambios de contrato de cuentas y alcances (ADR-0011)

Cambios incompatibles introducidos para que ningun contrato publico de identidad exponga ni
pida ids internos (docs/ux-ui.md U1, RA1). El unico cliente (frontend del monorepo) se
actualizo en el mismo cambio.

| Endpoint | Antes | Ahora |
| --- | --- | --- |
| `GET /api/v1/auth/me/` | `user.id`, `user.person.id` | `user.public_id`, `user.person.public_id`; agrega `status_display`, `is_superuser`, `permissions` (codigos efectivos con punto), `roles` (`public_id`, `name`, `slug`) y `session_idle_timeout_minutes` |
| `POST /api/v1/auth/login/` bloqueado | `non_field_errors: ["Cuenta temporalmente bloqueada."]` | mensaje con la hora de desbloqueo, `code: ["account_locked"]`, `locked_until: [iso]` |
| `POST /api/v1/identity/accounts/` | `person` (entero); respuesta `id`, `person` | `person_public_id`; respuesta `public_id`, `person_public_id`, `status_display` |
| Rutas `identity/accounts/<int:account_id>/...` | id entero | `identity/accounts/<uuid:public_id>/...` |
| `POST /api/v1/identity/accounts/activate/` | respuesta `id`, `username`, `status`; error de contraseña como texto | respuesta `username`, `status`; error `{"password": [...]}` |
| `POST /api/v1/identity/password-resets/consume/` | error de contraseña sin manejar | error `{"password": [...]}` |
| `ScopeGrantWrite` (`scope` de una asignacion) | ids enteros; `module_key` libre | `public_id`; `module_key` en `identity`, `students`, `teachers`, `enrolments`, `teaching_assignments`; `teaching_assignments: true` |
| `RoleAssignment` (respuesta) | `user` (entero) | `account` (UUID), `role_name`, `status`, `status_display`, `scopes[].dimensions[]` con `public_id` y etiqueta |
| `AccountList` (respuesta) | `id`, `username`, `status`, `is_active`, `person_name` | `public_id`, `email`, `status_display`, `person` (`public_id`, `full_name`, `email`, `is_teacher`), `roles`, `last_login`, `locked_until`, `is_locked` |
| `POST .../disable/` con dependencias | `teaching_assignments[].id` | `teaching_assignments[].public_id` |
| `GET /api/v1/identity/permissions/` | `name` del modelo (ingles) | `name` y `description` en espanol, `group`, `group_label`; incluye `academic_cycle.revert`, `retention_policy.declare`, `account.update`, `person.view`, `person.edit` y `document_type.manage` |
| `PATCH /api/v1/identity/accounts/{public_id}/` | `account.create` | `account.update`; la cuenta propia se rechaza (403). Los roles con `account.create` reciben `account.update` al migrar (`identity/0017`); revisar y retirar donde no corresponda |
| `GET /api/v1/audit/events/` (y `export/`) | campo y filtro `actor_id` | sin `actor_id`; usar `actor_public_id` |
| `sessions[]` en ficha y Mi cuenta | `last_activity_at`, `expires_at`, `is_current` | agrega `public_id`, `started_at`, `ip_address`, `device`; `expires_at` admite nulo |

Endpoints nuevos (todos con sesion salvo los marcados publicos):

- `GET /identity/accounts/list/?search=&status=&role=&locked=&ordering=`: busca tambien por
  correo; filtra por rol vigente (`public_id`) y por bloqueo temporal; ordena por `username`,
  `last_login` o `person`. Cualquiera de `account.create`, `account.activate` o
  `account.disable` sobre `identity`.
- `GET|PATCH /identity/accounts/{public_id}/`: ficha (incluye `sessions`, `recent_activity`,
  `activation_expires_at`) y edicion de `username` y `email` (`account.update`, auditada con
  valor anterior y nuevo; nadie edita su propia cuenta por esta ruta).
- `POST /identity/accounts/{public_id}/reactivate/` y `.../unlock/` con `{reason}`
  (`account.activate`, D8).
- `GET /identity/accounts/candidates/?search=`: personas sin cuenta por nombre, CUI exacto o
  correo; devuelve `cui_hint` (ultimos 4 digitos) y perfiles (`account.create`).
- `GET /identity/accounts/username-suggestion/?person={public_id}` (`account.create`).
- `GET /identity/role-assignments/expiring/?days=15`: por vencer y vencidas en 30 dias.
- `GET /identity/roles/?include_inactive=`, `GET /identity/roles/{public_id}/`,
  `GET .../holders/`, `POST .../deactivate/` y `.../reactivate/` con `{reason}`;
  `slug` opcional al crear (se deriva del nombre); `active_account_count` e `is_active` en la
  respuesta.
- `GET /identity/permissions/{code}/holders/`.
- `GET /identity/scope-options/`: modulos de alcance y la institucion (`public_id`).
- `GET /identity/me/account/`: datos, roles con alcances, sesiones y permisos propios.
- `GET /identity/password-policy/` (**publico**): reglas reales de contrasena.
- `GET /audit/events/` y `GET /audit/events/export/` filtran por `actor_public_id`,
  `actor_username` y `action_prefix`, y la respuesta devuelve `actor_public_id`.
  **Retirado (incompatible):** el campo `actor_id` y el filtro `?actor_id=`.
- `POST /auth/session/keep-alive/` (sesion): solo renueva la actividad de la sesion; responde 204.
- `POST /identity/me/sessions/{public_id}/close/`: la persona cierra una de sus sesiones.
- `POST /identity/accounts/{public_id}/sessions/{session_id}/close/`: administracion cierra una
  sesion concreta (`account.disable`).
- Elementos de `sessions` (ficha y Mi cuenta): `public_id`, `started_at`, `last_activity_at`,
  `expires_at` (nulo si la sesion de Django ya no existe), `ip_address`, `device` (resumen del
  agente de usuario) e `is_current`. Nunca se expone la clave de sesion.
- `POST /identity/accounts/{public_id}/role-assignments/` sobre una cuenta desactivada responde
  400 "Reactive la cuenta antes de asignarle roles."

## Expediente del estudiante con pestanas (#632)

La ruta frontend `/app/alumnos/{public_id}?tab={seccion}` usa lecturas especificas
paginadas y autorizadas: `GET /students/records/{public_id}/`,
`GET /students/records/{public_id}/guardians/`,
`GET /enrolments/students/{student_id}/record/` y
`GET /documents/students/{student_id}/records/` bajo `/api/v1/`.
`GET /attendance/events/` agrega el filtro UUID opcional `student_id`, validado
antes de paginar y combinado con el alcance existente. No cambia campos de
persona ni expone CUI/fecha de nacimiento. Los contratos previos se conservan.
Campos, permisos, paginacion, limites y evidencia en
[expediente con pestanas](student-record-tabs-ui.md).

## Uso de emisión de plantillas (#632, D7)

`DocumentTemplate` y sus versiones agregan `issuance_use`:

| Código | Etiqueta | Regla |
| --- | --- | --- |
| `none` | Ninguna | No selecciona una emisión automática; admite varias plantillas activas. |
| `enrolment_certificate` | Constancia de inscripción | Como máximo una activa por institución. |
| `study_certificate` | Certificado de estudios | Como máximo una activa por institución. |

`kind` conserva el código del catálogo institucional como clasificación; no decide qué plantilla
usa la emisión individual. Se conservan los campos existentes y los endpoints de alta, actualización,
baja lógica, versiones y vista previa. La emisión selecciona la última versión publicada de la
plantilla activa del uso solicitado, independientemente del código de tipo.

`POST /api/v1/documents/templates/` acepta el uso opcional, predeterminado `none`.
`PATCH /api/v1/documents/templates/{public_id}/` lo acepta opcional: omitir conserva el valor.
Un uso vacío, desconocido o `null` devuelve HTTP 400 con error de campo. No se infiere el uso
de plantillas nuevas a partir de tipos legados. Las versiones nuevas guardan también su uso.

Si el uso elegido está ocupado, el alta/actualización debe incluir `replaces_template_id`, UUID
público de la plantilla activa que se confirma reemplazar. Sin confirmación se devuelve HTTP 400.
Si la activa cambió, se rechaza con HTTP 400 y no se reemplaza la nueva ocupante. Un UUID de otra
institución, de otro uso, propio, desactivado o sin ocupante coincidente tampoco autoriza reemplazo.
La interfaz refresca disponibilidad ante error y exige confirmar el nuevo UUID, conservando el
borrador. No se acepta un booleano que autorice reemplazar cualquier ocupante futuro.

Reemplazar desactiva la anterior y crea/publica la nueva versión dentro de una transacción. Si falla
la unicidad del código o la publicación de versión se revierte todo, incluidos los asientos de esa
operación. Se conservan las versiones y emisiones anteriores. Guardar una plantilla desactivada
no la reactiva. Los servicios serializan escrituras mediante bloqueo de institución y la restricción
parcial de PostgreSQL protege la unicidad por uso. La auditoría identifica uso y plantillas afectadas.

`GET /api/v1/documents/templates/issuance-uses/` devuelve un arreglo cerrado, no paginado, de dos
elementos, correspondientes a los usos de emisión distintos de `none`:

```json
[
  {"code": "enrolment_certificate", "label": "Constancia de inscripción", "active_template": null, "uses_fallback": true},
  {"code": "study_certificate", "label": "Certificado de estudios", "active_template": {"public_id": "00000000-0000-0000-0000-000000000001", "name": "Certificado de ejemplo"}, "uses_fallback": false}
]
```

Son datos de ejemplo. `uses_fallback=true` si falta plantilla, versión publicada o contenido de esa
versión; el emisor conserva el texto predeterminado y la pantalla avisa. La consulta es institucional,
requiere sesión y resuelve las últimas versiones en una consulta, sin descargar el catálogo completo.
Las escrituras mantienen `scope_assign` con alcance institucional del catálogo existente.

La migración `documents.0016_template_issuance_use` asigna usos a las activas legadas de tipo
`constancia`/`certificate` y añade metadatos a las versiones según su código histórico. No cambia
contenido, secuencia, fechas, identificadores ni referencias de emisiones anteriores. Antes de
revertir deben resolverse explícitamente las activas del mismo tipo que violarían la restricción
anterior; la reversión no desactiva filas ni borra historia automáticamente.

La vista previa conserva `POST .../{public_id}/preview/` con `{payload: {...}}`. También puede recibir
un borrador sin guardar mediante `content`, `content_format`, `page_size`, `orientation`, márgenes,
`footer_text` y `signature_blocks`. La interfaz aporta valores sintéticos no vacíos para las ocho
etiquetas del catálogo. El sustituidor seguro compartido con emisión admite espacios dentro de
`{{ ... }}` y rechaza marcadores no autorizados. No guarda versiones ni emite documentos.

La respuesta mantiene `content`, `markers` y `marker_count`, y agrega `content_type`,
`pdf_base64` y `content_format`. `content` es cadena para `plain` y objeto JSON para `rich`.
La vista previa y la emisión individual usan el mismo renderizador de ReportLab. Las plantillas y
sus versiones incluyen tamaño, orientación, cuatro márgenes en puntos, pie y hasta dos firmas.
El contrato y las decisiones de compatibilidad están en [ADR-0012](../decisions/ADR-0012-renderizado-de-plantillas.md).

Decisión y evidencia: [ADR-0011, aporte D7](../decisions/ADR-0011-template-issuance-use.md) y
[entrega de plantillas](../development/632-template-issuance-use.md).

### Vista previa nueva y restauración de versiones (D4.2)

- `POST /api/v1/documents/templates/preview/` recibe el mismo borrador que la vista previa de una
  plantilla existente y responde el PDF en base64. Usa la institución de la sesión y no persiste
  plantilla, versión ni emisión.
- `POST /api/v1/documents/templates/{template_id}/versions/{version_id}/restore/` no recibe cuerpo.
  Copia contenido, página, pie y firmas del snapshot indicado y crea una versión nueva. Conserva
  código, clasificación, uso de emisión y estado actuales; nunca reescribe el historial.
- Ambos contratos exigen sesión y conservan la auditoría del módulo de plantillas.
## Desactivación autorizada del perfil docente (#632: T3)

`DELETE /api/v1/teachers/{id}/` mantiene 204 sin cuerpo y ahora exige
`teacher.deactivate` con `module_key="teachers"` vigente (o superusuario).
Sin permiso/alcance devuelve 403 auditado; no alcanza con una sesión abierta.
Este endurecimiento fue aprobado explícitamente por el responsable del proyecto.

Las representaciones de docente agregan `actions: {deactivate: boolean}` de solo
lectura. Se calcula una vez el permiso del módulo por respuesta y se combina con
la actividad del perfil, sin consultas de permisos por cada fila ni auditoría de
escrituras no intentadas. El DELETE vuelve a comprobar la autorización.

La baja y `teachers.teacher.deactivated` son atómicos. Repetir una baja autorizada
no duplica evento ni cambia fecha. No desactiva persona/cuenta, finaliza asignaciones
ni altera documentos. Migración de datos `identity.0018_seed_teacher_deactivate_permission`:
sin concesiones automáticas ni borrado de permisos en reversa. Contratos, despliegue,
evidencia y reversión segura: [T3](teacher-deactivation-ui.md).

## Edición de persona desde comunidad educativa (#632: E1, T1, G1)

- Los formularios de estudiantes, docentes y encargados envían los datos de persona a
  `PATCH /api/v1/people/{public_id}/`. El identificador de persona procede del perfil consultado.
- Además de nombres, apellidos, correo y teléfono, la edición persiste `sex`, `nationality`,
  `address`, `department` y `municipality`, campos ya publicados por `PersonSerializer`.
- El PATCH actualiza únicamente los campos enviados; los omitidos conservan su valor.
  Los campos de texto opcionales admiten `""` para vaciarlos y `sex` conserva sus opciones
  publicadas (`female`, `male`, `not_specified`). La validación de entrada precede a la escritura.
- La siguiente consulta del estudiante, docente o encargado devuelve su persona actualizada.
  CUI y fecha de nacimiento mantienen su condición `write_only` en los serializadores de
  persona y permanecen fuera de estos formularios de edición.
- `update_person` realiza la escritura y su auditoría en una transacción. El evento
  `people.person.updated` conserva actor, recurso y nombres de campos enviados; los valores
  personales quedan fuera del contexto de auditoría. Se conservan los metadatos técnicos de solicitud.
- Se conserva la autorización existente del endpoint de personas. Las pruebas incluyen el rechazo
  de un PATCH anónimo y la lectura del estudiante con permiso y alcance explícitos.
- Evidencia: `backend/tests/api/test_people_api.py`, `backend/tests/unit/test_people_services.py`
  y las pruebas `AlumnosPage.test.jsx`, `DocentesPage.test.jsx` y `GuardiansPage.test.jsx`.


## Puestos de docentes y administrativos (#632, T4)

`GET /api/v1/teachers/positions/` exige sesión y devuelve un arreglo sin paginar
de objetos `{value, label}` derivados de `Teacher.Position.choices`. No acepta
escrituras ni devuelve personas. Ejemplo de un elemento:

```json
{"value": "Docente Titulado", "label": "Docente Titulado"}
```

Alimenta filtros, alta y edición sin duplicar opciones en el frontend; los valores
de `position` y las validaciones de escritura existentes se conservan.
`GET /teachers/` mantiene búsqueda, puesto y actividad antes de paginar, con
`page_size` inicial 25 y máximo 100. Contratos, autorización existente y límites
de exportación en [T2/T4](teacher-server-list-ui.md).

## Desactivacion del estudiante desde el expediente (E7)

GET/HEAD `/students/records/{public_id}/` agrega `actions.deactivate`, calculada
segun actividad y permiso/alcance de edicion, sin auditoria de escritura no intentada.
La lectura mantiene `student.view_basic`. DELETE `/students/{id}/` conserva sesion,
`student.edit_basic`, alcance y 204 sin cuerpo; escritura y auditoria son atomicas.
La UI distingue el DELETE confirmado de errores al recargar: reintenta solo GET.
Ver [contratos y evidencia E7](student-deactivation-ui.md). No borra registros ni
modifica la matricula; D5/E9 queda separado.

## Expediente: vinculación E8 y cambio de estado E9/D5 (#632)

- `POST /api/v1/students/records/{public_id}/guardians/link/` recibe
  `guardian_id` o `person` (excluyentes), más `relationship_label`; responde 201
  con la relación. Crear persona/encargado/vínculo y auditorías es atómico.
- `GET /api/v1/students/records/{public_id}/status/?status=...` devuelve `status`,
  `can_change`, `options`, `has_active_enrolment`, `warnings` y `last_change`.
  El parámetro opcional revisa el destino sin escribir. `last_change` es null o
  `{previous_status, status, actor_label, changed_at}`; no incluye contexto privado.
- `POST` a esa ruta recibe `{status, expected_status}` y devuelve 200 con contexto
  actualizado. Rechaza una confirmación obsoleta, sin sobrescribir cambios.
  Los avisos de matrícula no bloquean ni ejecutan movimientos académicos.
- UUID identifica al estudiante; sesión/CSRF, lectura básica y edición con alcance
  obligatorio en cada operación. 403 sin permiso, 404 fuera de alcance, 400 para
  validación, duplicados o confirmación obsoleta. CUI/nacimiento siguen write-only.
- GET de ficha añade `actions.link_guardian`, según permiso, alcance e interacción
  admitida por el estudiante; conserva `actions.deactivate` y los campos anteriores.
- Los contratos anteriores se conservan; la UI retira status del editor general.
  `students.student.status_changed` conserva anterior/nuevo, actor y fecha.
  No reactiva perfiles desactivados ni altera matrícula o historial.
- Detalle, compatibilidad y pruebas: [E8/E9/D5](student-guardian-link-and-status-ui.md).

## Conversión de persona registrada (#632, D10)

Los tres endpoints de alta de perfiles (`POST /students/`, `POST /teachers/` y
`POST /students/guardians/`) aceptan `person_public_id` UUID con `person`
opcional para completar datos institucionales. La modalidad anterior con
`person` anidada sigue vigente. `person_public_id` se rechaza en actualización.
El servidor conserva el ID de persona, exige el permiso de conversión, valida
que no exista ya ese perfil y confirma persona, perfil y auditoría de forma
atómica. `GET /people/` agrega indicadores booleanos `profiles` y requiere
`person.view` o `person.edit` con alcance `identity`; las escrituras requieren
`person.edit`. La respuesta sigue ocultando CUI y fecha de nacimiento.
