# ADR-0011: Decisiones de negocio del reporte UX/UI (D1–D10) y contratos de identidad

## Estado

Aceptado. Consolida las decisiones D1–D10 de [docs/ux-ui.md](../ux-ui.md), sección 3. D1–D5 las definió el responsable del proyecto; D6–D10 se tomaron con el criterio de mínima sorpresa para la persona usuaria, menor riesgo para la integridad académica y consistencia con el alcance vigente ([functional-scope.md](../requirements/functional-scope.md)).

Este ADR reúne la redacción de los tres responsables del reporte. Cada decisión indica quién la implementa; registrarla aquí **no** marca como implementado ningún requerimiento: el estado real vive en el [catálogo](../requirements/requirements-catalogue.md) y la [matriz de trazabilidad](../requirements/traceability-matrix.md).

## Contexto

El análisis UX/UI (2026-10-17) encontró reglas que el código no cerraba (ciclo escolar, plantillas, expediente, cuentas, portal de encargados, personas) y dos contratos públicos que pedían identificadores internos que ningún cliente puede conocer (alta de cuenta y alcances). Las reglas de negocio cambian el dominio, así que se registran como ADR (AGENTS.md, reglas 1, 3, 10 y 13).

## Decisiones

| # | Decisión | Qué cambia | Hallazgos | Requerimientos | Responsable · estado |
|---|---|---|---|---|---|
| **D1** | Para activar un ciclo **hay que cerrar antes el ciclo activo**. | Backend sin cambios (ya es así). Interfaz: corregir textos y deshabilitar "Activar", con explicación y enlace al ciclo activo, mientras haya otro activo. | C5 | RF-CIC-002, RF-CIC-003 | Persona 2 · pendiente |
| **D2** | **Se puede clonar un ciclo activo** para preparar el siguiente. | `clone_academic_cycle` acepta ciclos `ACTIVE` y `CLOSED` y sigue rechazando borradores con un mensaje claro. Al clonar un activo se copian sus asignaciones vigentes (`ends_on` nulo). "Clonar" se deshabilita en borradores con explicación. | C2 | RF-CIC-007 | Persona 2 · pendiente |
| **D3** | **Existe "volver a borrador"** para un ciclo activado por error. | Servicio y endpoint auditados `POST /academics/cycles/{id}/revert-to-draft/` con motivo obligatorio; acción en la interfaz. Condiciones en D6. | C10 | RF-CIC-008 (nuevo) | Persona 2 · pendiente |
| **D4** | **Las plantillas llevan formato.** | Contenido estructurado con `content_format` (`plain`/`rich`) para no alterar versiones emitidas; configuración de página; un único motor de PDF para vista previa y emisión (la librería se decidirá en un ADR técnico); editor enriquecido con vista previa real. | PL3–PL6, PL10, 2.13.1 | RF-PLA-009 (nuevo), RF-PLA-006 | Persona 3 · pendiente |
| **D5** | **El estado del expediente del estudiante se edita a mano.** | Se mantiene el campo, con acción propia "Cambiar estado", confirmación, aviso (no bloqueo) de inconsistencia con la matrícula y trazabilidad visible desde la auditoría. | E9 | RF-EXP (estado del expediente) | Persona 3 · pendiente |
| **D6** | **Volver a borrador solo antes de que el ciclo tenga actividad.** Solo si el ciclo no tiene matrículas, notas, movimientos de asistencia, unidades de evaluación cerradas ni documentos emitidos. Exige motivo y el permiso nuevo `academic_cycle.revert`. Conserva estructura (ofertas, secciones, plan) y asignaciones docentes. | Si ya hay actividad, la vía es cerrar y, si hace falta, reabrir (RF-CIC-005). El botón aparece deshabilitado y lista qué lo impide. El permiso `academic_cycle.revert` **ya existe** en el catálogo atómico (migración `identity/0014`) y el administrador demo lo recibe. | C10 | RF-CIC-008, RF-CIC-005 | Permiso: Persona 1 · hecho. Servicio y UI: Persona 2 · pendiente |
| **D7** | **Cada plantilla declara para qué emisión se usa** ("Se usa para": Constancia de inscripción, Certificado de estudios o Ninguna), con una sola plantilla activa por uso. El tipo de documento queda solo como clasificación. | Migración: las plantillas activas con tipo `constancia` o `certificate` pasan al uso correspondiente. La emisión deja de buscar por código de tipo. La pantalla avisa cuando un uso usa el texto por defecto. | PL1, PL2, TD1 | RF-PLA-008 (nuevo), RF-PLA-007 | Persona 3 · pendiente |
| **D8** | **Se pueden reactivar cuentas desactivadas y desbloquear cuentas bloqueadas.** Reactivar devuelve la cuenta a `pending` con un código de activación nuevo; la persona define otra contraseña (la anterior queda inutilizable) y las asignaciones revocadas **no** vuelven solas. Desbloquear levanta el bloqueo temporal y reinicia los intentos fallidos. Ambas exigen `account.activate` y motivo, quedan auditadas y nadie puede aplicarlas a su propia cuenta. | `POST /identity/accounts/{public_id}/reactivate/` y `.../unlock/` (cuerpo `{reason}`), acciones en la ficha y el listado de cuentas. | U6 | RF-CTA-008 (nuevo) | Persona 1 · **hecho** |
| **D9** | **El portal para padres de familia queda fuera del alcance actual.** No figura en el catálogo y la granularidad de acceso de encargados sigue abierta ([PD-004](pending-decisions.md)). | El backend conserva `account_kind = "guardian"`; la interfaz no ofrece crear cuentas de encargado. | 2.17.6 | — | Persona 1 · **hecho** (la UI no lo ofrece) |
| **D10** | **Personas es un registro mínimo que se completa al convertirla** ("Convertir en estudiante / docente / encargado", que pide los datos faltantes y reutiliza la persona). Antes de crear se busca por CUI y nombre para evitar duplicados. | Backend: alta de estudiante, docente y encargado desde `person_public_id` además del alta con persona anidada. El alta de cuenta ya busca personas existentes por nombre o CUI (`/identity/accounts/candidates/`). | PE2, U1 | RF-EXP-010 (nuevo), RF-CTA-002 | Conversión: Persona 3 · pendiente. Búsqueda para cuentas: Persona 1 · hecho |

## Decisiones complementarias de identidad (Persona 1)

Tomadas al implementar 2.17 y 1.4, dentro de lo que el reporte deja abierto:

1. **Identificador público de cuenta.** `UserAccount` recibe `public_id` (UUID, migración `identity/0014` con relleno fila por fila). Todas las rutas y respuestas de cuentas, asignaciones y `/auth/me/` usan `public_id`. El `pk` entero queda como llave interna y referencia de bitácora (`target_user_id`, `resource_identifier`), que no se reescribe para no alterar historia auditable (regla 12).
2. **Alcances con `public_id`.** `ScopeGrantWriteSerializer` nombra institución, ciclo, grado, sección, curso, asignación docente y estudiante por `public_id`. `module_key` pasa a ser una lista cerrada (`identity`, `students`, `teachers`, `enrolments`, `teaching_assignments`): un módulo que ninguna vista evalúa no autoriza nada.
3. **Alcance docente automático (RA4).** El alcance del docente ya se deriva dinámicamente de sus asignaciones vigentes (RF-ALC-002). Asignar un rol con `{"teaching_assignments": true}` crea un grant `module_key="teaching_assignments"` que registra la decisión y se muestra como "Sus asignaciones docentes vigentes"; la cobertura real sigue siendo la derivación dinámica, que se ajusta sola cuando cambian las asignaciones. Solo se admite si la persona tiene perfil docente. No se tocó el dominio de asignaciones docentes.
4. **Retiro seguro de roles (RO6).** Un rol se retira (`is_active=False`), nunca se borra. Solo si nadie lo tiene vigente ni programado; los roles del sistema no se retiran. Un rol retirado no se puede asignar ni otorga permisos (`has_atomic_permission` exige `role__is_active`). Se puede volver a ofrecer; las asignaciones no vuelven solas.
5. **Edición de cuenta (U7)** exige `account.create`. La consulta de cuentas (listado y ficha) admite cualquiera de `account.create`, `account.activate` o `account.disable` sobre el módulo `identity`.
6. **Permisos efectivos en `/auth/me/` (1.4)** son solo presentación: replican las condiciones de `has_atomic_permission` (estado de la cuenta, bloqueo, estudiante activo) y no reemplazan ninguna autorización del backend, que sigue negando por defecto.
7. **Visibilidad del menú (2.17.6).** Un módulo se oculta solo si un permiso atómico lo controla en el backend. Excepción documentada: Personas se muestra con `account.create` o `student.edit_basic` y Tipos de documento con `document.issue` o `document.upload`, por ser administración; es presentación, el backend no cambia.
8. **Permiso `retention_policy.declare`.** Ya existía (migración `identity/0010`) pero no estaba en el catálogo atómico, así que no podía asignarse a un rol. Se agrega al catálogo.
9. **Catálogo atómico en español.** Etiqueta, descripción y grupo funcional por permiso en `atomic_permissions.py`; la migración `identity/0014` sincroniza `auth.Permission.name`. Los códigos no cambian.
10. **Inicio de sesión exitoso auditado** (`identity.login.succeeded`) para el historial de accesos de la ficha (U5).

## Cambios de contrato público

Detalle en [api-conventions.md](../architecture/api-conventions.md), sección "Cambios de contrato de cuentas y alcances (ADR-0011)". Resumen de lo incompatible:

- `POST /identity/accounts/`: `person` (entero) → `person_public_id` (UUID). Respuesta: `id`/`person` → `public_id`/`person_public_id`, más `status_display`.
- Rutas `accounts/<int:account_id>/…` → `accounts/<uuid:public_id>/…`.
- `ScopeGrantWrite`: valores enteros → `public_id`; `module_key` cerrado.
- `RoleAssignment`: `user` (entero) → `account` (UUID); agrega `role_name`, `status`, `scopes`.
- `/auth/me/`: `id` y `person.id` → `public_id` y `person.public_id`; agrega `status_display`, `is_superuser`, `permissions`, `roles`, `session_idle_timeout_minutes`.
- Activación (`accounts/activate/`) ya no devuelve `id`.
- Errores de contraseña en activación y restablecimiento: `error.detail` pasa de texto a `{"password": [...]}`.
- Login bloqueado: `non_field_errors` cambia de texto e incluye `code: ["account_locked"]` y `locked_until`.

El único cliente es el frontend de este repositorio, actualizado en el mismo cambio.

## Consecuencias

- Se puede dar acceso al sistema de punta a punta desde la interfaz sin conocer ids internos.
- Las decisiones D1–D7 y D10 quedan registradas como pendientes de implementación por sus responsables; sus requerimientos se dieron de alta o se anotaron sin marcarlos implementados.
- PD-004 sigue abierta (D9).
- Revisar este ADR si aparece un requerimiento de portal de encargados, autoservicio de restablecimiento por correo o un catálogo de módulos de alcance distinto.
