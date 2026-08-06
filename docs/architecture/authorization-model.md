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
- Alcance de encargado deriva de vinculo con estudiante y su vigencia.
- Cuentas sin alcance efectivo no operan aunque tengan rol asignado.

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

## Contratos internos de cuentas

- `create_account(actor, person, username, email="")` provisiona una cuenta exclusivamente por
  accion administrativa.
- La operacion requiere un superusuario o el permiso atomico logico `account.create`, representado
  por el codename Django `account_create`.
- La persona institucional es obligatoria y solo puede estar vinculada a una cuenta.
- La cuenta se crea con `status=pending`, `is_active=False` y sin contrasena utilizable.
- La activacion mediante codigo de un solo uso pertenece a un corte posterior de `RF-CTA-003`.
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
- La validacion del codigo y la activacion final pertenecen al siguiente corte de `RF-CTA-003`.
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
