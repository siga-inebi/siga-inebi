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
- Estados publicados: `pre_enrolled`, `active`, `inactive`, `withdrawn` y `graduated`.
- Semantica del expediente: `pre_enrolled` conserva al estudiante para matricula o rematricula
  del siguiente ciclo; `active` habilita interacciones ordinarias; `withdrawn` conserva la salida
  por desercion; `graduated` conserva la salida tras completar el pensum; `inactive` representa
  una baja administrativa logica. Matricular o rematricular cambia `pre_enrolled` a `active`.
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

## Historial de inscripciones

- `GET /api/v1/enrolments/history/?student_id={public_id}` devuelve todas las inscripciones
  registradas del estudiante, sin filtrar por estado ni por `is_active`.
- La respuesta es paginada y se ordena desde la vigencia más reciente hacia la más antigua.
  Los estados y fechas se conservan para mantener la trazabilidad histórica.

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
