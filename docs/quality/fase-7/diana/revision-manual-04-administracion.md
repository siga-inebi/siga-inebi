# Revisión del manual 04 — administración

Fecha: 12 de octubre de 2026, America/Guatemala.
Documento revisado: [`docs/manuals/04-administration-manual.md`](../../../manuals/04-administration-manual.md)
de Santiago, tal como está en `develop` (`5ed5fd24d02f494053c53dbbbafe50a8412534e5`).
Revisora: Diana. Revisión asistida por Claude Code.

## Resultado

**El manual es correcto en su mayor parte y cumple la estructura pedida.** Se contrastó cada
permiso, ruta, evento de auditoría y valor numérico contra el código. Hay **cinco puntos por
corregir** antes de darlo por final: en cuatro el manual afirma algo que la versión actual no
hace, y en uno el permiso indicado no es el que exige el código.

Método: lectura del manual contra sus
[instrucciones](../../../manuals/04-administration-manual-instructions.md) y contra
`backend/apps/identity`, `backend/apps/academics`, `backend/apps/audit`, `backend/apps/documents`
y `frontend/src`. No se ejecutó la aplicación para esta revisión.

## Por corregir

| # | Sección | Qué dice el manual | Qué hace el código | Corrección sugerida |
| --- | --- | --- | --- | --- |
| 1 | 6.3 Declarar alcances | Permiso requerido: `scope.assign`. Lo presenta como operación propia. | No hay endpoint de alcances. El alcance es el campo obligatorio `scope` de `POST identity/accounts/{id}/role-assignments/`, que exige `role.assign` con alcance de módulo `identity`. `scope.assign` solo se usa para escribir el catálogo académico. | Indicar que el alcance se declara al asignar el rol, con `role.assign`, y que hoy no se puede agregar ni cambiar un alcance sin crear otra asignación. |
| 2 | 9 Auditoría | Permiso requerido: `audit.read` «con alcance válido»; resultado: «eventos dentro del alcance». | `audit/api/views.py` solo comprueba `has_atomic_permission("audit_read")`. Quien tiene el permiso ve toda la bitácora. | Quitar la referencia al alcance o declararla como brecha conocida. |
| 3 | 2 y 3 | «El frontend ayuda a ocultar opciones no disponibles» y «módulos visibles para su autorización». | `frontend/src/auth/permissions.js` devuelve `true` siempre: el menú muestra todos los módulos a cualquier cuenta con sesión. El backend responde 403. | Decir que el menú muestra todos los módulos y que una opción visible no implica autorización. |
| 4 | 8 Documentos | Las descargas sensibles «deben usar el mecanismo temporal entregado por el sistema». | El servicio que emite el token de descarga existe, pero ninguna vista lo expone: la API solo valida el token. La descarga no se puede completar desde la aplicación. | Declarar la descarga con token como no disponible en esta versión. |
| 5 | 4 y 7.2 Ciclos | La tabla de disponibilidad no menciona cierre ni reapertura; 7.2 pide usar «los contratos autorizados». | `cycles/{id}/close/` y `cycles/{id}/reopen/` existen en la API; el frontend no los invoca. | Agregar a la tabla de la sección 4 que cerrar y reabrir un ciclo solo está disponible por API. |

Los puntos 2, 3 y 4 coinciden con brechas que el manual técnico ya declara; aquí importan
porque las instrucciones piden no prometer operaciones que la versión entregada no ofrece.

## Verificado sin observaciones

| Sección | Qué se comprobó |
| --- | --- |
| 5.1 a 5.5 | Listar, restablecer, cerrar sesiones y desactivar exigen `account.disable` con alcance de módulo `identity`. Las cuatro acciones existen en **Seguridad > Cuentas**. |
| 5.2 | `POST identity/accounts/` y la reemisión en `accounts/{id}/activation-challenges/` existen. Vigencia de 15 minutos y 3 intentos, ambos configurables por entorno. |
| 5.3 | Consumir el restablecimiento cierra las sesiones previas de la cuenta. |
| 5 y 6 | Los eventos citados existen con ese nombre: `identity.account.created`, `identity.activation_challenge.issued`, `identity.password_reset.issued`, `identity.password_reset.consumed`, `identity.session.closed_administratively`, `identity.account.disabled`, `identity.role.created`, `identity.role.updated`, `identity.role_assignment.created` e `identity.role_assignment.revoked`. |
| 6.1 y 6.2 | Roles y asignaciones exigen `role.assign`. Las rutas `identity/roles/`, `identity/permissions/` y `accounts/{id}/role-assignments/` existen. |
| 7.1 | Las escrituras del catálogo académico exigen `scope.assign` con alcance de institución. |
| 7.2 | `academic_cycle.reopen` existe en el catálogo de permisos. Crear, clonar y activar tienen pantalla. |
| 7.4 | La pantalla de asignaciones docentes ofrece asignación por lote, clonación a ciclo nuevo y reasignación. |
| 3 | **Cerrar todas las sesiones** existe en el menú de usuario. |
| 10 | El bloqueo por intentos fallidos dura 10 minutos por defecto. |

## Sugerencias menores

- **10, cuenta bloqueada.** Los 10 minutos son el valor por defecto de `LOGIN_LOCKOUT_MINUTES`;
  conviene decir que es configurable por entorno.
- **Criterio de cierre.** Las instrucciones piden que cada procedimiento declare permiso,
  precondición, resultado esperado y evento de auditoría. Las secciones 7.3 y 8 no los
  declaran por procedimiento.
- **6.3.** «Auditoría: conserve actor, objeto, alcance, vigencia y resultado» no nombra un
  evento. El alcance queda registrado dentro de `identity.role_assignment.created`.
- **Rol de encargado.** Qué permisos lleva ese rol sigue abierto (PD-004 y PD-005), como
  mostró la [revisión cruzada de EJ-D1-041](revision-cruzada-ej-d1-041.md). El manual podría
  advertir que no debe incluir `student_view_sensitive` hasta que se decida.

## Límites

Revisión documental contra el código de `develop`. No sustituye la validación del manual con
usuarios administrativos ni su repetición sobre el commit candidato final.
