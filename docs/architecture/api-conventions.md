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

- `POST /api/v1/identity/accounts/` provisiona una cuenta pendiente vinculada a una persona.
- La respuesta incluye el codigo de activacion inicial una sola vez y no debe almacenarse en cache.
- `POST /api/v1/identity/accounts/{account_id}/activation-challenges/` revoca el desafio anterior y
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

## Observaciones del estudiante

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
  partir de un ciclo cerrado. Copia ofertas, jornadas referenciadas, secciones y planes; el campo
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
- `POST /api/v1/identity/accounts/{account_id}/role-assignments/` asigna un rol con vigencia.
- `DELETE /api/v1/identity/role-assignments/{assignment_id}/` finaliza la vigencia sin borrar
  historial.
- Todos requieren sesion y `role.assign`, o condicion de superusuario.
- Permisos de entrada y salida usan codigos publicos con punto.
- Cambios de composicion y vigencia generan eventos auditables y aplican en la siguiente
  evaluacion de permisos de cualquier sesion activa.
- Crear una asignacion requiere el objeto `scope` con al menos una dimension soportada:
  institucion, ciclo, grado, seccion, curso, asignacion docente, estudiante o modulo.
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

La vista previa conserva `POST .../{public_id}/preview/` con `{payload: {...}}`. La interfaz aporta
valores sintéticos no vacíos para las ocho etiquetas del catálogo. El sustituidor seguro compartido
con emisión admite espacios dentro de `{{ ... }}` y rechaza marcadores no autorizados. No guarda
versiones ni emite documentos. PDF real y vista previa de borradores sin guardar pertenecen a D4,
PL4/PL6/PL10 y continúan pendientes.

Decisión y evidencia: [ADR-0011, aporte D7](../decisions/ADR-0011-template-issuance-use.md) y
[entrega de plantillas](../development/632-template-issuance-use.md).
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
