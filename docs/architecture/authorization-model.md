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
