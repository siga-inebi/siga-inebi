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

- `POST /api/v1/students/guardian-relations/` crea una asociacion; `is_primary` es calculado por
  el servicio y no se acepta en el payload.
- `POST /api/v1/students/guardian-relations/{id}/make-primary/` designa una relacion vigente como
  principal.
- `POST /api/v1/students/guardian-relations/{id}/end/` conserva el registro y termina el acceso.
  Debe incluir `replacement_relation` al terminar la relacion principal.

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
