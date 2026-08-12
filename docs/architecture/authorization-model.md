# Authorization Model

## Distinciones

- Autenticacion: probar identidad de cuenta.
- Autorizacion: decidir si operacion se permite.
- Rol: agrupacion configurable de permisos atomicos.
- Alcance: limite contextual obligatorio del permiso.

## Principios

- Denegacion por defecto.
- Multiples roles por usuario.
- Todo permiso evaluado por operacion.
- Todo permiso requiere alcance valido.
- Cambio de autorizacion debe reflejarse con vigencia controlada.
- Cuenta siempre vinculada a persona institucional.

## Modelo propuesto

```text
UserAccount -> Person
UserAccount -> RoleAssignment -> Role
Role -> PermissionGrant -> Permission
RoleAssignment -> ScopeGrant
```

## Alcances soportados

- Institucion
- Ciclo escolar
- Grado
- Seccion
- Curso o subarea
- Asignacion docente
- Estudiante vinculado
- Modulo
- Vigencia temporal

## Roles iniciales

- System Administrator
- Director
- Academic Coordinator
- Administrative Staff
- Teacher
- Attendance Operator
- Inventory Manager
- Food Programme Manager
- Parent or Guardian
- Read-only Auditor

## Reglas clave

- Rol no equivale a acceso total.
- Union de roles no debe romper restricciones por sensibilidad.
- Lectura historica y escritura historica pueden diferir.
- Alcance docente deriva de asignacion vigente.
- Alcance de encargado deriva de `StudentGuardianRelation` vigente; una relacion terminada no
  concede acceso historico, sin importar una fecha solicitada por el consumidor.
- Cuentas sin alcance efectivo no operan aunque tengan rol asignado.

## Implementacion de alcance contextual

- `UserAccount.has_atomic_permission(...)` verifica solamente el permiso atomico y se reserva para
  operaciones no contextuales, como administrar cuentas.
- `UserAccount.has_scoped_permission(..., scope=...)` delega en `apps.identity.scopes` para no
  separar las comprobaciones de objeto de las de listados. Una asignacion de rol sin alcance
  administrativo o derivado no concede acceso contextual.
- `apps.identity.scopes` concentra la resolucion reutilizable. `authorized_student_queryset(...)`
  devuelve solamente estudiantes autorizados o deniega cuando falta permiso o alcance;
  `can_access_student(...)` reutiliza la misma regla para un objeto.
- Para estudiantes, un grant de institucion se resuelve por la institucion de la seccion de una
  matricula activa; un grant de seccion se resuelve por esa misma matricula activa. Los grants
  directos de estudiante siguen siendo validos.
- Los grants efectivos de todas las asignaciones activas se combinan por union. Un grant de un rol
  no reduce los grants concedidos por otro.
- Las asignaciones docentes vigentes son una fuente de alcance derivado para su docente. Coinciden
  con estudiantes matriculados en la seccion y con comprobaciones directas de seccion, curso o
  asignacion docente; no requieren un `ScopeGrant` duplicado.
- Para `student_view_basic`, el resolvedor tambien une los estudiantes de las relaciones vigentes
  del `Guardian` vinculado a la persona de la cuenta. Ese alcance derivado no requiere
  `ScopeGrant`, pero tampoco concede estudiantes fuera de las relaciones actuales.
- Para estudiantes, el resolvedor tambien une el alcance derivado de `TeachingAssignment`: requiere
  que el ciclo este `active`, que la fecha local este entre `starts_on` y `ends_on` (o sin fin), y
  que el estudiante tenga una matricula activa en la seccion asignada. No se crea un `ScopeGrant`
  para esa derivacion. Este corte solo resuelve operaciones actuales; la lectura historica queda
  para #72 y las escrituras docentes para #73.
- Los alcances administrativos, de encargado y de docente son aditivos. El mismo resolvedor se usa
  para `scope={"student": ...}`, por lo que una comprobacion de objeto no puede omitir un alcance
  derivado que si aparece en un listado.
- `GET /api/v1/students/` y los detalles de estudiante usan el resolvedor central. Las lecturas
  requieren `student_view_basic`; las modificaciones y bajas requieren `student_edit_basic`.
  Las vistas no contienen filtros de alcance ad hoc.
- Las relaciones `StudentGuardianRelation` reutilizan el mismo resolvedor: listados y detalle se
  filtran por los estudiantes autorizados con `student_view_basic`; crear, marcar principal y
  terminar requieren `student_edit_basic` sobre el estudiante afectado. Las asignaciones docentes
  requieren `scope_assign` y un `ScopeGrant` institucional que coincida con la institucion operada.

Las pruebas en `backend/tests/permissions/test_identity_permissions.py` y
`backend/tests/api/test_students_api.py` cubren permiso sin alcance, herencia institucion a
  seccion, filtro de listado por seccion usando matriculas activas y la union positiva de dos roles.
  Tambien cubren alcance docente sin grant, reasignacion y union docente-administrativa.

## Relaciones estudiante-encargado

- `StudentGuardianRelation` conserva el historial con `ends_at`; no se elimina fisicamente.
- La base de datos permite a lo sumo una relacion principal sin `ends_at` por estudiante. Los
  servicios transaccionales garantizan exactamente una: el primer vinculo vigente es principal,
  `change_primary_student_guardian_relation(...)` reemplaza la principal, y
  `end_student_guardian_relation(...)` exige una relacion vigente de reemplazo al terminarla.
- `POST /api/v1/students/guardian-relations/` crea el vinculo y calcula su principalidad. La ruta
  de detalle es solo de lectura; `POST .../{id}/make-primary/` cambia la principal y
  `POST .../{id}/end/` termina la relacion con `replacement_relation` cuando corresponde.

## Permisos atomicos iniciales

- `auth.login`
- `auth.logout`
- `account.create`
- `account.activate`
- `account.disable`
- `role.assign`
- `scope.assign`
- `student.view_basic`
- `student.view_sensitive`
- `student.edit_basic`
- `enrollment.create`
- `enrollment.update`
- `attendance.scan`
- `attendance.record_entry`
- `attendance.record_exit`
- `attendance.declared_close`
- `attendance.record_manual`
- `attendance.justification.request`
- `attendance.justification.resolve`
- `grade.write`
- `grade.correct`
- `document.upload`
- `document.read`
- `document.download`
- `document.issue`
- `audit.read`

## Politicas sensibles

- Salud y documentos privados requieren permiso especifico mas alcance valido.
- Descargas deben ser trazables.
- Intentos denegados relevantes deben quedar auditados.

## Contratos internos de roles

- `create_role(...)` crea roles configurables compuestos exclusivamente por permisos del catalogo
  atomico.
- `update_role(...)` modifica la composicion sin recrear rol, asignaciones ni cuentas; registra
  estado anterior y posterior.
- `assign_role(...)` agrega roles adicionales con vigencia y prohibe autoasignacion.
- `revoke_role_assignment(...)` termina vigencia sin eliminacion fisica y prohibe
  autorevocacion.
- Operaciones administrativas requieren `role.assign` o condicion de superusuario.
- Evaluacion consulta asignaciones y composicion vigentes en cada operacion; no conserva permisos
  en sesion.

## Contratos internos de cuentas

- `create_account(actor, person, username, email="")` provisiona una cuenta exclusivamente por
  accion administrativa.
- La operacion requiere un superusuario o el permiso atomico logico `account.create`, representado
  por el codename Django `account_create`.
- La persona institucional es obligatoria y solo puede estar vinculada a una cuenta.
- La cuenta se crea con `status=pending`, `is_active=False` y sin contrasena utilizable.
- Tanto la creacion exitosa como el intento sin autorizacion generan un evento de auditoria.
- `provision_account_with_activation(...)` combina la provision con la emision inicial del desafio.
- El endpoint administrativo `POST /api/v1/identity/accounts/` devuelve el codigo inicial una sola
  vez y exige `account.create`.
- Los codigos son numericos de ocho digitos, duran quince minutos y permiten tres intentos.
- La base de datos conserva un HMAC del codigo; el valor original no se registra ni puede
  recuperarse.
- `POST /api/v1/identity/accounts/{account_id}/activation-challenges/` permite reemitir un codigo
  con `account.activate`; la reemision revoca inmediatamente cualquier desafio anterior vigente.
- Las respuestas que contienen codigos usan `Cache-Control: no-store`.
- `activate_account(username, activation_code, password)` valida el codigo con comparacion de
  tiempo constante dentro de una transaccion y aplica los validadores de contrasena de Django.
- `POST /api/v1/identity/accounts/activate/` es publico porque la cuenta aun no puede iniciar
  sesion; exige los tres valores del contrato confirmado y no revela si el usuario existe.
- Cada codigo admite tres intentos fallidos. Un codigo vencido, revocado, agotado o consumido no
  activa la cuenta.
- El canje exitoso registra `used_at`, invalida el desafio, define la contrasena y cambia la cuenta
  de `pending` e inactiva a `active` y activa en una sola transaccion.
- Exitos y rechazos de activacion generan eventos auditables sin guardar codigo ni contrasena.
- `disable_account(actor, user)` desactiva una cuenta institucional sin eliminarla.
- La operacion requiere un superusuario o el permiso atomico logico `account.disable`,
  representado por el codename Django existente `account_disable`.
- La desactivacion actualiza `status=disabled` e `is_active=False` dentro de una transaccion.
- Tanto la operacion exitosa como el intento denegado generan un evento de auditoria.
- Este contrato es interno del dominio; no agrega ni modifica endpoints de la API publica.

## Bloqueo temporal de autenticacion

- Cinco intentos fallidos consecutivos bloquean temporalmente la cuenta durante diez minutos.
- El umbral y la duracion se configuran con `LOGIN_MAX_FAILED_ATTEMPTS` y
  `LOGIN_LOCKOUT_MINUTES`.
- El bloqueo temporal usa `failed_login_attempts` y `locked_until`; no cambia el estado
  administrativo de la cuenta.
- Un inicio de sesion correcto o el primer acceso correcto posterior al vencimiento reinicia el
  contador y elimina el vencimiento.
- Cada intento rechazado genera un evento auditable sin almacenar la contrasena ni el identificador
  ingresado para cuentas inexistentes.
- El contrato de respuesta del endpoint existente se conserva: credenciales invalidas y cuenta
  temporalmente bloqueada continuan devolviendo validacion HTTP 400.
