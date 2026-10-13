# Diccionario de datos final de SIGA-INEBI

Estado: borrador de Fase 7, 2026-10-12. Responsable: Diana; revisión de Santiago pendiente.
Esquema descrito: rama `develop`, commit `5ed5fd24d02f494053c53dbbbafe50a8412534e5`, sobre PostgreSQL 16.14.
Debe regenerarse y revisarse sobre el commit candidato final antes de cerrar la entrega.
Sigue las [instrucciones del diccionario](05-final-data-dictionary-instructions.md).

## 1. Alcance y fuente

Este documento describe cada tabla y cada columna del esquema PostgreSQL que producen las
migraciones de Django. La fuente de verdad son los modelos y las migraciones; el
[modelo de datos inicial](../architecture/initial-data-model.md) es un documento de diseño y no
se usó para conservar atributos que el código ya no tiene.

| Dato | Valor |
| --- | --- |
| Tablas | 79 (72 del sistema y 7 de la plataforma Django) |
| Columnas | 765 |
| Migraciones aplicadas | 112 (94 de las apps del sistema) |
| Claves foráneas | 135 |
| Restricciones únicas | 130, más 10 únicas parciales |
| Restricciones de verificación | 54 |
| Restricciones de exclusión | 3 |

Cómo se obtuvo: se aplicaron todas las migraciones sobre una base PostgreSQL vacía y efímera,
se leyeron los catálogos del sistema (`pg_attribute`, `pg_constraint`, `pg_index`) y se
cruzaron con el registro de modelos de Django. `makemigrations --check` no reportó cambios
pendientes. No se leyó ninguna fila de datos: el documento no contiene valores reales, sumas
de verificación ni secretos.

## 2. Cómo leer las tablas

| Columna del diccionario | Significado |
| --- | --- |
| Campo | Nombre físico de la columna. |
| Tipo | Tipo PostgreSQL con su tamaño, precisión o escala. |
| Nulo | «Sí» si la columna admite `NULL`. |
| Defecto | Valor que se asigna si no se indica otro. Lo aplica el ORM de Django: en la base solo las claves `id` tienen valor autogenerado. |
| Clave | `PK` clave primaria; `FK → tabla.campo` clave foránea con su regla de borrado; `UQ` única. |
| Descripción y regla | Significado funcional y regla de validación de la columna. |
| Clasif. | Clasificación del dato según [clasificación de datos](../architecture/data-classification.md). |

Las restricciones que abarcan varias columnas, las de verificación, las de exclusión y los
índices únicos parciales se listan bajo cada tabla, en «Restricciones e índices».

| Clasificación | Qué significa | Controles mínimos |
| --- | --- | --- |
| Público | Puede exponerse sin autenticación controlada. | Límite de tasa y revelación mínima. |
| Interno | Uso institucional general: catálogos y estructura académica. | Autenticación y autorización básica. |
| Restringido | Uso limitado por rol y alcance: matrícula, notas, asistencia, contactos. | Autorización con alcance y auditoría de escritura. |
| Sensible especial | Alta sensibilidad: salud, documentos privados, secretos de acceso. | Autorización reforzada, auditoría de lectura y escritura, minimización. |

Ninguna tabla almacena hoy datos clasificados como públicos. La verificación pública de
documentos expone solo lo mínimo de `documents_documentverificationcode`, con límite de tasa.

## 3. Reglas transversales

- **Nombres.** Las tablas usan el nombre por defecto de Django, `<app>_<modelo>`. Hay dos
  modelos `Grade` con tablas distintas: `academics_grade` (grado escolar) y `evaluation_grade`
  (nota).
- **Columnas comunes.** Casi todas las tablas del sistema incluyen `id`, `public_id`,
  `created_at`, `updated_at` e `is_active`. `identity_useraccount` no hereda esa base porque
  extiende el usuario de Django, y las tablas de relación muchos a muchos solo tienen `id` y
  sus dos claves foráneas.
- **Textos opcionales.** Un texto opcional se guarda como cadena vacía, no como `NULL`; por
  eso varias columnas descritas como opcionales no admiten nulos.
- **Identificadores.** `id` es interno; la API expone `public_id` (UUID). Excepción conocida:
  los endpoints de estudiantes direccionan por `id` y sus subrecursos por `public_id`.
- **Historia antes que borrado.** Los registros se desactivan, se revocan, se versionan o
  cambian de estado; no se eliminan físicamente (ADR-0006). La regla concreta figura en cada tabla.
- **Reglas de borrado de las claves foráneas.** `PROTECT`, `CASCADE` y `SET_NULL` las aplica
  el ORM de Django. En PostgreSQL las claves foráneas se crean sin acción de borrado y como
  diferibles, de modo que un borrado por SQL directo que deje huérfanos es rechazado.
- **Índices.** Django crea un índice por cada clave foránea y por cada restricción única. Solo
  se documentan aparte los índices con significado de negocio.
- **Tiempo.** Los instantes se guardan como `timestamp with time zone`. Las fechas lectivas y
  de vigencia son `date` en la zona del establecimiento (`America/Guatemala`).
- **Archivos fuera de la base.** PostgreSQL guarda solo metadatos y una ruta. El contenido de
  fotografías, documentos y adjuntos vive en el almacenamiento de archivos (sección 18).
- **Retención.** No hay plazos de retención ni purga implementados: la política por tipo de
  dato sigue abierta (PD-003). Ninguna regla de este documento autoriza borrar historia.

## 4. Resumen por dominio

| # | Dominio | Tablas | Columnas | Contenido |
| --- | --- | --- | --- | --- |
| 5 | Personas | 1 | 17 | Identidad institucional de cada persona. |
| 6 | Identidad y acceso | 9 | 80 | Cuentas, roles, permisos, alcances y desafíos de acceso. |
| 7 | Expediente estudiantil | 6 | 53 | Estudiantes, encargados, vínculos, contactos, salud y observaciones. |
| 8 | Docentes | 1 | 11 | Docente como actor institucional. |
| 9 | Estructura académica | 18 | 173 | Institución, sedes, jornadas, niveles, grados, secciones, cursos, horarios, asignaciones y resultados congelados. |
| 10 | Matrícula | 4 | 41 | Matrículas, requisitos documentales y movimientos del estudiante. |
| 11 | Asistencia y credencial | 14 | 157 | Credencial QR, captura de eventos, cierres, justificaciones y permisos. |
| 12 | Evaluación | 6 | 57 | Unidades, notas, recuperación y configuración. |
| 13 | Documentos | 9 | 97 | Tipos, plantillas, expediente documental, folios, verificación y descarga. |
| 14 | Alertas | 2 | 25 | Umbrales y alertas institucionales de inasistencia. |
| 15 | Auditoría | 1 | 12 | Bitácora de operaciones, lecturas sensibles y denegaciones. |
| 16 | Operación | 1 | 15 | Registro de ejecución de tareas programadas. |
| 17 | Plataforma Django | 7 | 27 | Tablas del framework: permisos, tipos de contenido, sesiones y migraciones. |

## 5. Personas

Identidad institucional de cada persona.

### `people_person` — Persona institucional

Datos personales de cada persona vinculada al instituto. Es el ancla de identidad: la cuenta, el estudiante, el encargado y el docente se relacionan 1:1 con ella, de modo que una misma persona puede cumplir varios papeles sin duplicar datos.

- **Clasificación:** Restringido.
- **Historia:** Baja lógica con `is_active`; no se elimina físicamente.
- **La referencian:** `academics_teachingassignment`, `evaluation_captureexceptiongrant`, `identity_useraccount`, `students_guardian`, `students_student`, `teachers_teacher`.

| Campo | Tipo | Nulo | Defecto | Clave | Descripción y regla | Clasif. |
| --- | --- | --- | --- | --- | --- | --- |
| `id` | `bigint` | No | Autogenerado | PK | Identificador interno secuencial. Clave primaria. | Restringido |
| `public_id` | `uuid` | No | UUID aleatorio | UQ | Identificador público opaco que expone la API. Único, no editable. | Restringido |
| `created_at` | `timestamp with time zone` | No | Al crear | — | Fecha y hora de creación del registro. | Restringido |
| `updated_at` | `timestamp with time zone` | No | Al guardar | — | Fecha y hora de la última modificación. | Restringido |
| `is_active` | `boolean` | No | `true` | — | Vigencia del registro; `false` equivale a baja lógica. | Restringido |
| `first_name` | `character varying(150)` | No | — | — | Nombres de la persona. | Restringido |
| `last_name` | `character varying(150)` | No | — | — | Apellidos de la persona. | Restringido |
| `email` | `character varying(254)` | No | — | — | Correo electrónico de contacto. Opcional. | Restringido |
| `phone_number` | `character varying(30)` | No | — | — | Teléfono de contacto. Opcional. | Restringido |
| `institutional_identifier` | `character varying(100)` | No | — | — | Identificador institucional de la persona. Opcional. | Restringido |
| `birth_date` | `date` | Sí | — | — | Fecha de nacimiento. Dato de menores sujeto a minimización. | Sensible especial |
| `cui` | `character varying(13)` | Sí | — | UQ | Código Único de Identificación (CUI). Opcional. | Sensible especial |
| `sex` | `character varying(20)` | No | `not_specified` | — | Sexo registrado. Valores: `female`, `male`, `not_specified`. | Restringido |
| `nationality` | `character varying(100)` | No | — | — | Nacionalidad. Opcional. | Restringido |
| `address` | `character varying(255)` | No | — | — | Dirección de residencia. Opcional. | Restringido |
| `department` | `character varying(100)` | No | — | — | Departamento de residencia. Opcional. | Restringido |
| `municipality` | `character varying(100)` | No | — | — | Municipio de residencia. Opcional. | Restringido |

## 6. Identidad y acceso

Cuentas, roles, permisos, alcances y desafíos de acceso.

### `identity_activationchallenge` — Desafío de activación

Código de un solo uso para activar una cuenta nueva. Solo se guarda su resumen criptográfico.

- **Clasificación:** Sensible especial.
- **Historia:** No se elimina: se marca usado o revocado.

| Campo | Tipo | Nulo | Defecto | Clave | Descripción y regla | Clasif. |
| --- | --- | --- | --- | --- | --- | --- |
| `id` | `bigint` | No | Autogenerado | PK | Identificador interno secuencial. Clave primaria. | Sensible especial |
| `public_id` | `uuid` | No | UUID aleatorio | UQ | Identificador público opaco que expone la API. Único, no editable. | Sensible especial |
| `created_at` | `timestamp with time zone` | No | Al crear | — | Fecha y hora de creación del registro. | Sensible especial |
| `updated_at` | `timestamp with time zone` | No | Al guardar | — | Fecha y hora de la última modificación. | Sensible especial |
| `is_active` | `boolean` | No | `true` | — | Vigencia del registro; `false` equivale a baja lógica. | Sensible especial |
| `token_digest` | `character varying(64)` | No | — | — | Resumen HMAC del secreto. El secreto en claro nunca se guarda. | Sensible especial |
| `expires_at` | `timestamp with time zone` | No | — | — | Momento en que deja de ser válido. | Sensible especial |
| `failed_attempts` | `integer` | No | `0` | — | Intentos fallidos de activación. Al llegar al máximo el desafío deja de ser válido. No negativo. | Sensible especial |
| `used_at` | `timestamp with time zone` | Sí | — | — | Momento en que se consumió; vacío si no se ha usado. | Sensible especial |
| `revoked_at` | `timestamp with time zone` | Sí | — | — | Momento en que se revocó; vacío si no se revocó. | Sensible especial |
| `account_id` | `bigint` | No | — | FK → `identity_useraccount.id` (PROTECT) | Cuenta a la que pertenece el desafío. | Sensible especial |

### `identity_passwordresetchallenge` — Desafío de restablecimiento

Secreto de un solo uso y vigencia breve para restablecer una contraseña. Solo se guarda su resumen criptográfico.

- **Clasificación:** Sensible especial.
- **Historia:** No se elimina: se marca usado o revocado.

| Campo | Tipo | Nulo | Defecto | Clave | Descripción y regla | Clasif. |
| --- | --- | --- | --- | --- | --- | --- |
| `id` | `bigint` | No | Autogenerado | PK | Identificador interno secuencial. Clave primaria. | Sensible especial |
| `public_id` | `uuid` | No | UUID aleatorio | UQ | Identificador público opaco que expone la API. Único, no editable. | Sensible especial |
| `created_at` | `timestamp with time zone` | No | Al crear | — | Fecha y hora de creación del registro. | Sensible especial |
| `updated_at` | `timestamp with time zone` | No | Al guardar | — | Fecha y hora de la última modificación. | Sensible especial |
| `is_active` | `boolean` | No | `true` | — | Vigencia del registro; `false` equivale a baja lógica. | Sensible especial |
| `token_digest` | `character varying(64)` | No | — | — | Resumen HMAC del secreto. El secreto en claro nunca se guarda. | Sensible especial |
| `expires_at` | `timestamp with time zone` | No | — | — | Momento en que deja de ser válido. | Sensible especial |
| `used_at` | `timestamp with time zone` | Sí | — | — | Momento en que se consumió; vacío si no se ha usado. | Sensible especial |
| `revoked_at` | `timestamp with time zone` | Sí | — | — | Momento en que se revocó; vacío si no se revocó. | Sensible especial |
| `account_id` | `bigint` | No | — | FK → `identity_useraccount.id` (PROTECT) | Cuenta a la que pertenece el desafío. | Sensible especial |

### `identity_role` — Rol

Conjunto configurable de permisos atómicos que se asigna a las cuentas. Define además el tiempo de inactividad permitido para la sesión.

- **Clasificación:** Interno.
- **Historia:** Baja lógica con `is_active`; no se elimina físicamente.
- **La referencian:** `identity_role_permissions`, `identity_roleassignment`.

| Campo | Tipo | Nulo | Defecto | Clave | Descripción y regla | Clasif. |
| --- | --- | --- | --- | --- | --- | --- |
| `id` | `bigint` | No | Autogenerado | PK | Identificador interno secuencial. Clave primaria. | Interno |
| `public_id` | `uuid` | No | UUID aleatorio | UQ | Identificador público opaco que expone la API. Único, no editable. | Interno |
| `created_at` | `timestamp with time zone` | No | Al crear | — | Fecha y hora de creación del registro. | Interno |
| `updated_at` | `timestamp with time zone` | No | Al guardar | — | Fecha y hora de la última modificación. | Interno |
| `is_active` | `boolean` | No | `true` | — | Vigencia del registro; `false` equivale a baja lógica. | Interno |
| `name` | `character varying(150)` | No | — | UQ | Nombre del rol. | Interno |
| `slug` | `character varying(150)` | No | — | UQ | Identificador técnico del rol. Único. | Interno |
| `description` | `text` | No | — | — | Descripción del propósito del rol. | Interno |
| `is_system` | `boolean` | No | `false` | — | Rol del sistema, protegido frente a cambios que dejen la plataforma sin administrador. | Interno |
| `session_idle_timeout_minutes` | `integer` | No | `30` | — | Minutos máximos de inactividad antes de cerrar la sesión. Entre los roles activos de una cuenta se aplica el mayor. No negativo. | Interno |

### `identity_role_permissions` — Permisos del rol

Relación muchos a muchos entre roles y permisos atómicos.

- **Clasificación:** Interno.
- **Historia:** Se agrega o quita la fila al cambiar los permisos del rol; el cambio queda en la bitácora.

| Campo | Tipo | Nulo | Defecto | Clave | Descripción y regla | Clasif. |
| --- | --- | --- | --- | --- | --- | --- |
| `id` | `bigint` | No | Autogenerado | PK | Identificador interno secuencial. Clave primaria. | Interno |
| `role_id` | `bigint` | No | — | FK → `identity_role.id` (CASCADE) | Rol que recibe el permiso. | Interno |
| `permission_id` | `integer` | No | — | FK → `auth_permission.id` (CASCADE) | Permiso atómico concedido al rol. | Interno |

Restricciones e índices:

| Tipo | Nombre | Definición | Regla |
| --- | --- | --- | --- |
| Única compuesta | `identity_role_permissions_role_id_permission_id_97e7ca12_uniq` | `role_id`, `permission_id` | La combinación no se repite. |

### `identity_roleassignment` — Asignación de rol

Rol otorgado a una cuenta durante un periodo. Una cuenta puede tener varios roles; sus efectos se suman.

- **Clasificación:** Restringido.
- **Historia:** Se revoca fijando `ends_at`; la fila se conserva como historia.
- **La referencian:** `identity_scopegrant`.

| Campo | Tipo | Nulo | Defecto | Clave | Descripción y regla | Clasif. |
| --- | --- | --- | --- | --- | --- | --- |
| `id` | `bigint` | No | Autogenerado | PK | Identificador interno secuencial. Clave primaria. | Restringido |
| `public_id` | `uuid` | No | UUID aleatorio | UQ | Identificador público opaco que expone la API. Único, no editable. | Restringido |
| `created_at` | `timestamp with time zone` | No | Al crear | — | Fecha y hora de creación del registro. | Restringido |
| `updated_at` | `timestamp with time zone` | No | Al guardar | — | Fecha y hora de la última modificación. | Restringido |
| `is_active` | `boolean` | No | `true` | — | Vigencia del registro; `false` equivale a baja lógica. | Restringido |
| `starts_at` | `timestamp with time zone` | No | Momento actual | — | Inicio de vigencia de la asignación. | Restringido |
| `ends_at` | `timestamp with time zone` | Sí | — | — | Fin de vigencia; vacío si sigue vigente. Fijarlo equivale a revocar. | Restringido |
| `role_id` | `bigint` | No | — | FK → `identity_role.id` (PROTECT) | Rol asignado. | Restringido |
| `user_id` | `bigint` | No | — | FK → `identity_useraccount.id` (CASCADE) | Cuenta que recibe el rol. | Restringido |

Restricciones e índices:

| Tipo | Nombre | Definición | Regla |
| --- | --- | --- | --- |
| Única compuesta | `identity_roleassignment_user_id_role_id_starts_at_b3e38860_uniq` | `user_id`, `role_id`, `starts_at` | La combinación no se repite. |

### `identity_scopegrant` — Alcance

Delimita sobre qué datos aplica una asignación de rol: institución, ciclo, grado, sección, curso, asignación docente o estudiante. Un permiso sin alcance no concede acceso.

- **Clasificación:** Restringido.
- **Historia:** Se revoca con `ends_at` o `is_active`; la fila se conserva.

| Campo | Tipo | Nulo | Defecto | Clave | Descripción y regla | Clasif. |
| --- | --- | --- | --- | --- | --- | --- |
| `id` | `bigint` | No | Autogenerado | PK | Identificador interno secuencial. Clave primaria. | Restringido |
| `public_id` | `uuid` | No | UUID aleatorio | UQ | Identificador público opaco que expone la API. Único, no editable. | Restringido |
| `created_at` | `timestamp with time zone` | No | Al crear | — | Fecha y hora de creación del registro. | Restringido |
| `updated_at` | `timestamp with time zone` | No | Al guardar | — | Fecha y hora de la última modificación. | Restringido |
| `is_active` | `boolean` | No | `true` | — | Vigencia del registro; `false` equivale a baja lógica. | Restringido |
| `module_key` | `character varying(100)` | No | — | — | Módulo funcional al que se limita el alcance. Opcional. | Restringido |
| `starts_at` | `timestamp with time zone` | No | Momento actual | — | Inicio de vigencia del alcance. | Restringido |
| `ends_at` | `timestamp with time zone` | Sí | — | — | Fin de vigencia; vacío si sigue vigente. | Restringido |
| `academic_cycle_id` | `bigint` | Sí | — | FK → `academics_academiccycle.id` (CASCADE) | Dimensión ciclo escolar. Opcional. | Restringido |
| `assignment_id` | `bigint` | No | — | FK → `identity_roleassignment.id` (CASCADE) | Asignación de rol que este alcance delimita. | Restringido |
| `grade_id` | `bigint` | Sí | — | FK → `academics_grade.id` (CASCADE) | Dimensión grado. Opcional. | Restringido |
| `institution_id` | `bigint` | Sí | — | FK → `academics_institution.id` (CASCADE) | Dimensión institución. Opcional. | Restringido |
| `section_id` | `bigint` | Sí | — | FK → `academics_section.id` (CASCADE) | Dimensión sección. Opcional. | Restringido |
| `student_id` | `bigint` | Sí | — | FK → `students_student.id` (CASCADE) | Dimensión estudiante. Opcional. | Restringido |
| `subject_id` | `bigint` | Sí | — | FK → `academics_subject.id` (CASCADE) | Dimensión curso. Opcional. | Restringido |
| `teaching_assignment_id` | `bigint` | Sí | — | FK → `academics_teachingassignment.id` (CASCADE) | Dimensión asignación docente. Opcional. | Restringido |

Restricciones e índices:

| Tipo | Nombre | Definición | Regla |
| --- | --- | --- | --- |
| Verificación | `identity_scope_grant_has_dimension` | `CHECK (((NOT is_active) OR (institution_id IS NOT NULL) OR (academic_cycle_id IS NOT NULL) OR (grade_id IS NOT NULL) OR (section_id IS NOT NULL) OR (subject_id IS NOT NULL) OR (teaching_assignment_id IS NOT NULL) OR (student_id IS NOT NULL) OR (NOT ((module_key)::text = ''::text))))` | Todo alcance activo define al menos una dimensión. |

### `identity_useraccount` — Cuenta de usuario

Credenciales y estado de acceso de una persona. Toda cuenta pertenece obligatoriamente a una persona institucional y una persona tiene como máximo una cuenta.

- **Clasificación:** Restringido.
- **Historia:** No se elimina: se desactiva o bloquea con `status`. No hereda las columnas comunes porque extiende el usuario de Django.
- **La referencian:** `attendance_attendanceevent`, `attendance_attendancepermit`, `attendance_capturebatch`, `attendance_justification`, `attendance_justificationattachment`, `attendance_justificationnotification`, `attendance_sectionclosurelog`, `attendance_studentcredential`, `audit_auditevent`, `django_admin_log`, `documents_documentdownloadtoken`, `enrolments_studentmovementannulment`, `identity_activationchallenge`, `identity_passwordresetchallenge`, `identity_roleassignment`, `identity_useraccount_groups`, `identity_useraccount_user_permissions`, `reporting_alert`, `students_studenthealthnote`, `students_studentobservation`.

| Campo | Tipo | Nulo | Defecto | Clave | Descripción y regla | Clasif. |
| --- | --- | --- | --- | --- | --- | --- |
| `id` | `bigint` | No | Autogenerado | PK | Identificador interno secuencial. Clave primaria. | Restringido |
| `password` | `character varying(128)` | No | — | — | Resumen de la contraseña con el algoritmo de Django (PBKDF2). Nunca se guarda en claro. | Sensible especial |
| `last_login` | `timestamp with time zone` | Sí | — | — | Último inicio de sesión exitoso. | Restringido |
| `is_superuser` | `boolean` | No | `false` | — | Superusuario de Django: pasa la barrera de permisos. Uso excepcional. | Restringido |
| `username` | `character varying(150)` | No | — | UQ | Nombre de usuario para iniciar sesión. Único. | Restringido |
| `first_name` | `character varying(150)` | No | — | — | Heredado del usuario de Django. Los nombres canónicos están en `people_person`. | Restringido |
| `last_name` | `character varying(150)` | No | — | — | Heredado del usuario de Django. Los apellidos canónicos están en `people_person`. | Restringido |
| `email` | `character varying(254)` | No | — | — | Heredado del usuario de Django. El sistema no envía correo. | Restringido |
| `is_staff` | `boolean` | No | `false` | — | Permite entrar al sitio de administración de Django. | Restringido |
| `is_active` | `boolean` | No | `true` | — | Bandera de Django. El estado funcional de la cuenta está en `status`. | Restringido |
| `date_joined` | `timestamp with time zone` | No | Momento actual | — | Fecha y hora de creación de la cuenta. | Restringido |
| `status` | `character varying(20)` | No | `active` | — | Estado de la cuenta: pendiente de activación, activa, bloqueada o desactivada. Valores: `pending`, `active`, `blocked`, `disabled`. | Restringido |
| `failed_login_attempts` | `integer` | No | `0` | — | Intentos fallidos consecutivos de inicio de sesión. Al llegar al máximo configurado la cuenta se bloquea temporalmente. No negativo. | Restringido |
| `locked_until` | `timestamp with time zone` | Sí | — | — | Momento hasta el que la cuenta permanece bloqueada por intentos fallidos. | Restringido |
| `person_id` | `bigint` | No | — | FK → `people_person.id` (PROTECT); UQ | Persona institucional dueña de la cuenta. Obligatoria y única: no existe cuenta sin persona. | Restringido |

### `identity_useraccount_groups` — Grupos de la cuenta

Relación entre cuentas y grupos de Django, heredada del usuario base. La autorización del sistema se resuelve por roles y alcances, no por grupos.

- **Clasificación:** Interno.
- **Historia:** Gestionada por Django; no la administra el dominio.

| Campo | Tipo | Nulo | Defecto | Clave | Descripción y regla | Clasif. |
| --- | --- | --- | --- | --- | --- | --- |
| `id` | `bigint` | No | Autogenerado | PK | Identificador interno secuencial. Clave primaria. | Interno |
| `useraccount_id` | `bigint` | No | — | FK → `identity_useraccount.id` (CASCADE) | Cuenta asociada. | Interno |
| `group_id` | `integer` | No | — | FK → `auth_group.id` (CASCADE) | Grupo asociado. | Interno |

Restricciones e índices:

| Tipo | Nombre | Definición | Regla |
| --- | --- | --- | --- |
| Única compuesta | `identity_useraccount_gro_useraccount_id_group_id_db84dd21_uniq` | `useraccount_id`, `group_id` | La combinación no se repite. |

### `identity_useraccount_user_permissions` — Permisos directos de la cuenta

Relación entre cuentas y permisos, heredada del usuario base de Django. La autorización del sistema se resuelve por roles y alcances.

- **Clasificación:** Interno.
- **Historia:** Gestionada por Django; no la administra el dominio.

| Campo | Tipo | Nulo | Defecto | Clave | Descripción y regla | Clasif. |
| --- | --- | --- | --- | --- | --- | --- |
| `id` | `bigint` | No | Autogenerado | PK | Identificador interno secuencial. Clave primaria. | Interno |
| `useraccount_id` | `bigint` | No | — | FK → `identity_useraccount.id` (CASCADE) | Cuenta asociada. | Interno |
| `permission_id` | `integer` | No | — | FK → `auth_permission.id` (CASCADE) | Permiso asociado. | Interno |

Restricciones e índices:

| Tipo | Nombre | Definición | Regla |
| --- | --- | --- | --- |
| Única compuesta | `identity_useraccount_use_useraccount_id_permissio_d4a969ba_uniq` | `useraccount_id`, `permission_id` | La combinación no se repite. |

## 7. Expediente estudiantil

Estudiantes, encargados, vínculos, contactos, salud y observaciones.

### `students_emergencycontact` — Contacto de emergencia

Persona a quien llamar ante una emergencia del estudiante.

- **Clasificación:** Restringido.
- **Historia:** Sin borrado físico; baja lógica con `is_active`.

| Campo | Tipo | Nulo | Defecto | Clave | Descripción y regla | Clasif. |
| --- | --- | --- | --- | --- | --- | --- |
| `id` | `bigint` | No | Autogenerado | PK | Identificador interno secuencial. Clave primaria. | Restringido |
| `public_id` | `uuid` | No | UUID aleatorio | UQ | Identificador público opaco que expone la API. Único, no editable. | Restringido |
| `created_at` | `timestamp with time zone` | No | Al crear | — | Fecha y hora de creación del registro. | Restringido |
| `updated_at` | `timestamp with time zone` | No | Al guardar | — | Fecha y hora de la última modificación. | Restringido |
| `is_active` | `boolean` | No | `true` | — | Vigencia del registro; `false` equivale a baja lógica. | Restringido |
| `name` | `character varying(255)` | No | — | — | Nombre completo del contacto. | Restringido |
| `phone_number` | `character varying(30)` | No | — | — | Teléfono del contacto. | Restringido |
| `relationship_label` | `character varying(100)` | No | — | — | Parentesco o relación con el estudiante. | Restringido |
| `student_id` | `bigint` | No | — | FK → `students_student.id` (CASCADE) | Estudiante al que pertenece el registro. | Restringido |

### `students_guardian` — Encargado

Persona que actúa como encargado o responsable de uno o más estudiantes.

- **Clasificación:** Restringido.
- **Historia:** Sin borrado físico; baja lógica con `is_active`.
- **La referencian:** `documents_documentdeliveryreceipt`, `students_studentguardianrelation`.

| Campo | Tipo | Nulo | Defecto | Clave | Descripción y regla | Clasif. |
| --- | --- | --- | --- | --- | --- | --- |
| `id` | `bigint` | No | Autogenerado | PK | Identificador interno secuencial. Clave primaria. | Restringido |
| `public_id` | `uuid` | No | UUID aleatorio | UQ | Identificador público opaco que expone la API. Único, no editable. | Restringido |
| `created_at` | `timestamp with time zone` | No | Al crear | — | Fecha y hora de creación del registro. | Restringido |
| `updated_at` | `timestamp with time zone` | No | Al guardar | — | Fecha y hora de la última modificación. | Restringido |
| `is_active` | `boolean` | No | `true` | — | Vigencia del registro; `false` equivale a baja lógica. | Restringido |
| `person_id` | `bigint` | No | — | FK → `people_person.id` (PROTECT); UQ | Persona institucional del encargado. Relación 1:1. | Restringido |

### `students_student` — Estudiante

Expediente del estudiante: código, estado institucional y fotografía. Sus datos personales están en la persona asociada.

- **Clasificación:** Restringido.
- **Historia:** Sin borrado físico (el modelo lo rechaza); el ciclo de vida se refleja en `status` e `is_active`.
- **La referencian:** `attendance_attendancealert`, `attendance_attendanceevent`, `attendance_attendancepermit`, `attendance_justification`, `attendance_studentcredential`, `documents_documentdeliveryreceipt`, `documents_documentrecord`, `enrolments_enrolment`, `enrolments_studentmovement`, `identity_scopegrant`, `reporting_alert`, `students_emergencycontact`, `students_studentguardianrelation`, `students_studenthealthnote`, `students_studentobservation`.

| Campo | Tipo | Nulo | Defecto | Clave | Descripción y regla | Clasif. |
| --- | --- | --- | --- | --- | --- | --- |
| `id` | `bigint` | No | Autogenerado | PK | Identificador interno secuencial. Clave primaria. | Restringido |
| `public_id` | `uuid` | No | UUID aleatorio | UQ | Identificador público opaco que expone la API. Único, no editable. | Restringido |
| `created_at` | `timestamp with time zone` | No | Al crear | — | Fecha y hora de creación del registro. | Restringido |
| `updated_at` | `timestamp with time zone` | No | Al guardar | — | Fecha y hora de la última modificación. | Restringido |
| `is_active` | `boolean` | No | `true` | — | Vigencia del registro; `false` equivale a baja lógica. | Restringido |
| `student_code` | `character varying(50)` | No | — | UQ | Código institucional del estudiante. Único. | Restringido |
| `status` | `character varying(20)` | No | `pre_enrolled` | — | Estado institucional del estudiante. Un estudiante no activo restringe la interacción de su cuenta. Valores: `pre_enrolled`, `active`, `inactive`, `withdrawn`, `graduated`, `transferred`. | Restringido |
| `person_id` | `bigint` | No | — | FK → `people_person.id` (PROTECT); UQ | Persona institucional del estudiante. Relación 1:1. | Restringido |
| `photo` | `character varying(100)` | No | — | — | Ruta de la fotografía del estudiante (`student_photos/`). El archivo vive fuera de la base. | Restringido |

### `students_studentguardianrelation` — Vínculo estudiante-encargado

Relación entre un estudiante y un encargado, con parentesco, vigencia y marca de encargado principal. Determina el alcance derivado del encargado.

- **Clasificación:** Restringido.
- **Historia:** Se termina fijando `ends_at`; el vínculo terminado se conserva como historia.

| Campo | Tipo | Nulo | Defecto | Clave | Descripción y regla | Clasif. |
| --- | --- | --- | --- | --- | --- | --- |
| `id` | `bigint` | No | Autogenerado | PK | Identificador interno secuencial. Clave primaria. | Restringido |
| `public_id` | `uuid` | No | UUID aleatorio | UQ | Identificador público opaco que expone la API. Único, no editable. | Restringido |
| `created_at` | `timestamp with time zone` | No | Al crear | — | Fecha y hora de creación del registro. | Restringido |
| `updated_at` | `timestamp with time zone` | No | Al guardar | — | Fecha y hora de la última modificación. | Restringido |
| `is_active` | `boolean` | No | `true` | — | Vigencia del registro; `false` equivale a baja lógica. | Restringido |
| `relationship_label` | `character varying(100)` | No | — | — | Parentesco declarado (madre, padre, tutor, etc.). | Restringido |
| `is_primary` | `boolean` | No | `false` | — | Marca al encargado principal. Solo uno vigente por estudiante. | Restringido |
| `starts_at` | `date` | No | Fecha actual | — | Fecha de inicio del vínculo. | Restringido |
| `ends_at` | `date` | Sí | — | — | Fecha de fin del vínculo; vacía si sigue vigente. Al terminar, el encargado pierde el alcance sobre el estudiante. | Restringido |
| `guardian_id` | `bigint` | No | — | FK → `students_guardian.id` (PROTECT) | Encargado del vínculo. | Restringido |
| `student_id` | `bigint` | No | — | FK → `students_student.id` (CASCADE) | Estudiante del vínculo. | Restringido |

Restricciones e índices:

| Tipo | Nombre | Definición | Regla |
| --- | --- | --- | --- |
| Única parcial | `students_one_current_primary_guardian` | `btree (student_id) WHERE ((ends_at IS NULL) AND is_primary)` | Un solo encargado principal vigente por estudiante. |

### `students_studenthealthnote` — Nota de salud

Anotación de salud del estudiante, con autor y fecha. Su lectura individual queda auditada.

- **Clasificación:** Sensible especial.
- **Historia:** Sin borrado físico; baja lógica con `is_active`.

| Campo | Tipo | Nulo | Defecto | Clave | Descripción y regla | Clasif. |
| --- | --- | --- | --- | --- | --- | --- |
| `id` | `bigint` | No | Autogenerado | PK | Identificador interno secuencial. Clave primaria. | Sensible especial |
| `public_id` | `uuid` | No | UUID aleatorio | UQ | Identificador público opaco que expone la API. Único, no editable. | Sensible especial |
| `created_at` | `timestamp with time zone` | No | Al crear | — | Fecha y hora de creación del registro. | Sensible especial |
| `updated_at` | `timestamp with time zone` | No | Al guardar | — | Fecha y hora de la última modificación. | Sensible especial |
| `is_active` | `boolean` | No | `true` | — | Vigencia del registro; `false` equivale a baja lógica. | Sensible especial |
| `content` | `text` | No | — | — | Texto de la nota de salud. | Sensible especial |
| `recorded_on` | `date` | No | Fecha actual | — | Fecha en que se registró la nota. | Sensible especial |
| `author_id` | `bigint` | No | — | FK → `identity_useraccount.id` (PROTECT) | Cuenta que redactó la anotación. | Sensible especial |
| `student_id` | `bigint` | No | — | FK → `students_student.id` (PROTECT) | Estudiante al que pertenece el registro. | Sensible especial |

### `students_studentobservation` — Observación del estudiante

Observación o anotación disciplinaria, con autor y fecha. Su lectura individual queda auditada.

- **Clasificación:** Sensible especial.
- **Historia:** Sin borrado físico; baja lógica con `is_active`.

| Campo | Tipo | Nulo | Defecto | Clave | Descripción y regla | Clasif. |
| --- | --- | --- | --- | --- | --- | --- |
| `id` | `bigint` | No | Autogenerado | PK | Identificador interno secuencial. Clave primaria. | Sensible especial |
| `public_id` | `uuid` | No | UUID aleatorio | UQ | Identificador público opaco que expone la API. Único, no editable. | Sensible especial |
| `created_at` | `timestamp with time zone` | No | Al crear | — | Fecha y hora de creación del registro. | Sensible especial |
| `updated_at` | `timestamp with time zone` | No | Al guardar | — | Fecha y hora de la última modificación. | Sensible especial |
| `is_active` | `boolean` | No | `true` | — | Vigencia del registro; `false` equivale a baja lógica. | Sensible especial |
| `description` | `text` | No | — | — | Texto de la observación. | Sensible especial |
| `observed_on` | `date` | No | Fecha actual | — | Fecha del hecho observado. | Sensible especial |
| `author_id` | `bigint` | No | — | FK → `identity_useraccount.id` (PROTECT) | Cuenta que redactó la anotación. | Sensible especial |
| `student_id` | `bigint` | No | — | FK → `students_student.id` (PROTECT) | Estudiante al que pertenece el registro. | Sensible especial |

## 8. Docentes

Docente como actor institucional.

### `teachers_teacher` — Docente

Datos laborales del docente: código de empleado, especialidad, puesto, nombramiento y fotografía. Sus datos personales están en la persona asociada.

- **Clasificación:** Restringido.
- **Historia:** Baja lógica con `is_active`; no se elimina físicamente.

| Campo | Tipo | Nulo | Defecto | Clave | Descripción y regla | Clasif. |
| --- | --- | --- | --- | --- | --- | --- |
| `id` | `bigint` | No | Autogenerado | PK | Identificador interno secuencial. Clave primaria. | Restringido |
| `public_id` | `uuid` | No | UUID aleatorio | UQ | Identificador público opaco que expone la API. Único, no editable. | Restringido |
| `created_at` | `timestamp with time zone` | No | Al crear | — | Fecha y hora de creación del registro. | Restringido |
| `updated_at` | `timestamp with time zone` | No | Al guardar | — | Fecha y hora de la última modificación. | Restringido |
| `is_active` | `boolean` | No | `true` | — | Vigencia del registro; `false` equivale a baja lógica. | Restringido |
| `employee_code` | `character varying(50)` | No | — | UQ | Código de empleado del docente. Único. | Restringido |
| `specialty` | `character varying(150)` | No | — | — | Especialidad o área del docente. | Restringido |
| `position` | `character varying(20)` | No | — | — | Puesto que ocupa. Valores: `Docente Titulado`, `Docente Interino`, `Orientador/a`, `Administrativo`. | Restringido |
| `appointment_date` | `date` | Sí | — | — | Fecha de nombramiento. Opcional. | Restringido |
| `photo` | `character varying(100)` | No | — | — | Ruta de la fotografía del docente (`teacher_photos/`). El archivo vive fuera de la base. | Restringido |
| `person_id` | `bigint` | No | — | FK → `people_person.id` (PROTECT); UQ | Persona institucional del docente. Relación 1:1. | Restringido |

## 9. Estructura académica

Institución, sedes, jornadas, niveles, grados, secciones, cursos, horarios, asignaciones y resultados congelados.

### `academics_academiccycle` — Ciclo escolar

Año lectivo de la institución, con fechas y estado. Solo puede haber un ciclo activo por institución.

- **Clasificación:** Interno.
- **Historia:** No se elimina: pasa por los estados borrador, activo y cerrado.
- **La referencian:** `academics_classschedulepublication`, `academics_classsession`, `academics_curriculumplan`, `academics_gradeoffering`, `academics_teachingassignment`, `attendance_jornadaparameters`, `enrolments_enrolment`, `evaluation_cycleevaluationconfig`, `evaluation_evaluationunit`, `identity_scopegrant`, `reporting_absencethresholdparameters`.

| Campo | Tipo | Nulo | Defecto | Clave | Descripción y regla | Clasif. |
| --- | --- | --- | --- | --- | --- | --- |
| `id` | `bigint` | No | Autogenerado | PK | Identificador interno secuencial. Clave primaria. | Interno |
| `public_id` | `uuid` | No | UUID aleatorio | UQ | Identificador público opaco que expone la API. Único, no editable. | Interno |
| `created_at` | `timestamp with time zone` | No | Al crear | — | Fecha y hora de creación del registro. | Interno |
| `updated_at` | `timestamp with time zone` | No | Al guardar | — | Fecha y hora de la última modificación. | Interno |
| `is_active` | `boolean` | No | `true` | — | Vigencia del registro; `false` equivale a baja lógica. | Interno |
| `name` | `character varying(100)` | No | — | — | Nombre del ciclo. Único por institución. | Interno |
| `starts_on` | `date` | No | — | — | Primer día del ciclo. | Interno |
| `ends_on` | `date` | No | — | — | Último día del ciclo. | Interno |
| `status` | `character varying(20)` | No | `draft` | — | Estado del ciclo: borrador, activo o cerrado. Valores: `draft`, `active`, `closed`. | Interno |
| `institution_id` | `bigint` | No | — | FK → `academics_institution.id` (CASCADE) | Institución a la que pertenece. | Interno |
| `description` | `text` | No | — | — | Descripción libre. | Interno |
| `year` | `smallint` | No | — | — | Año lectivo. Único por institución. No negativo. | Interno |

Restricciones e índices:

| Tipo | Nombre | Definición | Regla |
| --- | --- | --- | --- |
| Verificación | `academic_cycle_valid_dates` | `CHECK ((starts_on <= ends_on))` | El inicio del ciclo no puede ser posterior a su fin. |
| Única compuesta | `unique_cycle_name_per_institution` | `institution_id`, `name` | No se repite el nombre de ciclo en una institución. |
| Única compuesta | `unique_cycle_year_per_institution` | `institution_id`, `year` | Un solo ciclo por año en una institución. |
| Exclusión | `academic_cycle_no_overlapping_dates` | `EXCLUDE USING gist (institution_id WITH =, daterange(starts_on, ends_on, '[]'::text) WITH &&)` | Los ciclos de una institución no pueden traslapar sus fechas. |
| Única parcial | `unique_active_cycle_per_institution` | `btree (institution_id) WHERE ((status)::text = 'active'::text)` | Un solo ciclo activo por institución. |

### `academics_campus` — Sede

Sitio físico de la institución. De ella dependen las jornadas y, por tanto, toda la oferta de grados.

- **Clasificación:** Interno.
- **Historia:** Baja lógica con `is_active`; no se elimina físicamente.
- **La referencian:** `academics_classroom`, `academics_shift`, `attendance_controlpoint`.

| Campo | Tipo | Nulo | Defecto | Clave | Descripción y regla | Clasif. |
| --- | --- | --- | --- | --- | --- | --- |
| `id` | `bigint` | No | Autogenerado | PK | Identificador interno secuencial. Clave primaria. | Interno |
| `public_id` | `uuid` | No | UUID aleatorio | UQ | Identificador público opaco que expone la API. Único, no editable. | Interno |
| `created_at` | `timestamp with time zone` | No | Al crear | — | Fecha y hora de creación del registro. | Interno |
| `updated_at` | `timestamp with time zone` | No | Al guardar | — | Fecha y hora de la última modificación. | Interno |
| `is_active` | `boolean` | No | `true` | — | Vigencia del registro; `false` equivale a baja lógica. | Interno |
| `name` | `character varying(150)` | No | — | — | Nombre de la sede. | Interno |
| `code` | `character varying(30)` | No | — | — | Código de la sede. Único por institución. | Interno |
| `address` | `character varying(255)` | No | — | — | Dirección física de la sede. | Interno |
| `is_main` | `boolean` | No | `false` | — | Marca la sede principal. Solo una por institución. | Interno |
| `institution_id` | `bigint` | No | — | FK → `academics_institution.id` (CASCADE) | Institución a la que pertenece. | Interno |

Restricciones e índices:

| Tipo | Nombre | Definición | Regla |
| --- | --- | --- | --- |
| Única compuesta | `unique_campus_code_per_institution` | `institution_id`, `code` | El código de sede no se repite en una institución. |
| Única parcial | `unique_main_campus_per_institution` | `btree (institution_id) WHERE is_main` | Una sola sede principal por institución. |

### `academics_classroom` — Aula

Aula, laboratorio u otro espacio de enseñanza de una sede, con capacidad y estado de servicio.

- **Clasificación:** Interno.
- **Historia:** Baja lógica con `is_active`; no se elimina físicamente.
- **La referencian:** `academics_classsession`, `academics_section`.

| Campo | Tipo | Nulo | Defecto | Clave | Descripción y regla | Clasif. |
| --- | --- | --- | --- | --- | --- | --- |
| `id` | `bigint` | No | Autogenerado | PK | Identificador interno secuencial. Clave primaria. | Interno |
| `public_id` | `uuid` | No | UUID aleatorio | UQ | Identificador público opaco que expone la API. Único, no editable. | Interno |
| `created_at` | `timestamp with time zone` | No | Al crear | — | Fecha y hora de creación del registro. | Interno |
| `updated_at` | `timestamp with time zone` | No | Al guardar | — | Fecha y hora de la última modificación. | Interno |
| `is_active` | `boolean` | No | `true` | — | Vigencia del registro; `false` equivale a baja lógica. | Interno |
| `name` | `character varying(150)` | No | — | — | Nombre del aula. | Interno |
| `code` | `character varying(30)` | No | — | — | Código del aula. Único por sede. | Interno |
| `location` | `character varying(255)` | No | — | — | Ubicación dentro de la sede. | Interno |
| `capacity` | `integer` | No | `0` | — | Capacidad del aula en personas. No negativo. | Interno |
| `campus_id` | `bigint` | No | — | FK → `academics_campus.id` (PROTECT) | Sede a la que pertenece. | Interno |
| `service_status` | `character varying(20)` | No | `available` | — | Estado de servicio del aula. Valores: `available`, `unavailable`, `maintenance`. | Interno |

Restricciones e índices:

| Tipo | Nombre | Definición | Regla |
| --- | --- | --- | --- |
| Única compuesta | `unique_classroom_code_per_campus` | `campus_id`, `code` | El código de aula no se repite en una sede. |

### `academics_classscheduleblock` — Bloque de horario

Periodo de la rejilla horaria de una jornada (por ejemplo, «Bloque 1: 07:00-07:45»).

- **Clasificación:** Interno.
- **Historia:** Baja lógica con `is_active`; no se elimina físicamente.
- **La referencian:** `academics_classsession`.

| Campo | Tipo | Nulo | Defecto | Clave | Descripción y regla | Clasif. |
| --- | --- | --- | --- | --- | --- | --- |
| `id` | `bigint` | No | Autogenerado | PK | Identificador interno secuencial. Clave primaria. | Interno |
| `public_id` | `uuid` | No | UUID aleatorio | UQ | Identificador público opaco que expone la API. Único, no editable. | Interno |
| `created_at` | `timestamp with time zone` | No | Al crear | — | Fecha y hora de creación del registro. | Interno |
| `updated_at` | `timestamp with time zone` | No | Al guardar | — | Fecha y hora de la última modificación. | Interno |
| `is_active` | `boolean` | No | `true` | — | Vigencia del registro; `false` equivale a baja lógica. | Interno |
| `number` | `smallint` | No | — | — | Orden del bloque dentro de la jornada: 1, 2, 3, etc. No negativo. | Interno |
| `name` | `character varying(100)` | No | — | — | Nombre para mostrar: «Bloque 1», «Recreo», etc. | Interno |
| `starts_on` | `time without time zone` | No | — | — | Hora de inicio del bloque. | Interno |
| `ends_on` | `time without time zone` | No | — | — | Hora de fin del bloque. | Interno |
| `shift_id` | `bigint` | No | — | FK → `academics_shift.id` (CASCADE) | Jornada a la que corresponde. | Interno |

Restricciones e índices:

| Tipo | Nombre | Definición | Regla |
| --- | --- | --- | --- |
| Verificación | `class_schedule_block_valid_times` | `CHECK ((starts_on < ends_on))` | La hora de inicio del bloque es anterior a la de fin. |
| Única compuesta | `unique_schedule_block_number_per_shift` | `shift_id`, `number` | El número de bloque no se repite en una jornada. |

### `academics_classschedulepublication` — Publicación del horario

Estado de publicación del horario de un ciclo. Mientras no se publique, las sesiones son un borrador de trabajo.

- **Clasificación:** Interno.
- **Historia:** Baja lógica con `is_active`; no se elimina físicamente.

| Campo | Tipo | Nulo | Defecto | Clave | Descripción y regla | Clasif. |
| --- | --- | --- | --- | --- | --- | --- |
| `id` | `bigint` | No | Autogenerado | PK | Identificador interno secuencial. Clave primaria. | Interno |
| `public_id` | `uuid` | No | UUID aleatorio | UQ | Identificador público opaco que expone la API. Único, no editable. | Interno |
| `created_at` | `timestamp with time zone` | No | Al crear | — | Fecha y hora de creación del registro. | Interno |
| `updated_at` | `timestamp with time zone` | No | Al guardar | — | Fecha y hora de la última modificación. | Interno |
| `is_active` | `boolean` | No | `true` | — | Vigencia del registro; `false` equivale a baja lógica. | Interno |
| `published_at` | `timestamp with time zone` | Sí | — | — | Momento de publicación del horario; vacío mientras es borrador. | Interno |
| `academic_cycle_id` | `bigint` | No | — | FK → `academics_academiccycle.id` (CASCADE); UQ | Ciclo cuyo horario se publica. Relación 1:1. | Interno |

### `academics_classsession` — Sesión de clase

Clase programada: un curso impartido a una sección un día de la semana en un bloque. El docente no se guarda aquí: se deriva de la asignación docente vigente.

- **Clasificación:** Interno.
- **Historia:** Baja lógica con `is_active`; no se elimina físicamente.

| Campo | Tipo | Nulo | Defecto | Clave | Descripción y regla | Clasif. |
| --- | --- | --- | --- | --- | --- | --- |
| `id` | `bigint` | No | Autogenerado | PK | Identificador interno secuencial. Clave primaria. | Interno |
| `public_id` | `uuid` | No | UUID aleatorio | UQ | Identificador público opaco que expone la API. Único, no editable. | Interno |
| `created_at` | `timestamp with time zone` | No | Al crear | — | Fecha y hora de creación del registro. | Interno |
| `updated_at` | `timestamp with time zone` | No | Al guardar | — | Fecha y hora de la última modificación. | Interno |
| `is_active` | `boolean` | No | `true` | — | Vigencia del registro; `false` equivale a baja lógica. | Interno |
| `day_of_week` | `smallint` | No | — | — | Día de la semana, de 1 (lunes) a 7 (domingo). No negativo. | Interno |
| `academic_cycle_id` | `bigint` | No | — | FK → `academics_academiccycle.id` (CASCADE) | Ciclo escolar al que pertenece. | Interno |
| `schedule_block_id` | `bigint` | No | — | FK → `academics_classscheduleblock.id` (PROTECT) | Bloque de la rejilla horaria en que ocurre la clase. | Interno |
| `section_id` | `bigint` | No | — | FK → `academics_section.id` (CASCADE) | Sección a la que corresponde. | Interno |
| `subject_id` | `bigint` | No | — | FK → `academics_subject.id` (CASCADE) | Curso al que corresponde. | Interno |
| `classroom_id` | `bigint` | Sí | — | FK → `academics_classroom.id` (PROTECT) | Aula asignada a la sesión. Opcional. | Interno |
| `starts_on` | `date` | No | Fecha actual | — | Fecha desde la que la sesión está vigente. | Interno |

Restricciones e índices:

| Tipo | Nombre | Definición | Regla |
| --- | --- | --- | --- |
| Única compuesta | `unique_class_session_registration` | `section_id`, `subject_id`, `day_of_week`, `schedule_block_id` | No se duplica la misma clase (sección, curso, día y bloque). |

### `academics_curriculumplan` — Plan de estudios

Cursos que componen el plan de un grado en un ciclo determinado.

- **Clasificación:** Interno.
- **Historia:** Baja lógica con `is_active`; no se elimina físicamente.

| Campo | Tipo | Nulo | Defecto | Clave | Descripción y regla | Clasif. |
| --- | --- | --- | --- | --- | --- | --- |
| `id` | `bigint` | No | Autogenerado | PK | Identificador interno secuencial. Clave primaria. | Interno |
| `public_id` | `uuid` | No | UUID aleatorio | UQ | Identificador público opaco que expone la API. Único, no editable. | Interno |
| `created_at` | `timestamp with time zone` | No | Al crear | — | Fecha y hora de creación del registro. | Interno |
| `updated_at` | `timestamp with time zone` | No | Al guardar | — | Fecha y hora de la última modificación. | Interno |
| `is_active` | `boolean` | No | `true` | — | Vigencia del registro; `false` equivale a baja lógica. | Interno |
| `is_required` | `boolean` | No | `true` | — | Indica si el curso es obligatorio en el plan. | Interno |
| `academic_cycle_id` | `bigint` | No | — | FK → `academics_academiccycle.id` (CASCADE) | Ciclo escolar al que pertenece. | Interno |
| `grade_id` | `bigint` | No | — | FK → `academics_grade.id` (CASCADE) | Grado al que corresponde. | Interno |
| `subject_id` | `bigint` | No | — | FK → `academics_subject.id` (CASCADE) | Curso al que corresponde. | Interno |

Restricciones e índices:

| Tipo | Nombre | Definición | Regla |
| --- | --- | --- | --- |
| Única compuesta | `unique_curriculum_plan_per_cycle_grade_subject` | `academic_cycle_id`, `grade_id`, `subject_id` | Un curso aparece una sola vez en el plan de un grado y ciclo. |

### `academics_frozenpromotionresult` — Resultado congelado de promoción

Fotografía inmutable de la condición de promoción de una matrícula al cierre del ciclo.

- **Clasificación:** Restringido.
- **Historia:** Solo inserción: una corrección agrega una fila nueva con `is_correction = true` y motivo obligatorio.

| Campo | Tipo | Nulo | Defecto | Clave | Descripción y regla | Clasif. |
| --- | --- | --- | --- | --- | --- | --- |
| `id` | `bigint` | No | Autogenerado | PK | Identificador interno secuencial. Clave primaria. | Restringido |
| `public_id` | `uuid` | No | UUID aleatorio | UQ | Identificador público opaco que expone la API. Único, no editable. | Restringido |
| `created_at` | `timestamp with time zone` | No | Al crear | — | Fecha y hora de creación del registro. | Restringido |
| `updated_at` | `timestamp with time zone` | No | Al guardar | — | Fecha y hora de la última modificación. | Restringido |
| `is_active` | `boolean` | No | `true` | — | Vigencia del registro; `false` equivale a baja lógica. | Restringido |
| `promoted` | `boolean` | No | — | — | Indica si el estudiante fue promovido. | Restringido |
| `condition` | `character varying(20)` | No | — | — | Condición de promoción al cierre del ciclo. | Restringido |
| `failed_subjects` | `jsonb` | No | `[]` | — | Lista de cursos reprobados al cierre, en JSON. | Restringido |
| `is_correction` | `boolean` | No | `false` | — | Indica que la fila corrige un resultado ya congelado. | Restringido |
| `correction_reason` | `text` | No | Vacío | — | Motivo de la corrección. Obligatorio cuando `is_correction` es verdadero. | Restringido |
| `enrolment_id` | `bigint` | No | — | FK → `enrolments_enrolment.id` (PROTECT) | Matrícula a la que pertenece; liga el registro al estudiante, la sección y el ciclo. | Restringido |

Restricciones e índices:

| Tipo | Nombre | Definición | Regla |
| --- | --- | --- | --- |
| Verificación | `frozen_promotion_result_correction_requires_reason` | `CHECK (((NOT is_correction) OR (NOT (correction_reason = ''::text))))` | Toda corrección de promoción exige motivo. |

### `academics_frozensubjectresult` — Resultado congelado por curso

Fotografía inmutable del resultado final de un curso para una matrícula al cierre del ciclo.

- **Clasificación:** Restringido.
- **Historia:** Solo inserción: una corrección agrega una fila nueva con `is_correction = true` y motivo obligatorio.

| Campo | Tipo | Nulo | Defecto | Clave | Descripción y regla | Clasif. |
| --- | --- | --- | --- | --- | --- | --- |
| `id` | `bigint` | No | Autogenerado | PK | Identificador interno secuencial. Clave primaria. | Restringido |
| `public_id` | `uuid` | No | UUID aleatorio | UQ | Identificador público opaco que expone la API. Único, no editable. | Restringido |
| `created_at` | `timestamp with time zone` | No | Al crear | — | Fecha y hora de creación del registro. | Restringido |
| `updated_at` | `timestamp with time zone` | No | Al guardar | — | Fecha y hora de la última modificación. | Restringido |
| `is_active` | `boolean` | No | `true` | — | Vigencia del registro; `false` equivale a baja lógica. | Restringido |
| `final_grade` | `smallint` | Sí | — | — | Nota final redondeada del curso. No negativo. | Restringido |
| `condition` | `character varying(30)` | No | Vacío | — | Condición del curso al cierre (aprobado, reprobado, etc.). | Restringido |
| `recovery_grade` | `smallint` | Sí | — | — | Nota de recuperación, si la hubo. No negativo. | Restringido |
| `is_correction` | `boolean` | No | `false` | — | Indica que la fila corrige un resultado ya congelado. | Restringido |
| `correction_reason` | `text` | No | Vacío | — | Motivo de la corrección. Obligatorio cuando `is_correction` es verdadero. | Restringido |
| `enrolment_id` | `bigint` | No | — | FK → `enrolments_enrolment.id` (PROTECT) | Matrícula a la que pertenece; liga el registro al estudiante, la sección y el ciclo. | Restringido |
| `subject_id` | `bigint` | No | — | FK → `academics_subject.id` (PROTECT) | Curso al que corresponde. | Restringido |

Restricciones e índices:

| Tipo | Nombre | Definición | Regla |
| --- | --- | --- | --- |
| Verificación | `frozen_subject_result_correction_requires_reason` | `CHECK (((NOT is_correction) OR (NOT (correction_reason = ''::text))))` | Toda corrección de resultado por curso exige motivo. |

### `academics_grade` — Grado

Grado dentro de un nivel (por ejemplo, primero básico).

- **Clasificación:** Interno.
- **Historia:** Baja lógica con `is_active`; no se elimina físicamente.
- **La referencian:** `academics_curriculumplan`, `academics_gradeoffering`, `enrolments_enrolment`, `identity_scopegrant`.

| Campo | Tipo | Nulo | Defecto | Clave | Descripción y regla | Clasif. |
| --- | --- | --- | --- | --- | --- | --- |
| `id` | `bigint` | No | Autogenerado | PK | Identificador interno secuencial. Clave primaria. | Interno |
| `public_id` | `uuid` | No | UUID aleatorio | UQ | Identificador público opaco que expone la API. Único, no editable. | Interno |
| `created_at` | `timestamp with time zone` | No | Al crear | — | Fecha y hora de creación del registro. | Interno |
| `updated_at` | `timestamp with time zone` | No | Al guardar | — | Fecha y hora de la última modificación. | Interno |
| `is_active` | `boolean` | No | `true` | — | Vigencia del registro; `false` equivale a baja lógica. | Interno |
| `name` | `character varying(100)` | No | — | — | Nombre del grado. | Interno |
| `code` | `character varying(30)` | No | — | — | Código del grado. Único por institución. | Interno |
| `institution_id` | `bigint` | No | — | FK → `academics_institution.id` (CASCADE) | Institución del grado. Duplica la del nivel a propósito, para poder exigir la unicidad del código por institución. | Interno |
| `sequence` | `integer` | No | — | — | Orden del grado dentro del nivel. Único por nivel. No negativo. | Interno |
| `level_id` | `bigint` | No | — | FK → `academics_level.id` (PROTECT) | Nivel al que pertenece. | Interno |

Restricciones e índices:

| Tipo | Nombre | Definición | Regla |
| --- | --- | --- | --- |
| Única compuesta | `unique_grade_code_per_institution` | `institution_id`, `code` | El código de grado no se repite en una institución. |
| Única compuesta | `unique_grade_sequence_per_level` | `level_id`, `sequence` | El orden del grado no se repite dentro de un nivel. |

### `academics_gradeoffering` — Oferta de grado

Grado que realmente se ofrece en una jornada durante un ciclo. Es el nodo del catálogo al que se asignan las secciones y se reconstruye en cada ciclo.

- **Clasificación:** Interno.
- **Historia:** Baja lógica con `is_active`; no se elimina físicamente.
- **La referencian:** `academics_section`.

| Campo | Tipo | Nulo | Defecto | Clave | Descripción y regla | Clasif. |
| --- | --- | --- | --- | --- | --- | --- |
| `id` | `bigint` | No | Autogenerado | PK | Identificador interno secuencial. Clave primaria. | Interno |
| `public_id` | `uuid` | No | UUID aleatorio | UQ | Identificador público opaco que expone la API. Único, no editable. | Interno |
| `created_at` | `timestamp with time zone` | No | Al crear | — | Fecha y hora de creación del registro. | Interno |
| `updated_at` | `timestamp with time zone` | No | Al guardar | — | Fecha y hora de la última modificación. | Interno |
| `is_active` | `boolean` | No | `true` | — | Vigencia del registro; `false` equivale a baja lógica. | Interno |
| `academic_cycle_id` | `bigint` | No | — | FK → `academics_academiccycle.id` (CASCADE) | Ciclo escolar al que pertenece. | Interno |
| `grade_id` | `bigint` | No | — | FK → `academics_grade.id` (PROTECT) | Grado que se ofrece. | Interno |
| `shift_id` | `bigint` | No | — | FK → `academics_shift.id` (PROTECT) | Jornada en la que se ofrece. | Interno |

Restricciones e índices:

| Tipo | Nombre | Definición | Regla |
| --- | --- | --- | --- |
| Única compuesta | `unique_grade_offering_per_cycle_shift` | `academic_cycle_id`, `shift_id`, `grade_id` | Un grado se ofrece una sola vez por ciclo y jornada. |

### `academics_institution` — Institución

Establecimiento educativo propietario de la estructura académica y de los catálogos.

- **Clasificación:** Interno.
- **Historia:** Baja lógica con `is_active`; no se elimina físicamente.
- **La referencian:** `academics_academiccycle`, `academics_campus`, `academics_grade`, `academics_level`, `academics_subject`, `documents_documentkind`, `documents_documenttemplate`, `documents_officialfolio`, `identity_scopegrant`.

| Campo | Tipo | Nulo | Defecto | Clave | Descripción y regla | Clasif. |
| --- | --- | --- | --- | --- | --- | --- |
| `id` | `bigint` | No | Autogenerado | PK | Identificador interno secuencial. Clave primaria. | Interno |
| `public_id` | `uuid` | No | UUID aleatorio | UQ | Identificador público opaco que expone la API. Único, no editable. | Interno |
| `created_at` | `timestamp with time zone` | No | Al crear | — | Fecha y hora de creación del registro. | Interno |
| `updated_at` | `timestamp with time zone` | No | Al guardar | — | Fecha y hora de la última modificación. | Interno |
| `is_active` | `boolean` | No | `true` | — | Vigencia del registro; `false` equivale a baja lógica. | Interno |
| `name` | `character varying(255)` | No | — | — | Nombre oficial de la institución. | Interno |
| `short_name` | `character varying(100)` | No | — | — | Nombre corto o siglas. | Interno |

### `academics_level` — Nivel

Nivel educativo de la institución (por ejemplo, básico), con su orden pedagógico.

- **Clasificación:** Interno.
- **Historia:** Baja lógica con `is_active`; no se elimina físicamente.
- **La referencian:** `academics_grade`, `academics_levelsubject`.

| Campo | Tipo | Nulo | Defecto | Clave | Descripción y regla | Clasif. |
| --- | --- | --- | --- | --- | --- | --- |
| `id` | `bigint` | No | Autogenerado | PK | Identificador interno secuencial. Clave primaria. | Interno |
| `public_id` | `uuid` | No | UUID aleatorio | UQ | Identificador público opaco que expone la API. Único, no editable. | Interno |
| `created_at` | `timestamp with time zone` | No | Al crear | — | Fecha y hora de creación del registro. | Interno |
| `updated_at` | `timestamp with time zone` | No | Al guardar | — | Fecha y hora de la última modificación. | Interno |
| `is_active` | `boolean` | No | `true` | — | Vigencia del registro; `false` equivale a baja lógica. | Interno |
| `name` | `character varying(100)` | No | — | — | Nombre del nivel. | Interno |
| `code` | `character varying(30)` | No | — | — | Código del nivel. Único por institución. | Interno |
| `sequence` | `integer` | No | — | — | Orden pedagógico del nivel. Único por institución. No negativo. | Interno |
| `institution_id` | `bigint` | No | — | FK → `academics_institution.id` (CASCADE) | Institución a la que pertenece. | Interno |

Restricciones e índices:

| Tipo | Nombre | Definición | Regla |
| --- | --- | --- | --- |
| Única compuesta | `unique_level_code_per_institution` | `institution_id`, `code` | El código de nivel no se repite en una institución. |
| Única compuesta | `unique_level_id_institution` | `id`, `institution_id` | Unicidad técnica que permite referenciar el nivel junto con su institución. |
| Única compuesta | `unique_level_sequence_per_institution` | `institution_id`, `sequence` | El orden del nivel no se repite en una institución. |

### `academics_levelsubject` — Curso del nivel

Curso ofrecido en un nivel, con su carácter obligatorio y horas semanales.

- **Clasificación:** Interno.
- **Historia:** Baja lógica con `is_active`; no se elimina físicamente.

| Campo | Tipo | Nulo | Defecto | Clave | Descripción y regla | Clasif. |
| --- | --- | --- | --- | --- | --- | --- |
| `id` | `bigint` | No | Autogenerado | PK | Identificador interno secuencial. Clave primaria. | Interno |
| `public_id` | `uuid` | No | UUID aleatorio | UQ | Identificador público opaco que expone la API. Único, no editable. | Interno |
| `created_at` | `timestamp with time zone` | No | Al crear | — | Fecha y hora de creación del registro. | Interno |
| `updated_at` | `timestamp with time zone` | No | Al guardar | — | Fecha y hora de la última modificación. | Interno |
| `is_active` | `boolean` | No | `true` | — | Vigencia del registro; `false` equivale a baja lógica. | Interno |
| `is_required` | `boolean` | No | `true` | — | Indica si el curso es obligatorio en el nivel. | Interno |
| `weekly_hours` | `integer` | No | `0` | — | Horas semanales del curso en el nivel. No negativo. | Interno |
| `level_id` | `bigint` | No | — | FK → `academics_level.id` (CASCADE) | Nivel al que pertenece. | Interno |
| `subject_id` | `bigint` | No | — | FK → `academics_subject.id` (CASCADE) | Curso al que corresponde. | Interno |

Restricciones e índices:

| Tipo | Nombre | Definición | Regla |
| --- | --- | --- | --- |
| Única compuesta | `unique_subject_per_level` | `level_id`, `subject_id` | Un curso se vincula una sola vez a un nivel. |

### `academics_section` — Sección

Grupo concreto de estudiantes dentro de una oferta de grado, con cupo y aula habitual.

- **Clasificación:** Interno.
- **Historia:** Baja lógica con `is_active`; no se elimina físicamente.
- **La referencian:** `academics_classsession`, `academics_teachingassignment`, `attendance_attendancealert`, `attendance_sectionclosurelog`, `enrolments_enrolment`, `identity_scopegrant`, `reporting_alert`.

| Campo | Tipo | Nulo | Defecto | Clave | Descripción y regla | Clasif. |
| --- | --- | --- | --- | --- | --- | --- |
| `id` | `bigint` | No | Autogenerado | PK | Identificador interno secuencial. Clave primaria. | Interno |
| `public_id` | `uuid` | No | UUID aleatorio | UQ | Identificador público opaco que expone la API. Único, no editable. | Interno |
| `created_at` | `timestamp with time zone` | No | Al crear | — | Fecha y hora de creación del registro. | Interno |
| `updated_at` | `timestamp with time zone` | No | Al guardar | — | Fecha y hora de la última modificación. | Interno |
| `is_active` | `boolean` | No | `true` | — | Vigencia del registro; `false` equivale a baja lógica. | Interno |
| `name` | `character varying(50)` | No | — | — | Nombre de la sección (A, B, etc.). Único por oferta. | Interno |
| `capacity` | `integer` | No | `0` | — | Cupo máximo de estudiantes de la sección. No negativo. | Interno |
| `offering_id` | `bigint` | No | — | FK → `academics_gradeoffering.id` (CASCADE) | Oferta de grado a la que pertenece la sección. | Interno |
| `default_classroom_id` | `bigint` | Sí | — | FK → `academics_classroom.id` (PROTECT) | Aula habitual de referencia para las clases de la sección. Opcional. | Interno |

Restricciones e índices:

| Tipo | Nombre | Definición | Regla |
| --- | --- | --- | --- |
| Única compuesta | `unique_section_name_per_offering` | `offering_id`, `name` | El nombre de sección no se repite dentro de una oferta de grado. |

### `academics_shift` — Jornada

Turno de trabajo de una sede: matutina, vespertina o nocturna.

- **Clasificación:** Interno.
- **Historia:** Baja lógica con `is_active`; no se elimina físicamente.
- **La referencian:** `academics_classscheduleblock`, `academics_gradeoffering`, `attendance_attendancealert`, `attendance_attendanceevent`, `attendance_jornadaparameters`, `reporting_absencethresholdparameters`, `reporting_alert`.

| Campo | Tipo | Nulo | Defecto | Clave | Descripción y regla | Clasif. |
| --- | --- | --- | --- | --- | --- | --- |
| `id` | `bigint` | No | Autogenerado | PK | Identificador interno secuencial. Clave primaria. | Interno |
| `public_id` | `uuid` | No | UUID aleatorio | UQ | Identificador público opaco que expone la API. Único, no editable. | Interno |
| `created_at` | `timestamp with time zone` | No | Al crear | — | Fecha y hora de creación del registro. | Interno |
| `updated_at` | `timestamp with time zone` | No | Al guardar | — | Fecha y hora de la última modificación. | Interno |
| `is_active` | `boolean` | No | `true` | — | Vigencia del registro; `false` equivale a baja lógica. | Interno |
| `name` | `character varying(100)` | No | — | — | Nombre de la jornada. | Interno |
| `code` | `character varying(30)` | No | — | — | Código de la jornada. Único por sede. | Interno |
| `campus_id` | `bigint` | No | — | FK → `academics_campus.id` (CASCADE) | Sede a la que pertenece. | Interno |

Restricciones e índices:

| Tipo | Nombre | Definición | Regla |
| --- | --- | --- | --- |
| Única compuesta | `unique_shift_code_per_campus` | `campus_id`, `code` | El código de jornada no se repite en una sede. |

### `academics_subject` — Curso

Curso o subárea que se imparte en uno o más niveles.

- **Clasificación:** Interno.
- **Historia:** Baja lógica con `is_active`; no se elimina físicamente.
- **La referencian:** `academics_classsession`, `academics_curriculumplan`, `academics_frozensubjectresult`, `academics_levelsubject`, `academics_teachingassignment`, `evaluation_captureexceptiongrant`, `evaluation_grade`, `evaluation_recoverygrade`, `identity_scopegrant`.

| Campo | Tipo | Nulo | Defecto | Clave | Descripción y regla | Clasif. |
| --- | --- | --- | --- | --- | --- | --- |
| `id` | `bigint` | No | Autogenerado | PK | Identificador interno secuencial. Clave primaria. | Interno |
| `public_id` | `uuid` | No | UUID aleatorio | UQ | Identificador público opaco que expone la API. Único, no editable. | Interno |
| `created_at` | `timestamp with time zone` | No | Al crear | — | Fecha y hora de creación del registro. | Interno |
| `updated_at` | `timestamp with time zone` | No | Al guardar | — | Fecha y hora de la última modificación. | Interno |
| `is_active` | `boolean` | No | `true` | — | Vigencia del registro; `false` equivale a baja lógica. | Interno |
| `name` | `character varying(150)` | No | — | — | Nombre del curso. | Interno |
| `code` | `character varying(50)` | No | — | — | Código del curso. Único por institución. | Interno |
| `institution_id` | `bigint` | No | — | FK → `academics_institution.id` (CASCADE) | Institución a la que pertenece. | Interno |

Restricciones e índices:

| Tipo | Nombre | Definición | Regla |
| --- | --- | --- | --- |
| Única compuesta | `unique_subject_code_per_institution` | `institution_id`, `code` | El código de curso no se repite en una institución. |

### `academics_teachingassignment` — Asignación docente

Docente responsable de un curso en una sección durante un periodo del ciclo. Determina el alcance derivado del docente.

- **Clasificación:** Restringido.
- **Historia:** La reasignación cierra la fila con `ends_on` y crea otra; la historia se conserva.
- **La referencian:** `identity_scopegrant`.

| Campo | Tipo | Nulo | Defecto | Clave | Descripción y regla | Clasif. |
| --- | --- | --- | --- | --- | --- | --- |
| `id` | `bigint` | No | Autogenerado | PK | Identificador interno secuencial. Clave primaria. | Restringido |
| `public_id` | `uuid` | No | UUID aleatorio | UQ | Identificador público opaco que expone la API. Único, no editable. | Restringido |
| `created_at` | `timestamp with time zone` | No | Al crear | — | Fecha y hora de creación del registro. | Restringido |
| `updated_at` | `timestamp with time zone` | No | Al guardar | — | Fecha y hora de la última modificación. | Restringido |
| `is_active` | `boolean` | No | `true` | — | Vigencia del registro; `false` equivale a baja lógica. | Restringido |
| `starts_on` | `date` | No | Fecha actual | — | Fecha de inicio de la asignación. | Restringido |
| `ends_on` | `date` | Sí | — | — | Fecha de fin de la asignación; vacía si sigue vigente. | Restringido |
| `academic_cycle_id` | `bigint` | No | — | FK → `academics_academiccycle.id` (CASCADE) | Ciclo escolar al que pertenece. | Restringido |
| `section_id` | `bigint` | No | — | FK → `academics_section.id` (CASCADE) | Sección a la que corresponde. | Restringido |
| `subject_id` | `bigint` | No | — | FK → `academics_subject.id` (CASCADE) | Curso al que corresponde. | Restringido |
| `teacher_id` | `bigint` | No | — | FK → `people_person.id` (PROTECT) | Persona del docente asignado. | Restringido |

Restricciones e índices:

| Tipo | Nombre | Definición | Regla |
| --- | --- | --- | --- |
| Verificación | `teaching_assignment_valid_dates` | `CHECK (((ends_on IS NULL) OR (starts_on <= ends_on)))` | El inicio de la asignación no puede ser posterior a su fin. |
| Única compuesta | `academics_teachingassign_academic_cycle_id_sectio_bc374c60_uniq` | `academic_cycle_id`, `section_id`, `subject_id`, `teacher_id`, `starts_on` | La combinación no se repite. |
| Exclusión | `teaching_assignment_no_overlapping_period` | `EXCLUDE USING gist (academic_cycle_id WITH =, section_id WITH =, subject_id WITH =, daterange(starts_on, ends_on, '[]'::text) WITH &&)` | Un curso de una sección no puede tener dos asignaciones docentes con fechas traslapadas. |

## 10. Matrícula

Matrículas, requisitos documentales y movimientos del estudiante.

### `enrolments_enrolment` — Matrícula

Inscripción de un estudiante en un ciclo, grado y sección, con su vigencia y estado. Un estudiante solo puede tener una matrícula activa.

- **Clasificación:** Restringido.
- **Historia:** No se elimina: termina con `status` y `ends_on`.
- **La referencian:** `academics_frozenpromotionresult`, `academics_frozensubjectresult`, `documents_documentrecord`, `enrolments_enrolmentdocumentrequirement`, `enrolments_studentmovement`, `evaluation_grade`, `evaluation_recoverygrade`.

| Campo | Tipo | Nulo | Defecto | Clave | Descripción y regla | Clasif. |
| --- | --- | --- | --- | --- | --- | --- |
| `id` | `bigint` | No | Autogenerado | PK | Identificador interno secuencial. Clave primaria. | Restringido |
| `public_id` | `uuid` | No | UUID aleatorio | UQ | Identificador público opaco que expone la API. Único, no editable. | Restringido |
| `created_at` | `timestamp with time zone` | No | Al crear | — | Fecha y hora de creación del registro. | Restringido |
| `updated_at` | `timestamp with time zone` | No | Al guardar | — | Fecha y hora de la última modificación. | Restringido |
| `is_active` | `boolean` | No | `true` | — | Vigencia del registro; `false` equivale a baja lógica. | Restringido |
| `effective_on` | `date` | No | Fecha actual | — | Fecha desde la que rige la matrícula. | Restringido |
| `ends_on` | `date` | Sí | — | — | Fecha de fin de la matrícula; vacía si sigue vigente. | Restringido |
| `status` | `character varying(20)` | No | `active` | — | Estado de la matrícula. Valores: `active`, `withdrawn`, `completed`, `cancelled`. | Restringido |
| `academic_cycle_id` | `bigint` | No | — | FK → `academics_academiccycle.id` (PROTECT) | Ciclo escolar de la matrícula. | Restringido |
| `grade_id` | `bigint` | No | — | FK → `academics_grade.id` (PROTECT) | Grado en el que se matricula. | Restringido |
| `section_id` | `bigint` | No | — | FK → `academics_section.id` (PROTECT) | Sección asignada. | Restringido |
| `student_id` | `bigint` | No | — | FK → `students_student.id` (PROTECT) | Estudiante matriculado. | Restringido |

Restricciones e índices:

| Tipo | Nombre | Definición | Regla |
| --- | --- | --- | --- |
| Verificación | `enrolment_valid_effective_dates` | `CHECK (((ends_on IS NULL) OR (effective_on <= ends_on)))` | El inicio de la matrícula no puede ser posterior a su fin. |
| Única compuesta | `unique_enrolment_per_student_section` | `student_id`, `section_id` | Un estudiante no se matricula dos veces en la misma sección. |
| Única parcial | `unique_active_enrolment_per_student` | `btree (student_id) WHERE ((status)::text = 'active'::text)` | Una sola matrícula activa por estudiante. |

### `enrolments_enrolmentdocumentrequirement` — Requisito documental de matrícula

Documento que la matrícula debe presentar y su estado de entrega.

- **Clasificación:** Restringido.
- **Historia:** Baja lógica con `is_active`; no se elimina físicamente.

| Campo | Tipo | Nulo | Defecto | Clave | Descripción y regla | Clasif. |
| --- | --- | --- | --- | --- | --- | --- |
| `id` | `bigint` | No | Autogenerado | PK | Identificador interno secuencial. Clave primaria. | Restringido |
| `public_id` | `uuid` | No | UUID aleatorio | UQ | Identificador público opaco que expone la API. Único, no editable. | Restringido |
| `created_at` | `timestamp with time zone` | No | Al crear | — | Fecha y hora de creación del registro. | Restringido |
| `updated_at` | `timestamp with time zone` | No | Al guardar | — | Fecha y hora de la última modificación. | Restringido |
| `is_active` | `boolean` | No | `true` | — | Vigencia del registro; `false` equivale a baja lógica. | Restringido |
| `code` | `character varying(50)` | No | — | — | Código del requisito. Único por matrícula. | Restringido |
| `name` | `character varying(150)` | No | — | — | Nombre del documento requerido. | Restringido |
| `is_required` | `boolean` | No | `true` | — | Indica si es obligatorio. | Restringido |
| `status` | `character varying(20)` | No | `pending` | — | Estado de entrega del requisito. Valores: `pending`, `delivered`. | Restringido |
| `enrolment_id` | `bigint` | No | — | FK → `enrolments_enrolment.id` (PROTECT) | Matrícula a la que pertenece el requisito. | Restringido |

Restricciones e índices:

| Tipo | Nombre | Definición | Regla |
| --- | --- | --- | --- |
| Única compuesta | `unique_document_requirement_per_enrolment` | `enrolment_id`, `code` | El código de requisito no se repite en una matrícula. |

### `enrolments_studentmovement` — Movimiento del estudiante

Cambio de sección, traslado de entrada o salida, o retiro, con fecha efectiva y matrículas de origen y destino.

- **Clasificación:** Restringido.
- **Historia:** No se edita ni se borra: un movimiento erróneo se anula con una fila de anulación.
- **La referencian:** `attendance_studentcredential`, `enrolments_studentmovementannulment`.

| Campo | Tipo | Nulo | Defecto | Clave | Descripción y regla | Clasif. |
| --- | --- | --- | --- | --- | --- | --- |
| `id` | `bigint` | No | Autogenerado | PK | Identificador interno secuencial. Clave primaria. | Restringido |
| `public_id` | `uuid` | No | UUID aleatorio | UQ | Identificador público opaco que expone la API. Único, no editable. | Restringido |
| `created_at` | `timestamp with time zone` | No | Al crear | — | Fecha y hora de creación del registro. | Restringido |
| `updated_at` | `timestamp with time zone` | No | Al guardar | — | Fecha y hora de la última modificación. | Restringido |
| `is_active` | `boolean` | No | `true` | — | Vigencia del registro; `false` equivale a baja lógica. | Restringido |
| `movement_type` | `character varying(30)` | No | — | — | Tipo de movimiento. Valores: `section_change`, `transfer_in`, `transfer_out`, `withdrawal`. | Restringido |
| `effective_on` | `date` | No | Fecha actual | — | Fecha efectiva del movimiento. | Restringido |
| `source_enrolment_id` | `bigint` | Sí | — | FK → `enrolments_enrolment.id` (PROTECT) | Matrícula de origen. Obligatoria o vacía según el tipo de movimiento. | Restringido |
| `student_id` | `bigint` | No | — | FK → `students_student.id` (PROTECT) | Estudiante al que pertenece el registro. | Restringido |
| `target_enrolment_id` | `bigint` | Sí | — | FK → `enrolments_enrolment.id` (PROTECT) | Matrícula de destino. Obligatoria o vacía según el tipo de movimiento. | Restringido |
| `reason` | `text` | No | Vacío | — | Motivo del movimiento. Obligatorio en los retiros. | Restringido |

Restricciones e índices:

| Tipo | Nombre | Definición | Regla |
| --- | --- | --- | --- |
| Verificación | `student_movement_distinct_enrolments` | `CHECK (((source_enrolment_id IS NULL) OR (target_enrolment_id IS NULL) OR (NOT ((source_enrolment_id = target_enrolment_id) AND (source_enrolment_id IS NOT NULL) AND (target_enrolment_id IS NOT NULL)))))` | La matrícula de origen y la de destino deben ser distintas. |
| Verificación | `student_movement_valid_enrolment_shape` | `CHECK (((((movement_type)::text = 'section_change'::text) AND (source_enrolment_id IS NOT NULL) AND (target_enrolment_id IS NOT NULL)) OR (((movement_type)::text = 'transfer_in'::text) AND (source_enrolment_id IS NULL) AND (target_enrolment_id IS NOT NULL)) OR (((movement_type)::text = 'transfer_out'::text) AND (source_enrolment_id IS NOT NULL) AND (target_enrolment_id IS NULL)) OR (((movement_type)::text = 'withdrawal'::text) AND (source_enrolment_id IS NOT NULL) AND (target_enrolment_id IS NULL))))` | Cada tipo de movimiento exige la combinación correcta de matrícula de origen y de destino. |
| Verificación | `student_withdrawal_requires_reason` | `CHECK (((NOT ((movement_type)::text = 'withdrawal'::text)) OR (NOT (reason = ''::text))))` | Todo retiro exige motivo. |

### `enrolments_studentmovementannulment` — Anulación de movimiento

Deja sin efecto un movimiento, con motivo obligatorio y responsable.

- **Clasificación:** Restringido.
- **Historia:** Solo inserción: no se edita ni se elimina.

| Campo | Tipo | Nulo | Defecto | Clave | Descripción y regla | Clasif. |
| --- | --- | --- | --- | --- | --- | --- |
| `id` | `bigint` | No | Autogenerado | PK | Identificador interno secuencial. Clave primaria. | Restringido |
| `public_id` | `uuid` | No | UUID aleatorio | UQ | Identificador público opaco que expone la API. Único, no editable. | Restringido |
| `created_at` | `timestamp with time zone` | No | Al crear | — | Fecha y hora de creación del registro. | Restringido |
| `updated_at` | `timestamp with time zone` | No | Al guardar | — | Fecha y hora de la última modificación. | Restringido |
| `is_active` | `boolean` | No | `true` | — | Vigencia del registro; `false` equivale a baja lógica. | Restringido |
| `reason` | `text` | No | — | — | Motivo de la anulación. Obligatorio. | Restringido |
| `annulled_by_id` | `bigint` | No | — | FK → `identity_useraccount.id` (PROTECT) | Cuenta que anuló el movimiento. | Restringido |
| `movement_id` | `bigint` | No | — | FK → `enrolments_studentmovement.id` (PROTECT); UQ | Movimiento anulado. Relación 1:1. | Restringido |

Restricciones e índices:

| Tipo | Nombre | Definición | Regla |
| --- | --- | --- | --- |
| Verificación | `student_movement_annulment_requires_reason` | `CHECK ((NOT (reason = ''::text)))` | Toda anulación exige motivo. |

## 11. Asistencia y credencial

Credencial QR, captura de eventos, cierres, justificaciones y permisos.

### `attendance_attendancealert` — Alerta de asistencia

Alerta generada por la asistencia, como una permanencia sin salida registrada o eventos contradictorios en la misma jornada.

- **Clasificación:** Restringido.
- **Historia:** Solo inserción: no se edita ni se elimina.
- **La referencian:** `reporting_alert`.

| Campo | Tipo | Nulo | Defecto | Clave | Descripción y regla | Clasif. |
| --- | --- | --- | --- | --- | --- | --- |
| `id` | `bigint` | No | Autogenerado | PK | Identificador interno secuencial. Clave primaria. | Restringido |
| `public_id` | `uuid` | No | UUID aleatorio | UQ | Identificador público opaco que expone la API. Único, no editable. | Restringido |
| `created_at` | `timestamp with time zone` | No | Al crear | — | Fecha y hora de creación del registro. | Restringido |
| `updated_at` | `timestamp with time zone` | No | Al guardar | — | Fecha y hora de la última modificación. | Restringido |
| `is_active` | `boolean` | No | `true` | — | Vigencia del registro; `false` equivale a baja lógica. | Restringido |
| `alert_type` | `character varying(30)` | No | — | — | Tipo de alerta. Valores: `permanencia_sin_cierre`, `inconsistencia`. | Restringido |
| `event_date` | `date` | No | — | — | Fecha lectiva a la que corresponde. | Restringido |
| `target_roles` | `jsonb` | No | `[]` | — | Lista de roles a los que se dirige la alerta. | Restringido |
| `context` | `jsonb` | No | `{}` | — | Datos adicionales de contexto en JSON. | Restringido |
| `section_id` | `bigint` | Sí | — | FK → `academics_section.id` (PROTECT) | Sección del estudiante al generarse la alerta. Opcional. | Restringido |
| `shift_id` | `bigint` | No | — | FK → `academics_shift.id` (PROTECT) | Jornada a la que corresponde. | Restringido |
| `student_id` | `bigint` | No | — | FK → `students_student.id` (PROTECT) | Estudiante al que pertenece el registro. | Restringido |

Restricciones e índices:

| Tipo | Nombre | Definición | Regla |
| --- | --- | --- | --- |
| Índice | `attendance_alert_lookup_idx` | `btree (student_id, shift_id, event_date, alert_type)` | Acelera la búsqueda de alertas por estudiante, jornada y fecha. |

### `attendance_attendanceevent` — Evento de asistencia

Movimiento de entrada o salida de un estudiante en una jornada y fecha. Es la fuente de la que se calcula el estado del día.

- **Clasificación:** Restringido.
- **Historia:** Solo inserción: nunca se borra ni se sobrescribe, aunque un evento posterior tenga precedencia.

| Campo | Tipo | Nulo | Defecto | Clave | Descripción y regla | Clasif. |
| --- | --- | --- | --- | --- | --- | --- |
| `id` | `bigint` | No | Autogenerado | PK | Identificador interno secuencial. Clave primaria. | Restringido |
| `public_id` | `uuid` | No | UUID aleatorio | UQ | Identificador público opaco que expone la API. Único, no editable. | Restringido |
| `created_at` | `timestamp with time zone` | No | Al crear | — | Fecha y hora de creación del registro. | Restringido |
| `updated_at` | `timestamp with time zone` | No | Al guardar | — | Fecha y hora de la última modificación. | Restringido |
| `is_active` | `boolean` | No | `true` | — | Vigencia del registro; `false` equivale a baja lógica. | Restringido |
| `event_date` | `date` | No | — | — | Fecha lectiva a la que corresponde. | Restringido |
| `movement_type` | `character varying(10)` | No | — | — | Tipo de movimiento: entrada o salida. Valores: `entry`, `exit`. | Restringido |
| `origin` | `character varying(10)` | No | — | — | Origen del evento: escaneo, registro manual o declarado en un cierre. Valores: `scan`, `manual`, `declared`. | Restringido |
| `transmission` | `character varying(12)` | No | `individual` | — | Forma de envío: individual o por lote. Valores: `individual`, `batch`. | Restringido |
| `captured_at` | `timestamp with time zone` | No | — | — | Momento real de la captura. | Restringido |
| `shift_id` | `bigint` | No | — | FK → `academics_shift.id` (PROTECT) | Jornada a la que corresponde. | Restringido |
| `student_id` | `bigint` | No | — | FK → `students_student.id` (PROTECT) | Estudiante al que pertenece el registro. | Restringido |
| `batch_id` | `character varying(100)` | No | Vacío | — | Identificador de lote enviado por el cliente. Opcional. | Restringido |
| `client_event_id` | `character varying(100)` | No | Vacío | — | Identificador del evento generado por el cliente. Hace idempotente el reintento sin conexión. | Restringido |
| `operator_id` | `bigint` | Sí | — | FK → `identity_useraccount.id` (PROTECT) | Cuenta del operador que realizó la captura. | Restringido |
| `control_point_id` | `bigint` | Sí | — | FK → `attendance_controlpoint.id` (PROTECT) | Punto de control donde se capturó. Opcional. | Restringido |
| `manual_reason_id` | `bigint` | Sí | — | FK → `attendance_manualregistrationreason.id` (PROTECT) | Motivo del registro manual, cuando el origen es manual. | Restringido |
| `capture_batch_id` | `bigint` | Sí | — | FK → `attendance_capturebatch.id` (PROTECT) | Lote de captura al que pertenece. Opcional. | Restringido |

Restricciones e índices:

| Tipo | Nombre | Definición | Regla |
| --- | --- | --- | --- |
| Índice | `attendance_event_prec_idx` | `btree (student_id, shift_id, event_date, movement_type)` | Acelera la resolución del evento vigente de un estudiante en una jornada y fecha. |
| Única parcial | `unique_attendance_event_client_event_id` | `btree (client_event_id) WHERE (NOT ((client_event_id)::text = ''::text))` | Un mismo evento enviado por el cliente no se registra dos veces (idempotencia sin conexión). |

### `attendance_attendancepermit` — Permiso de asistencia

Solicitud anticipada de un encargado para autorizar una salida temprana o una llegada tardía en una fecha, y su resolución.

- **Clasificación:** Restringido.
- **Historia:** No se elimina: se resuelve como aprobado o rechazado.

| Campo | Tipo | Nulo | Defecto | Clave | Descripción y regla | Clasif. |
| --- | --- | --- | --- | --- | --- | --- |
| `id` | `bigint` | No | Autogenerado | PK | Identificador interno secuencial. Clave primaria. | Restringido |
| `public_id` | `uuid` | No | UUID aleatorio | UQ | Identificador público opaco que expone la API. Único, no editable. | Restringido |
| `created_at` | `timestamp with time zone` | No | Al crear | — | Fecha y hora de creación del registro. | Restringido |
| `updated_at` | `timestamp with time zone` | No | Al guardar | — | Fecha y hora de la última modificación. | Restringido |
| `is_active` | `boolean` | No | `true` | — | Vigencia del registro; `false` equivale a baja lógica. | Restringido |
| `permit_type` | `character varying(15)` | No | — | — | Tipo de permiso: salida temprana o llegada tardía. Valores: `early_exit`, `late_arrival`. | Restringido |
| `permit_date` | `date` | No | — | — | Fecha para la que se solicita el permiso. | Restringido |
| `scheduled_time` | `time without time zone` | No | — | — | Hora prevista del hecho. | Restringido |
| `reason` | `text` | No | — | — | Explicación del encargado. | Restringido |
| `status` | `character varying(10)` | No | `pending` | — | Estado de la solicitud. Valores: `pending`, `approved`, `rejected`. | Restringido |
| `resolved_at` | `timestamp with time zone` | Sí | — | — | Momento de la resolución; vacío si está pendiente. | Restringido |
| `resolution_comment` | `text` | No | Vacío | — | Comentario de quien resolvió. | Restringido |
| `resolved_by_id` | `bigint` | Sí | — | FK → `identity_useraccount.id` (PROTECT) | Cuenta que resolvió la solicitud; vacía si está pendiente. | Restringido |
| `student_id` | `bigint` | No | — | FK → `students_student.id` (PROTECT) | Estudiante al que pertenece el registro. | Restringido |
| `submitted_by_id` | `bigint` | No | — | FK → `identity_useraccount.id` (PROTECT) | Cuenta del encargado que presentó la solicitud. | Restringido |

### `attendance_capturebatch` — Lote de captura

Grupo de movimientos escaneados por un operador que permanece abierto entre sesiones y dispositivos hasta que lo confirma.

- **Clasificación:** Restringido.
- **Historia:** No se elimina: se confirma o cierra. Un solo lote abierto por operador.
- **La referencian:** `attendance_attendanceevent`.

| Campo | Tipo | Nulo | Defecto | Clave | Descripción y regla | Clasif. |
| --- | --- | --- | --- | --- | --- | --- |
| `id` | `bigint` | No | Autogenerado | PK | Identificador interno secuencial. Clave primaria. | Restringido |
| `public_id` | `uuid` | No | UUID aleatorio | UQ | Identificador público opaco que expone la API. Único, no editable. | Restringido |
| `created_at` | `timestamp with time zone` | No | Al crear | — | Fecha y hora de creación del registro. | Restringido |
| `updated_at` | `timestamp with time zone` | No | Al guardar | — | Fecha y hora de la última modificación. | Restringido |
| `is_active` | `boolean` | No | `true` | — | Vigencia del registro; `false` equivale a baja lógica. | Restringido |
| `status` | `character varying(10)` | No | `open` | — | Estado del lote: abierto o confirmado. Valores: `open`, `confirmed`. | Restringido |
| `confirmed_at` | `timestamp with time zone` | Sí | — | — | Momento en que el operador confirmó el lote. | Restringido |
| `operator_id` | `bigint` | No | — | FK → `identity_useraccount.id` (PROTECT) | Cuenta del operador que realizó la captura. | Restringido |
| `closed_at` | `timestamp with time zone` | Sí | — | — | Momento de cierre del lote. | Restringido |
| `session_key` | `character varying(64)` | No | Vacío | — | Clave de la sesión en la que se abrió el lote. | Restringido |

Restricciones e índices:

| Tipo | Nombre | Definición | Regla |
| --- | --- | --- | --- |
| Única parcial | `unique_open_capture_batch_per_operator` | `btree (operator_id) WHERE ((status)::text = 'open'::text)` | Un solo lote de captura abierto por operador. |

### `attendance_controlpoint` — Punto de control

Lugar físico donde se capturan los escaneos (portón, entrada) y qué tipos de movimiento admite.

- **Clasificación:** Interno.
- **Historia:** Catálogo: se retira con `is_active = false` para no romper referencias históricas.
- **La referencian:** `attendance_attendanceevent`.

| Campo | Tipo | Nulo | Defecto | Clave | Descripción y regla | Clasif. |
| --- | --- | --- | --- | --- | --- | --- |
| `id` | `bigint` | No | Autogenerado | PK | Identificador interno secuencial. Clave primaria. | Interno |
| `public_id` | `uuid` | No | UUID aleatorio | UQ | Identificador público opaco que expone la API. Único, no editable. | Interno |
| `created_at` | `timestamp with time zone` | No | Al crear | — | Fecha y hora de creación del registro. | Interno |
| `updated_at` | `timestamp with time zone` | No | Al guardar | — | Fecha y hora de la última modificación. | Interno |
| `is_active` | `boolean` | No | `true` | — | Vigencia del registro; `false` equivale a baja lógica. | Interno |
| `name` | `character varying(100)` | No | — | — | Nombre del punto de control. | Interno |
| `code` | `character varying(30)` | No | — | — | Código del punto de control. Único por sede. | Interno |
| `campus_id` | `bigint` | No | — | FK → `academics_campus.id` (PROTECT) | Sede a la que pertenece. | Interno |
| `allows_entry` | `boolean` | No | `true` | — | Indica si admite registrar entradas. | Interno |
| `allows_exit` | `boolean` | No | `true` | — | Indica si admite registrar salidas. | Interno |

Restricciones e índices:

| Tipo | Nombre | Definición | Regla |
| --- | --- | --- | --- |
| Única compuesta | `unique_control_point_code_per_campus` | `campus_id`, `code` | El código de punto de control no se repite en una sede. |

### `attendance_jornadaparameters` — Parámetros de jornada

Hora límite de ingreso, tolerancia, hora de cierre, supresión de duplicados y días lectivos de una jornada en un ciclo.

- **Clasificación:** Interno.
- **Historia:** Versionado por vigencia: un cambio crea una fila nueva y conserva las anteriores.

| Campo | Tipo | Nulo | Defecto | Clave | Descripción y regla | Clasif. |
| --- | --- | --- | --- | --- | --- | --- |
| `id` | `bigint` | No | Autogenerado | PK | Identificador interno secuencial. Clave primaria. | Interno |
| `public_id` | `uuid` | No | UUID aleatorio | UQ | Identificador público opaco que expone la API. Único, no editable. | Interno |
| `created_at` | `timestamp with time zone` | No | Al crear | — | Fecha y hora de creación del registro. | Interno |
| `updated_at` | `timestamp with time zone` | No | Al guardar | — | Fecha y hora de la última modificación. | Interno |
| `is_active` | `boolean` | No | `true` | — | Vigencia del registro; `false` equivale a baja lógica. | Interno |
| `entry_limit_time` | `time without time zone` | No | — | — | Hora límite de ingreso puntual. | Interno |
| `tolerance_minutes` | `integer` | No | — | — | Minutos de tolerancia tras la hora límite. No negativo. | Interno |
| `closing_time` | `time without time zone` | No | — | — | Hora de cierre de la jornada. | Interno |
| `duplicate_suppression_minutes` | `integer` | No | — | — | Minutos durante los que un escaneo repetido se registra como rechazo y no como movimiento. No negativo. | Interno |
| `school_days` | `jsonb` | No | `[]` | — | Días de la semana lectivos, en JSON. | Interno |
| `effective_from` | `date` | No | — | — | Fecha desde la que rige esta versión de los parámetros. | Interno |
| `academic_cycle_id` | `bigint` | No | — | FK → `academics_academiccycle.id` (PROTECT) | Ciclo escolar al que pertenece. | Interno |
| `shift_id` | `bigint` | No | — | FK → `academics_shift.id` (PROTECT) | Jornada a la que corresponde. | Interno |

Restricciones e índices:

| Tipo | Nombre | Definición | Regla |
| --- | --- | --- | --- |
| Única compuesta | `unique_jornada_parameters_effective_from` | `shift_id`, `academic_cycle_id`, `effective_from` | Una sola versión de parámetros por jornada, ciclo y fecha de vigencia. |
| Índice | `attendance_params_lookup_idx` | `btree (shift_id, academic_cycle_id, effective_from)` | Acelera la búsqueda de los parámetros vigentes de una jornada y ciclo. |

### `attendance_justification` — Justificación

Solicitud de un encargado para justificar la ausencia o llegada tardía de un estudiante en una fecha, y su resolución.

- **Clasificación:** Sensible especial.
- **Historia:** No se elimina: se resuelve como aprobada o rechazada y conserva quién y cuándo.
- **La referencian:** `attendance_justificationattachment`, `attendance_justificationnotification`.

| Campo | Tipo | Nulo | Defecto | Clave | Descripción y regla | Clasif. |
| --- | --- | --- | --- | --- | --- | --- |
| `id` | `bigint` | No | Autogenerado | PK | Identificador interno secuencial. Clave primaria. | Sensible especial |
| `public_id` | `uuid` | No | UUID aleatorio | UQ | Identificador público opaco que expone la API. Único, no editable. | Sensible especial |
| `created_at` | `timestamp with time zone` | No | Al crear | — | Fecha y hora de creación del registro. | Sensible especial |
| `updated_at` | `timestamp with time zone` | No | Al guardar | — | Fecha y hora de la última modificación. | Sensible especial |
| `is_active` | `boolean` | No | `true` | — | Vigencia del registro; `false` equivale a baja lógica. | Sensible especial |
| `absence_date` | `date` | No | — | — | Fecha de la ausencia o llegada tardía que se justifica. | Sensible especial |
| `reason` | `text` | No | — | — | Explicación del encargado. Puede contener información sensible. | Sensible especial |
| `status` | `character varying(10)` | No | `pending` | — | Estado de la solicitud. Valores: `pending`, `approved`, `rejected`. | Sensible especial |
| `is_exception` | `boolean` | No | `false` | — | Indica que se aceptó fuera del plazo ordinario. | Sensible especial |
| `exception_reason` | `character varying(255)` | No | Vacío | — | Motivo por el que se admitió la excepción de plazo. | Sensible especial |
| `student_id` | `bigint` | No | — | FK → `students_student.id` (PROTECT) | Estudiante al que pertenece el registro. | Sensible especial |
| `submitted_by_id` | `bigint` | No | — | FK → `identity_useraccount.id` (PROTECT) | Cuenta del encargado que presentó la solicitud. | Sensible especial |
| `resolution_comment` | `text` | No | Vacío | — | Comentario de quien resolvió. | Sensible especial |
| `resolved_at` | `timestamp with time zone` | Sí | — | — | Momento de la resolución; vacío si está pendiente. | Sensible especial |
| `resolved_by_id` | `bigint` | Sí | — | FK → `identity_useraccount.id` (PROTECT) | Cuenta que resolvió la solicitud; vacía si está pendiente. | Sensible especial |
| `situation_type` | `character varying(15)` | No | `absence` | — | Situación que se justifica: ausencia o llegada tardía. Valores: `absence`, `late_arrival`. | Sensible especial |
| `reason_catalog_id` | `bigint` | Sí | — | FK → `attendance_justificationreason.id` (PROTECT) | Motivo del catálogo elegido por el encargado. Opcional. | Sensible especial |

### `attendance_justificationattachment` — Adjunto de justificación

Metadatos del documento de respaldo de una justificación (por ejemplo, una constancia médica). El archivo vive fuera de la base.

- **Clasificación:** Sensible especial.
- **Historia:** Se conserva junto con la justificación.

| Campo | Tipo | Nulo | Defecto | Clave | Descripción y regla | Clasif. |
| --- | --- | --- | --- | --- | --- | --- |
| `id` | `bigint` | No | Autogenerado | PK | Identificador interno secuencial. Clave primaria. | Sensible especial |
| `public_id` | `uuid` | No | UUID aleatorio | UQ | Identificador público opaco que expone la API. Único, no editable. | Sensible especial |
| `created_at` | `timestamp with time zone` | No | Al crear | — | Fecha y hora de creación del registro. | Sensible especial |
| `updated_at` | `timestamp with time zone` | No | Al guardar | — | Fecha y hora de la última modificación. | Sensible especial |
| `is_active` | `boolean` | No | `true` | — | Vigencia del registro; `false` equivale a baja lógica. | Sensible especial |
| `filename` | `character varying(255)` | No | — | — | Nombre original del archivo, normalizado. | Sensible especial |
| `storage_key` | `character varying(500)` | No | — | UQ | Ruta del archivo en el almacenamiento. Es aleatoria y no deriva del nombre original. | Sensible especial |
| `content_type` | `character varying(100)` | No | — | — | Tipo MIME declarado del archivo. | Sensible especial |
| `size_bytes` | `bigint` | No | — | — | Tamaño del archivo en bytes. No negativo. | Sensible especial |
| `checksum` | `character varying(128)` | No | — | — | Suma SHA-256 del archivo, para verificar su integridad. | Sensible especial |
| `justification_id` | `bigint` | No | — | FK → `attendance_justification.id` (CASCADE); UQ | Justificación a la que pertenece el adjunto. Relación 1:1. | Sensible especial |
| `uploaded_by_id` | `bigint` | No | — | FK → `identity_useraccount.id` (PROTECT) | Cuenta que subió el adjunto. | Sensible especial |

### `attendance_justificationnotification` — Notificación de justificación

Constancia de que el encargado fue informado de la resolución de su justificación. El sistema no envía correo ni notificaciones externas.

- **Clasificación:** Restringido.
- **Historia:** Solo inserción: no se edita ni se elimina.

| Campo | Tipo | Nulo | Defecto | Clave | Descripción y regla | Clasif. |
| --- | --- | --- | --- | --- | --- | --- |
| `id` | `bigint` | No | Autogenerado | PK | Identificador interno secuencial. Clave primaria. | Restringido |
| `public_id` | `uuid` | No | UUID aleatorio | UQ | Identificador público opaco que expone la API. Único, no editable. | Restringido |
| `created_at` | `timestamp with time zone` | No | Al crear | — | Fecha y hora de creación del registro. | Restringido |
| `updated_at` | `timestamp with time zone` | No | Al guardar | — | Fecha y hora de la última modificación. | Restringido |
| `is_active` | `boolean` | No | `true` | — | Vigencia del registro; `false` equivale a baja lógica. | Restringido |
| `justification_id` | `bigint` | No | — | FK → `attendance_justification.id` (CASCADE); UQ | Justificación cuya resolución se notificó. Relación 1:1. | Restringido |
| `recipient_id` | `bigint` | No | — | FK → `identity_useraccount.id` (PROTECT) | Cuenta del encargado notificado. | Restringido |

### `attendance_justificationpolicy` — Política de justificación

Días hábiles posteriores a una ausencia durante los que aún se admite justificarla. Fila única global.

- **Clasificación:** Interno.
- **Historia:** Fila única; se actualiza en sitio.

| Campo | Tipo | Nulo | Defecto | Clave | Descripción y regla | Clasif. |
| --- | --- | --- | --- | --- | --- | --- |
| `id` | `bigint` | No | Autogenerado | PK | Identificador interno secuencial. Clave primaria. | Interno |
| `public_id` | `uuid` | No | UUID aleatorio | UQ | Identificador público opaco que expone la API. Único, no editable. | Interno |
| `created_at` | `timestamp with time zone` | No | Al crear | — | Fecha y hora de creación del registro. | Interno |
| `updated_at` | `timestamp with time zone` | No | Al guardar | — | Fecha y hora de la última modificación. | Interno |
| `is_active` | `boolean` | No | `true` | — | Vigencia del registro; `false` equivale a baja lógica. | Interno |
| `window_business_days` | `integer` | No | `5` | — | Días hábiles tras la ausencia en que aún se admite la justificación. No negativo. | Interno |

### `attendance_justificationreason` — Motivo de justificación

Motivo configurable que el encargado elige al justificar una ausencia.

- **Clasificación:** Interno.
- **Historia:** Catálogo: se retira con `is_active = false` para no romper referencias históricas.
- **La referencian:** `attendance_justification`.

| Campo | Tipo | Nulo | Defecto | Clave | Descripción y regla | Clasif. |
| --- | --- | --- | --- | --- | --- | --- |
| `id` | `bigint` | No | Autogenerado | PK | Identificador interno secuencial. Clave primaria. | Interno |
| `public_id` | `uuid` | No | UUID aleatorio | UQ | Identificador público opaco que expone la API. Único, no editable. | Interno |
| `created_at` | `timestamp with time zone` | No | Al crear | — | Fecha y hora de creación del registro. | Interno |
| `updated_at` | `timestamp with time zone` | No | Al guardar | — | Fecha y hora de la última modificación. | Interno |
| `is_active` | `boolean` | No | `true` | — | Vigencia del registro; `false` equivale a baja lógica. | Interno |
| `name` | `character varying(100)` | No | — | — | Texto del motivo. | Interno |
| `code` | `character varying(30)` | No | — | UQ | Código del motivo. Único. | Interno |

### `attendance_manualregistrationreason` — Motivo de registro manual

Motivo configurable que justifica registrar un evento de asistencia sin escaneo.

- **Clasificación:** Interno.
- **Historia:** Catálogo: se retira con `is_active = false` para no romper referencias históricas.
- **La referencian:** `attendance_attendanceevent`.

| Campo | Tipo | Nulo | Defecto | Clave | Descripción y regla | Clasif. |
| --- | --- | --- | --- | --- | --- | --- |
| `id` | `bigint` | No | Autogenerado | PK | Identificador interno secuencial. Clave primaria. | Interno |
| `public_id` | `uuid` | No | UUID aleatorio | UQ | Identificador público opaco que expone la API. Único, no editable. | Interno |
| `created_at` | `timestamp with time zone` | No | Al crear | — | Fecha y hora de creación del registro. | Interno |
| `updated_at` | `timestamp with time zone` | No | Al guardar | — | Fecha y hora de la última modificación. | Interno |
| `is_active` | `boolean` | No | `true` | — | Vigencia del registro; `false` equivale a baja lógica. | Interno |
| `name` | `character varying(100)` | No | — | — | Texto del motivo. | Interno |
| `code` | `character varying(30)` | No | — | UQ | Código del motivo. Único. | Interno |

### `attendance_sectionclosurelog` — Bitácora de cierre de sección

Constancia de cada cierre declarado de una sección: quién lo declaró, si cubría a otro docente y cuántos estudiantes incluyó u omitió.

- **Clasificación:** Restringido.
- **Historia:** Solo inserción: no se edita ni se elimina.

| Campo | Tipo | Nulo | Defecto | Clave | Descripción y regla | Clasif. |
| --- | --- | --- | --- | --- | --- | --- |
| `id` | `bigint` | No | Autogenerado | PK | Identificador interno secuencial. Clave primaria. | Restringido |
| `public_id` | `uuid` | No | UUID aleatorio | UQ | Identificador público opaco que expone la API. Único, no editable. | Restringido |
| `created_at` | `timestamp with time zone` | No | Al crear | — | Fecha y hora de creación del registro. | Restringido |
| `updated_at` | `timestamp with time zone` | No | Al guardar | — | Fecha y hora de la última modificación. | Restringido |
| `is_active` | `boolean` | No | `true` | — | Vigencia del registro; `false` equivale a baja lógica. | Restringido |
| `event_date` | `date` | No | — | — | Fecha lectiva a la que corresponde. | Restringido |
| `is_covering` | `boolean` | No | — | — | Indica que quien declaró el cierre cubría al docente asignado. | Restringido |
| `included_count` | `integer` | No | — | — | Estudiantes incluidos en el cierre. No negativo. | Restringido |
| `omitted_count` | `integer` | No | — | — | Estudiantes omitidos en el cierre. No negativo. | Restringido |
| `declared_by_id` | `bigint` | No | — | FK → `identity_useraccount.id` (PROTECT) | Cuenta que declaró el cierre. | Restringido |
| `section_id` | `bigint` | No | — | FK → `academics_section.id` (PROTECT) | Sección a la que corresponde. | Restringido |

### `attendance_studentcredential` — Credencial del estudiante

Credencial QR del estudiante. El identificador opaco es todo el contenido del QR: se genera al azar y no deriva de ningún dato personal.

- **Clasificación:** Restringido.
- **Historia:** No se elimina: se revoca con `status`, motivo y responsable. Una sola credencial activa por estudiante.

| Campo | Tipo | Nulo | Defecto | Clave | Descripción y regla | Clasif. |
| --- | --- | --- | --- | --- | --- | --- |
| `id` | `bigint` | No | Autogenerado | PK | Identificador interno secuencial. Clave primaria. | Restringido |
| `public_id` | `uuid` | No | UUID aleatorio | UQ | Identificador público opaco que expone la API. Único, no editable. | Restringido |
| `created_at` | `timestamp with time zone` | No | Al crear | — | Fecha y hora de creación del registro. | Restringido |
| `updated_at` | `timestamp with time zone` | No | Al guardar | — | Fecha y hora de la última modificación. | Restringido |
| `is_active` | `boolean` | No | `true` | — | Vigencia del registro; `false` equivale a baja lógica. | Restringido |
| `opaque_identifier` | `character varying(64)` | No | — | UQ | Identificador aleatorio que constituye todo el contenido del QR. No contiene ni deriva de datos personales. Único. | Restringido |
| `status` | `character varying(20)` | No | `active` | — | Estado de la credencial. Valores: `active`, `revoked`. | Restringido |
| `issued_at` | `timestamp with time zone` | No | — | — | Momento de emisión de la credencial. | Restringido |
| `student_id` | `bigint` | No | — | FK → `students_student.id` (PROTECT) | Estudiante al que pertenece el registro. | Restringido |
| `revocation_reason` | `character varying(255)` | No | Vacío | — | Motivo de la revocación. | Restringido |
| `revoked_by_id` | `bigint` | Sí | — | FK → `identity_useraccount.id` (PROTECT) | Cuenta que revocó la credencial. | Restringido |
| `revoked_on_movement_id` | `bigint` | Sí | — | FK → `enrolments_studentmovement.id` (PROTECT) | Movimiento del estudiante que provocó la revocación automática, si aplica. | Restringido |

Restricciones e índices:

| Tipo | Nombre | Definición | Regla |
| --- | --- | --- | --- |
| Índice | `attendance_cred_student_idx` | `btree (student_id, status)` | Acelera la búsqueda de las credenciales de un estudiante por estado. |
| Única parcial | `unique_active_student_credential` | `btree (student_id) WHERE (is_active AND ((status)::text = 'active'::text))` | Una sola credencial activa por estudiante. |

## 12. Evaluación

Unidades, notas, recuperación y configuración.

### `evaluation_captureexceptiongrant` — Excepción de captura

Autorización excepcional y temporal para que un docente capture notas de un curso fuera de la ventana de la unidad.

- **Clasificación:** Restringido.
- **Historia:** Vence sola en `expires_at`; la fila se conserva.

| Campo | Tipo | Nulo | Defecto | Clave | Descripción y regla | Clasif. |
| --- | --- | --- | --- | --- | --- | --- |
| `id` | `bigint` | No | Autogenerado | PK | Identificador interno secuencial. Clave primaria. | Restringido |
| `public_id` | `uuid` | No | UUID aleatorio | UQ | Identificador público opaco que expone la API. Único, no editable. | Restringido |
| `created_at` | `timestamp with time zone` | No | Al crear | — | Fecha y hora de creación del registro. | Restringido |
| `updated_at` | `timestamp with time zone` | No | Al guardar | — | Fecha y hora de la última modificación. | Restringido |
| `is_active` | `boolean` | No | `true` | — | Vigencia del registro; `false` equivale a baja lógica. | Restringido |
| `reason` | `text` | No | — | — | Justificación obligatoria de la excepción. | Restringido |
| `expires_at` | `timestamp with time zone` | No | — | — | Momento en que la excepción vence automáticamente. | Restringido |
| `evaluation_unit_id` | `bigint` | No | — | FK → `evaluation_evaluationunit.id` (CASCADE) | Unidad a la que aplica la excepción. | Restringido |
| `subject_id` | `bigint` | No | — | FK → `academics_subject.id` (PROTECT) | Curso al que se limita la excepción. | Restringido |
| `teacher_id` | `bigint` | No | — | FK → `people_person.id` (PROTECT) | Persona del docente autorizado. | Restringido |

### `evaluation_cycleevaluationconfig` — Configuración de evaluación del ciclo

Ajuste de la cantidad de unidades para un ciclo, sin alterar la configuración global.

- **Clasificación:** Interno.
- **Historia:** Baja lógica con `is_active`; no se elimina físicamente.

| Campo | Tipo | Nulo | Defecto | Clave | Descripción y regla | Clasif. |
| --- | --- | --- | --- | --- | --- | --- |
| `id` | `bigint` | No | Autogenerado | PK | Identificador interno secuencial. Clave primaria. | Interno |
| `public_id` | `uuid` | No | UUID aleatorio | UQ | Identificador público opaco que expone la API. Único, no editable. | Interno |
| `created_at` | `timestamp with time zone` | No | Al crear | — | Fecha y hora de creación del registro. | Interno |
| `updated_at` | `timestamp with time zone` | No | Al guardar | — | Fecha y hora de la última modificación. | Interno |
| `is_active` | `boolean` | No | `true` | — | Vigencia del registro; `false` equivale a baja lógica. | Interno |
| `unit_count` | `smallint` | Sí | — | — | Cantidad de unidades propia del ciclo. Vacía hereda la configuración global. No negativo. | Interno |
| `academic_cycle_id` | `bigint` | No | — | FK → `academics_academiccycle.id` (CASCADE); UQ | Ciclo al que aplica el ajuste. Relación 1:1. | Interno |

Restricciones e índices:

| Tipo | Nombre | Definición | Regla |
| --- | --- | --- | --- |
| Verificación | `cycle_evaluation_config_positive_unit_count` | `CHECK (((unit_count IS NULL) OR (unit_count > 0)))` | La cantidad de unidades del ciclo, si se define, es mayor que cero. |

### `evaluation_evaluationglobalconfig` — Configuración global de evaluación

Cantidad de unidades de evaluación sugerida para los ciclos nuevos. Fila única.

- **Clasificación:** Interno.
- **Historia:** Fila única; se actualiza en sitio.

| Campo | Tipo | Nulo | Defecto | Clave | Descripción y regla | Clasif. |
| --- | --- | --- | --- | --- | --- | --- |
| `id` | `bigint` | No | Autogenerado | PK | Identificador interno secuencial. Clave primaria. | Interno |
| `public_id` | `uuid` | No | UUID aleatorio | UQ | Identificador público opaco que expone la API. Único, no editable. | Interno |
| `created_at` | `timestamp with time zone` | No | Al crear | — | Fecha y hora de creación del registro. | Interno |
| `updated_at` | `timestamp with time zone` | No | Al guardar | — | Fecha y hora de la última modificación. | Interno |
| `is_active` | `boolean` | No | `true` | — | Vigencia del registro; `false` equivale a baja lógica. | Interno |
| `singleton_key` | `boolean` | No | `true` | UQ | Clave fija que garantiza una sola fila. Única. | Interno |
| `default_unit_count` | `smallint` | No | `4` | — | Cantidad de unidades sugerida para los ciclos nuevos. Mayor que cero. No negativo. | Interno |

Restricciones e índices:

| Tipo | Nombre | Definición | Regla |
| --- | --- | --- | --- |
| Verificación | `evaluation_global_config_positive_unit_count` | `CHECK ((default_unit_count > 0))` | La cantidad de unidades por defecto es mayor que cero. |

### `evaluation_evaluationunit` — Unidad de evaluación

Periodo de evaluación dentro de un ciclo (bimestre, trimestre), con sus ventanas de captura y de recuperación.

- **Clasificación:** Interno.
- **Historia:** No se elimina: se abre o cierra con `status`.
- **La referencian:** `evaluation_captureexceptiongrant`, `evaluation_grade`.

| Campo | Tipo | Nulo | Defecto | Clave | Descripción y regla | Clasif. |
| --- | --- | --- | --- | --- | --- | --- |
| `id` | `bigint` | No | Autogenerado | PK | Identificador interno secuencial. Clave primaria. | Interno |
| `public_id` | `uuid` | No | UUID aleatorio | UQ | Identificador público opaco que expone la API. Único, no editable. | Interno |
| `created_at` | `timestamp with time zone` | No | Al crear | — | Fecha y hora de creación del registro. | Interno |
| `updated_at` | `timestamp with time zone` | No | Al guardar | — | Fecha y hora de la última modificación. | Interno |
| `is_active` | `boolean` | No | `true` | — | Vigencia del registro; `false` equivale a baja lógica. | Interno |
| `number` | `smallint` | No | — | — | Orden de la unidad dentro del ciclo: 1, 2, 3, etc. No negativo. | Interno |
| `name` | `character varying(100)` | No | — | — | Nombre para mostrar de la unidad. | Interno |
| `starts_on` | `date` | No | — | — | Primer día del periodo de evaluación. | Interno |
| `ends_on` | `date` | No | — | — | Último día del periodo de evaluación. | Interno |
| `status` | `character varying(20)` | No | `open` | — | Abierta: admite captura de notas. Cerrada: no admite captura salvo excepción autorizada. Valores: `open`, `closed`. | Interno |
| `capture_starts_on` | `date` | No | — | — | Fecha en que abre la ventana de captura de notas. | Interno |
| `capture_ends_on` | `date` | No | — | — | Fecha en que cierra la ventana de captura de notas. | Interno |
| `recovery_starts_on` | `date` | Sí | — | — | Fecha en que abre la ventana de recuperación. Opcional. | Interno |
| `recovery_ends_on` | `date` | Sí | — | — | Fecha en que cierra la ventana de recuperación. Opcional. | Interno |
| `academic_cycle_id` | `bigint` | No | — | FK → `academics_academiccycle.id` (CASCADE) | Ciclo escolar al que pertenece. | Interno |

Restricciones e índices:

| Tipo | Nombre | Definición | Regla |
| --- | --- | --- | --- |
| Verificación | `evaluation_unit_valid_capture_dates` | `CHECK ((capture_starts_on <= capture_ends_on))` | La ventana de captura abre antes de cerrar. |
| Verificación | `evaluation_unit_valid_dates` | `CHECK ((starts_on <= ends_on))` | El inicio de la unidad no puede ser posterior a su fin. |
| Verificación | `evaluation_unit_valid_recovery_dates` | `CHECK ((((recovery_ends_on IS NULL) AND (recovery_starts_on IS NULL)) OR ((recovery_ends_on IS NOT NULL) AND (recovery_starts_on IS NOT NULL) AND (recovery_starts_on <= recovery_ends_on))))` | La ventana de recuperación se define completa (inicio y fin en orden) o no se define. |
| Única compuesta | `unique_unit_number_per_cycle` | `academic_cycle_id`, `number` | El número de unidad no se repite en un ciclo. |
| Exclusión | `evaluation_unit_no_overlapping_dates` | `EXCLUDE USING gist (academic_cycle_id WITH =, daterange(starts_on, ends_on, '[]'::text) WITH &&)` | Las unidades de un ciclo no pueden traslapar sus fechas. |

### `evaluation_grade` — Nota de unidad

Nota consolidada de un estudiante en un curso y una unidad. Llega ya calculada por el docente.

- **Clasificación:** Restringido.
- **Historia:** Una fila por matrícula, curso y unidad; los cambios quedan en la bitácora.

| Campo | Tipo | Nulo | Defecto | Clave | Descripción y regla | Clasif. |
| --- | --- | --- | --- | --- | --- | --- |
| `id` | `bigint` | No | Autogenerado | PK | Identificador interno secuencial. Clave primaria. | Restringido |
| `public_id` | `uuid` | No | UUID aleatorio | UQ | Identificador público opaco que expone la API. Único, no editable. | Restringido |
| `created_at` | `timestamp with time zone` | No | Al crear | — | Fecha y hora de creación del registro. | Restringido |
| `updated_at` | `timestamp with time zone` | No | Al guardar | — | Fecha y hora de la última modificación. | Restringido |
| `is_active` | `boolean` | No | `true` | — | Vigencia del registro; `false` equivale a baja lógica. | Restringido |
| `value` | `smallint` | No | — | — | Nota consolidada de la unidad, en escala de 0 a 100. No negativo. | Restringido |
| `enrolment_id` | `bigint` | No | — | FK → `enrolments_enrolment.id` (PROTECT) | Matrícula a la que pertenece; liga el registro al estudiante, la sección y el ciclo. | Restringido |
| `evaluation_unit_id` | `bigint` | No | — | FK → `evaluation_evaluationunit.id` (PROTECT) | Unidad a la que pertenece la nota. | Restringido |
| `subject_id` | `bigint` | No | — | FK → `academics_subject.id` (PROTECT) | Curso al que corresponde. | Restringido |

Restricciones e índices:

| Tipo | Nombre | Definición | Regla |
| --- | --- | --- | --- |
| Verificación | `grade_value_within_scale` | `CHECK (((value >= 0) AND (value <= 100)))` | La nota está entre 0 y 100. |
| Única compuesta | `unique_grade_per_enrolment_subject_unit` | `enrolment_id`, `subject_id`, `evaluation_unit_id` | Una sola nota por matrícula, curso y unidad. |

### `evaluation_recoverygrade` — Nota de recuperación

Resultado de la recuperación de un curso reprobado. Se guarda junto a la nota final original, sin reemplazarla.

- **Clasificación:** Restringido.
- **Historia:** Una fila por matrícula y curso; conserva la nota final original.

| Campo | Tipo | Nulo | Defecto | Clave | Descripción y regla | Clasif. |
| --- | --- | --- | --- | --- | --- | --- |
| `id` | `bigint` | No | Autogenerado | PK | Identificador interno secuencial. Clave primaria. | Restringido |
| `public_id` | `uuid` | No | UUID aleatorio | UQ | Identificador público opaco que expone la API. Único, no editable. | Restringido |
| `created_at` | `timestamp with time zone` | No | Al crear | — | Fecha y hora de creación del registro. | Restringido |
| `updated_at` | `timestamp with time zone` | No | Al guardar | — | Fecha y hora de la última modificación. | Restringido |
| `is_active` | `boolean` | No | `true` | — | Vigencia del registro; `false` equivale a baja lógica. | Restringido |
| `value` | `smallint` | No | — | — | Resultado de la recuperación, en escala de 0 a 100. No negativo. | Restringido |
| `original_final_grade` | `smallint` | No | — | — | Nota final redondeada antes de la recuperación, conservada como referencia. No negativo. | Restringido |
| `enrolment_id` | `bigint` | No | — | FK → `enrolments_enrolment.id` (PROTECT) | Matrícula a la que pertenece; liga el registro al estudiante, la sección y el ciclo. | Restringido |
| `subject_id` | `bigint` | No | — | FK → `academics_subject.id` (PROTECT) | Curso reprobado al que aplica la recuperación. | Restringido |

Restricciones e índices:

| Tipo | Nombre | Definición | Regla |
| --- | --- | --- | --- |
| Verificación | `recovery_grade_value_within_scale` | `CHECK (((value >= 0) AND (value <= 100)))` | La nota de recuperación está entre 0 y 100. |
| Única compuesta | `unique_recovery_grade_per_enrolment_subject` | `enrolment_id`, `subject_id` | Una sola nota de recuperación por matrícula y curso. |

## 13. Documentos

Tipos, plantillas, expediente documental, folios, verificación y descarga.

### `documents_documentbatchrun` — Corrida de emisión por lote

Marca de idempotencia de una emisión por lote, para no repetirla si el cliente reintenta.

- **Clasificación:** Interno.
- **Historia:** Solo inserción: no se edita ni se elimina.

| Campo | Tipo | Nulo | Defecto | Clave | Descripción y regla | Clasif. |
| --- | --- | --- | --- | --- | --- | --- |
| `id` | `bigint` | No | Autogenerado | PK | Identificador interno secuencial. Clave primaria. | Interno |
| `public_id` | `uuid` | No | UUID aleatorio | UQ | Identificador público opaco que expone la API. Único, no editable. | Interno |
| `created_at` | `timestamp with time zone` | No | Al crear | — | Fecha y hora de creación del registro. | Interno |
| `updated_at` | `timestamp with time zone` | No | Al guardar | — | Fecha y hora de la última modificación. | Interno |
| `is_active` | `boolean` | No | `true` | — | Vigencia del registro; `false` equivale a baja lógica. | Interno |
| `client_batch_id` | `character varying(100)` | No | Vacío | — | Identificador del lote generado por el cliente. Hace idempotente el reintento. | Interno |
| `document_type` | `character varying(100)` | No | — | — | Tipo de documento emitido. | Interno |
| `enrolment_count` | `integer` | No | — | — | Cantidad de matrículas incluidas en el lote. No negativo. | Interno |

Restricciones e índices:

| Tipo | Nombre | Definición | Regla |
| --- | --- | --- | --- |
| Única parcial | `unique_document_batch_run_client_batch_id` | `btree (client_batch_id) WHERE (NOT ((client_batch_id)::text = ''::text))` | Un mismo lote enviado por el cliente no se emite dos veces. |

### `documents_documentdeliveryreceipt` — Constancia de entrega

Acuse inmutable de que un documento impreso fue entregado a un encargado.

- **Clasificación:** Restringido.
- **Historia:** Solo inserción: no se edita ni se elimina.

| Campo | Tipo | Nulo | Defecto | Clave | Descripción y regla | Clasif. |
| --- | --- | --- | --- | --- | --- | --- |
| `id` | `bigint` | No | Autogenerado | PK | Identificador interno secuencial. Clave primaria. | Restringido |
| `public_id` | `uuid` | No | UUID aleatorio | UQ | Identificador público opaco que expone la API. Único, no editable. | Restringido |
| `created_at` | `timestamp with time zone` | No | Al crear | — | Fecha y hora de creación del registro. | Restringido |
| `updated_at` | `timestamp with time zone` | No | Al guardar | — | Fecha y hora de la última modificación. | Restringido |
| `is_active` | `boolean` | No | `true` | — | Vigencia del registro; `false` equivale a baja lógica. | Restringido |
| `document_type` | `character varying(100)` | No | — | — | Tipo de documento emitido. | Restringido |
| `folio` | `character varying(100)` | No | — | — | Folio del documento emitido. | Restringido |
| `recipient_name` | `character varying(150)` | No | — | — | Nombre de quien recibió el documento. | Restringido |
| `delivered_at` | `timestamp with time zone` | No | Momento actual | — | Momento de la entrega. | Restringido |
| `notes` | `text` | No | — | — | Observaciones de la entrega. | Restringido |
| `guardian_id` | `bigint` | No | — | FK → `students_guardian.id` (PROTECT) | Encargado que recibió el documento. | Restringido |
| `student_id` | `bigint` | No | — | FK → `students_student.id` (PROTECT) | Estudiante al que pertenece el registro. | Restringido |

### `documents_documentdownloadtoken` — Token de descarga

Token de un solo uso y vigencia breve para descargar un documento, ligado a la cuenta que lo solicitó. Solo se guarda su resumen criptográfico.

- **Clasificación:** Sensible especial.
- **Historia:** No se elimina: se marca usado o revocado.

| Campo | Tipo | Nulo | Defecto | Clave | Descripción y regla | Clasif. |
| --- | --- | --- | --- | --- | --- | --- |
| `id` | `bigint` | No | Autogenerado | PK | Identificador interno secuencial. Clave primaria. | Sensible especial |
| `public_id` | `uuid` | No | UUID aleatorio | UQ | Identificador público opaco que expone la API. Único, no editable. | Sensible especial |
| `created_at` | `timestamp with time zone` | No | Al crear | — | Fecha y hora de creación del registro. | Sensible especial |
| `updated_at` | `timestamp with time zone` | No | Al guardar | — | Fecha y hora de la última modificación. | Sensible especial |
| `is_active` | `boolean` | No | `true` | — | Vigencia del registro; `false` equivale a baja lógica. | Sensible especial |
| `token_hash` | `character varying(128)` | No | — | UQ | Resumen SHA-256 del token. El token en claro nunca se guarda. | Sensible especial |
| `expires_at` | `timestamp with time zone` | No | Ahora + vigencia breve | — | Momento en que deja de ser válido. | Sensible especial |
| `used_at` | `timestamp with time zone` | Sí | — | — | Momento en que se consumió; vacío si no se ha usado. | Sensible especial |
| `revoked_at` | `timestamp with time zone` | Sí | — | — | Momento en que se revocó; vacío si no se revocó. | Sensible especial |
| `created_by_id` | `bigint` | Sí | — | FK → `identity_useraccount.id` (PROTECT) | Cuenta que solicitó el token; solo ella puede consumirlo. | Sensible especial |
| `document_id` | `bigint` | No | — | FK → `documents_documentrecord.id` (PROTECT) | Documento que el token permite descargar. | Sensible especial |

### `documents_documentkind` — Tipo de documento

Catálogo institucional de tipos de documento (constancia, certificado, etc.).

- **Clasificación:** Interno.
- **Historia:** Catálogo: se retira con `is_active = false` para no romper referencias históricas.
- **La referencian:** `documents_documenttemplate`.

| Campo | Tipo | Nulo | Defecto | Clave | Descripción y regla | Clasif. |
| --- | --- | --- | --- | --- | --- | --- |
| `id` | `bigint` | No | Autogenerado | PK | Identificador interno secuencial. Clave primaria. | Interno |
| `public_id` | `uuid` | No | UUID aleatorio | UQ | Identificador público opaco que expone la API. Único, no editable. | Interno |
| `created_at` | `timestamp with time zone` | No | Al crear | — | Fecha y hora de creación del registro. | Interno |
| `updated_at` | `timestamp with time zone` | No | Al guardar | — | Fecha y hora de la última modificación. | Interno |
| `is_active` | `boolean` | No | `true` | — | Vigencia del registro; `false` equivale a baja lógica. | Interno |
| `code` | `character varying(30)` | No | — | — | Código del tipo de documento. Único por institución. | Interno |
| `label` | `character varying(100)` | No | — | — | Nombre para mostrar del tipo de documento. | Interno |
| `description` | `character varying(255)` | No | Vacío | — | Descripción libre. | Interno |
| `institution_id` | `bigint` | No | — | FK → `academics_institution.id` (CASCADE) | Institución a la que pertenece. | Interno |

Restricciones e índices:

| Tipo | Nombre | Definición | Regla |
| --- | --- | --- | --- |
| Única compuesta | `unique_document_kind_code_per_institution` | `institution_id`, `code` | El código de tipo de documento no se repite en una institución. |

### `documents_documentrecord` — Documento del expediente

Metadatos de un archivo almacenado del expediente del estudiante: nombre, tipo, tamaño, suma de verificación y linaje de versiones. El contenido del archivo vive fuera de la base.

- **Clasificación:** Sensible especial.
- **Historia:** Sin borrado físico. Los metadatos son inmutables: una nueva versión crea otra fila enlazada con `supersedes_id`.
- **La referencian:** `documents_documentdownloadtoken`.

| Campo | Tipo | Nulo | Defecto | Clave | Descripción y regla | Clasif. |
| --- | --- | --- | --- | --- | --- | --- |
| `id` | `bigint` | No | Autogenerado | PK | Identificador interno secuencial. Clave primaria. | Sensible especial |
| `public_id` | `uuid` | No | UUID aleatorio | UQ | Identificador público opaco que expone la API. Único, no editable. | Sensible especial |
| `created_at` | `timestamp with time zone` | No | Al crear | — | Fecha y hora de creación del registro. | Sensible especial |
| `updated_at` | `timestamp with time zone` | No | Al guardar | — | Fecha y hora de la última modificación. | Sensible especial |
| `is_active` | `boolean` | No | `true` | — | Vigencia del registro; `false` equivale a baja lógica. | Sensible especial |
| `filename` | `character varying(255)` | No | — | — | Nombre original del archivo, normalizado. | Sensible especial |
| `storage_key` | `character varying(500)` | No | — | UQ | Ruta del archivo en el almacenamiento. Es aleatoria y no deriva del nombre original. | Sensible especial |
| `content_type` | `character varying(100)` | No | — | — | Tipo MIME declarado del archivo. | Sensible especial |
| `size_bytes` | `bigint` | No | — | — | Tamaño del archivo en bytes. No negativo. | Sensible especial |
| `checksum` | `character varying(128)` | No | — | — | Suma SHA-256 del archivo, para verificar su integridad. | Sensible especial |
| `status` | `character varying(20)` | No | `active` | — | Estado de almacenamiento del documento. Valores: `active`, `archived`, `retained`. | Sensible especial |
| `enrolment_id` | `bigint` | Sí | — | FK → `enrolments_enrolment.id` (PROTECT) | Matrícula a la que se asocia el documento. Opcional. | Sensible especial |
| `student_id` | `bigint` | No | — | FK → `students_student.id` (PROTECT) | Estudiante al que pertenece el registro. | Sensible especial |
| `supersedes_id` | `bigint` | Sí | — | FK → `documents_documentrecord.id` (PROTECT) | Versión anterior que este documento reemplaza. Vacía en la primera versión. | Sensible especial |
| `version_group_id` | `uuid` | No | UUID aleatorio | — | Identificador común de todas las versiones de un mismo documento. | Sensible especial |
| `version_number` | `integer` | No | `1` | — | Número de versión dentro del grupo. No negativo. | Sensible especial |

Restricciones e índices:

| Tipo | Nombre | Definición | Regla |
| --- | --- | --- | --- |
| Única compuesta | `unique_document_record_version_in_group` | `version_group_id`, `version_number` | El número de versión no se repite dentro de un mismo documento. |

### `documents_documenttemplate` — Plantilla de documento

Formato reutilizable para emitir reportes y certificados. Solo una plantilla activa por tipo de documento e institución.

- **Clasificación:** Interno.
- **Historia:** Baja lógica con `is_active`; no se elimina físicamente.
- **La referencian:** `documents_documenttemplateversion`.

| Campo | Tipo | Nulo | Defecto | Clave | Descripción y regla | Clasif. |
| --- | --- | --- | --- | --- | --- | --- |
| `id` | `bigint` | No | Autogenerado | PK | Identificador interno secuencial. Clave primaria. | Interno |
| `public_id` | `uuid` | No | UUID aleatorio | UQ | Identificador público opaco que expone la API. Único, no editable. | Interno |
| `created_at` | `timestamp with time zone` | No | Al crear | — | Fecha y hora de creación del registro. | Interno |
| `updated_at` | `timestamp with time zone` | No | Al guardar | — | Fecha y hora de la última modificación. | Interno |
| `is_active` | `boolean` | No | `true` | — | Vigencia del registro; `false` equivale a baja lógica. | Interno |
| `name` | `character varying(150)` | No | — | — | Nombre de la plantilla. | Interno |
| `code` | `character varying(30)` | No | — | — | Código de la plantilla. Único por institución. | Interno |
| `description` | `character varying(255)` | No | — | — | Descripción libre. | Interno |
| `institution_id` | `bigint` | No | — | FK → `academics_institution.id` (CASCADE) | Institución a la que pertenece. | Interno |
| `content` | `text` | No | Vacío | — | Contenido de la plantilla con sus etiquetas de campo. | Interno |
| `document_kind_id` | `bigint` | No | — | FK → `documents_documentkind.id` (PROTECT) | Tipo de documento del catálogo institucional. | Interno |

Restricciones e índices:

| Tipo | Nombre | Definición | Regla |
| --- | --- | --- | --- |
| Única compuesta | `unique_document_template_code_per_institution` | `institution_id`, `code` | El código de plantilla no se repite en una institución. |
| Única parcial | `unique_active_document_template_per_kind_per_institution` | `btree (institution_id, document_kind_id) WHERE is_active` | Una sola plantilla activa por tipo de documento e institución. |

### `documents_documenttemplateversion` — Versión de plantilla

Fotografía inmutable del contenido de una plantilla en un momento dado, para trazabilidad institucional.

- **Clasificación:** Interno.
- **Historia:** Solo inserción: no se edita ni se elimina.

| Campo | Tipo | Nulo | Defecto | Clave | Descripción y regla | Clasif. |
| --- | --- | --- | --- | --- | --- | --- |
| `id` | `bigint` | No | Autogenerado | PK | Identificador interno secuencial. Clave primaria. | Interno |
| `public_id` | `uuid` | No | UUID aleatorio | UQ | Identificador público opaco que expone la API. Único, no editable. | Interno |
| `created_at` | `timestamp with time zone` | No | Al crear | — | Fecha y hora de creación del registro. | Interno |
| `updated_at` | `timestamp with time zone` | No | Al guardar | — | Fecha y hora de la última modificación. | Interno |
| `is_active` | `boolean` | No | `true` | — | Vigencia del registro; `false` equivale a baja lógica. | Interno |
| `sequence` | `integer` | No | — | — | Número de versión dentro de la plantilla. No negativo. | Interno |
| `name` | `character varying(150)` | No | — | — | Nombre de la plantilla al momento de la versión. | Interno |
| `kind` | `character varying(30)` | No | — | — | Código del tipo de documento al momento de la versión. | Interno |
| `description` | `character varying(255)` | No | — | — | Descripción de la plantilla al momento de la versión. | Interno |
| `template_id` | `bigint` | No | — | FK → `documents_documenttemplate.id` (CASCADE) | Plantilla a la que pertenece la versión. | Interno |
| `content` | `text` | No | Vacío | — | Contenido de la plantilla al momento de la versión. | Interno |

Restricciones e índices:

| Tipo | Nombre | Definición | Regla |
| --- | --- | --- | --- |
| Única compuesta | `unique_document_template_version_sequence` | `template_id`, `sequence` | El número de versión no se repite dentro de una plantilla. |

### `documents_documentverificationcode` — Código de verificación

Registro para verificar públicamente un documento emitido mediante un código aleatorio no secuencial.

- **Clasificación:** Restringido.
- **Historia:** Solo inserción: no se edita ni se elimina.

| Campo | Tipo | Nulo | Defecto | Clave | Descripción y regla | Clasif. |
| --- | --- | --- | --- | --- | --- | --- |
| `id` | `bigint` | No | Autogenerado | PK | Identificador interno secuencial. Clave primaria. | Restringido |
| `public_id` | `uuid` | No | UUID aleatorio | UQ | Identificador público opaco que expone la API. Único, no editable. | Restringido |
| `created_at` | `timestamp with time zone` | No | Al crear | — | Fecha y hora de creación del registro. | Restringido |
| `updated_at` | `timestamp with time zone` | No | Al guardar | — | Fecha y hora de la última modificación. | Restringido |
| `is_active` | `boolean` | No | `true` | — | Vigencia del registro; `false` equivale a baja lógica. | Restringido |
| `code` | `character varying(64)` | No | — | UQ | Código aleatorio no secuencial para la verificación pública. Único. | Restringido |
| `document_type` | `character varying(100)` | No | — | — | Tipo de documento emitido. | Restringido |
| `issued_at` | `character varying(50)` | No | Vacío | — | Fecha de emisión que se muestra al verificar, guardada como texto. | Restringido |
| `folio` | `character varying(100)` | No | Vacío | — | Folio del documento emitido. | Restringido |

### `documents_officialfolio` — Folio oficial

Contador institucional de la secuencia de folios de documentos oficiales por año.

- **Clasificación:** Restringido.
- **Historia:** Solo inserción: no se edita ni se elimina.

| Campo | Tipo | Nulo | Defecto | Clave | Descripción y regla | Clasif. |
| --- | --- | --- | --- | --- | --- | --- |
| `id` | `bigint` | No | Autogenerado | PK | Identificador interno secuencial. Clave primaria. | Restringido |
| `public_id` | `uuid` | No | UUID aleatorio | UQ | Identificador público opaco que expone la API. Único, no editable. | Restringido |
| `created_at` | `timestamp with time zone` | No | Al crear | — | Fecha y hora de creación del registro. | Restringido |
| `updated_at` | `timestamp with time zone` | No | Al guardar | — | Fecha y hora de la última modificación. | Restringido |
| `is_active` | `boolean` | No | `true` | — | Vigencia del registro; `false` equivale a baja lógica. | Restringido |
| `year` | `smallint` | No | — | — | Año del folio. No negativo. | Restringido |
| `sequence` | `integer` | No | — | — | Número correlativo del folio dentro del año. No negativo. | Restringido |
| `document_type` | `character varying(50)` | No | — | — | Tipo de documento emitido. | Restringido |
| `issued_at` | `timestamp with time zone` | Sí | — | — | Momento de emisión del folio. | Restringido |
| `institution_id` | `bigint` | No | — | FK → `academics_institution.id` (PROTECT) | Institución a la que pertenece. | Restringido |

Restricciones e índices:

| Tipo | Nombre | Definición | Regla |
| --- | --- | --- | --- |
| Única compuesta | `unique_official_folio_per_institution_year_sequence` | `institution_id`, `year`, `sequence` | El folio no se repite por institución y año. |

## 14. Alertas

Umbrales y alertas institucionales de inasistencia.

### `reporting_absencethresholdparameters` — Umbral de ausencias

Cantidad de ausencias y ventana de días que definen «ausencias frecuentes» para una jornada en un ciclo.

- **Clasificación:** Interno.
- **Historia:** Versionado por vigencia: un cambio crea una fila nueva y conserva las anteriores.

| Campo | Tipo | Nulo | Defecto | Clave | Descripción y regla | Clasif. |
| --- | --- | --- | --- | --- | --- | --- |
| `id` | `bigint` | No | Autogenerado | PK | Identificador interno secuencial. Clave primaria. | Interno |
| `public_id` | `uuid` | No | UUID aleatorio | UQ | Identificador público opaco que expone la API. Único, no editable. | Interno |
| `created_at` | `timestamp with time zone` | No | Al crear | — | Fecha y hora de creación del registro. | Interno |
| `updated_at` | `timestamp with time zone` | No | Al guardar | — | Fecha y hora de la última modificación. | Interno |
| `is_active` | `boolean` | No | `true` | — | Vigencia del registro; `false` equivale a baja lógica. | Interno |
| `max_absences` | `integer` | No | — | — | Cantidad de ausencias que dispara la alerta de ausencias frecuentes. No negativo. | Interno |
| `lookback_days` | `integer` | No | — | — | Días hacia atrás que se consideran para contar ausencias. No negativo. | Interno |
| `effective_from` | `date` | No | — | — | Fecha desde la que rige esta versión de los parámetros. | Interno |
| `academic_cycle_id` | `bigint` | No | — | FK → `academics_academiccycle.id` (PROTECT) | Ciclo escolar al que pertenece. | Interno |
| `shift_id` | `bigint` | No | — | FK → `academics_shift.id` (PROTECT) | Jornada a la que corresponde. | Interno |

Restricciones e índices:

| Tipo | Nombre | Definición | Regla |
| --- | --- | --- | --- |
| Única compuesta | `unique_absence_threshold_parameters_effective_from` | `shift_id`, `academic_cycle_id`, `effective_from` | Una sola versión del umbral por jornada, ciclo y fecha de vigencia. |
| Índice | `reporting_threshold_lookup_idx` | `btree (shift_id, academic_cycle_id, effective_from)` | Acelera la búsqueda del umbral vigente de una jornada y ciclo. |

### `reporting_alert` — Alerta institucional

Alerta de inasistencia dirigida a los roles que deben atenderla. Algunas se proyectan desde las alertas de asistencia.

- **Clasificación:** Restringido.
- **Historia:** No se elimina: se marca atendida con `acknowledged_at` y `acknowledged_by_id`.

| Campo | Tipo | Nulo | Defecto | Clave | Descripción y regla | Clasif. |
| --- | --- | --- | --- | --- | --- | --- |
| `id` | `bigint` | No | Autogenerado | PK | Identificador interno secuencial. Clave primaria. | Restringido |
| `public_id` | `uuid` | No | UUID aleatorio | UQ | Identificador público opaco que expone la API. Único, no editable. | Restringido |
| `created_at` | `timestamp with time zone` | No | Al crear | — | Fecha y hora de creación del registro. | Restringido |
| `updated_at` | `timestamp with time zone` | No | Al guardar | — | Fecha y hora de la última modificación. | Restringido |
| `is_active` | `boolean` | No | `true` | — | Vigencia del registro; `false` equivale a baja lógica. | Restringido |
| `alert_type` | `character varying(30)` | No | — | — | Tipo de alerta. Valores: `ausente_sin_registro`, `permanencia_sin_cierre`, `frecuencia_ausencias`, `inconsistencia`. | Restringido |
| `event_date` | `date` | No | — | — | Fecha lectiva a la que corresponde. | Restringido |
| `target_roles` | `jsonb` | No | `[]` | — | Lista de roles a los que se dirige la alerta. | Restringido |
| `context` | `jsonb` | No | `{}` | — | Datos adicionales de contexto en JSON. | Restringido |
| `acknowledged_at` | `timestamp with time zone` | Sí | — | — | Momento en que se marcó como atendida; vacío si sigue pendiente. | Restringido |
| `acknowledged_by_id` | `bigint` | Sí | — | FK → `identity_useraccount.id` (SET_NULL) | Cuenta que la marcó como atendida. | Restringido |
| `section_id` | `bigint` | Sí | — | FK → `academics_section.id` (PROTECT) | Sección del estudiante al generarse la alerta. Opcional. | Restringido |
| `shift_id` | `bigint` | No | — | FK → `academics_shift.id` (PROTECT) | Jornada a la que corresponde. | Restringido |
| `source_attendance_alert_id` | `bigint` | Sí | — | FK → `attendance_attendancealert.id` (PROTECT) | Alerta de asistencia que originó esta alerta, si aplica. | Restringido |
| `student_id` | `bigint` | No | — | FK → `students_student.id` (PROTECT) | Estudiante al que pertenece el registro. | Restringido |

Restricciones e índices:

| Tipo | Nombre | Definición | Regla |
| --- | --- | --- | --- |
| Índice | `reporting_alert_lookup_idx` | `btree (student_id, shift_id, event_date, alert_type)` | Acelera la búsqueda de alertas por estudiante, jornada y fecha. |
| Única parcial | `unique_active_alert_per_student_day_type` | `btree (student_id, shift_id, event_date, alert_type) WHERE is_active` | Una sola alerta activa por estudiante, jornada, fecha y tipo. |

## 15. Auditoría

Bitácora de operaciones, lecturas sensibles y denegaciones.

### `audit_auditevent` — Evento de auditoría

Bitácora única de escrituras, lecturas sensibles y denegaciones: quién, qué acción, sobre qué recurso, desde dónde y con qué contexto.

- **Clasificación:** Sensible especial.
- **Historia:** Inmutable en la aplicación: no admite edición ni borrado. La inmutabilidad no está reforzada en PostgreSQL.

| Campo | Tipo | Nulo | Defecto | Clave | Descripción y regla | Clasif. |
| --- | --- | --- | --- | --- | --- | --- |
| `id` | `bigint` | No | Autogenerado | PK | Identificador interno secuencial. Clave primaria. | Sensible especial |
| `public_id` | `uuid` | No | UUID aleatorio | UQ | Identificador público opaco que expone la API. Único, no editable. | Sensible especial |
| `created_at` | `timestamp with time zone` | No | Al crear | — | Fecha y hora de creación del registro. | Sensible especial |
| `updated_at` | `timestamp with time zone` | No | Al guardar | — | Fecha y hora de la última modificación. | Sensible especial |
| `is_active` | `boolean` | No | `true` | — | Columna heredada; no se usa para dar de baja eventos. | Sensible especial |
| `actor_label` | `character varying(255)` | No | — | — | Nombre de usuario del actor, conservado aunque la cuenta deje de existir. | Sensible especial |
| `action` | `character varying(100)` | No | — | — | Acción registrada, por ejemplo `identity.login.denied`. | Sensible especial |
| `resource` | `character varying(150)` | No | — | — | Tipo de recurso afectado. | Sensible especial |
| `resource_identifier` | `character varying(255)` | No | — | — | Identificador del recurso afectado. | Sensible especial |
| `ip_address` | `inet` | Sí | — | — | Dirección IP de la petición. | Sensible especial |
| `context` | `jsonb` | No | `{}` | — | Contexto saneado en JSON: ruta, agente, motivo y cambios. Sin contraseñas, tokens ni cookies. | Sensible especial |
| `actor_id` | `bigint` | Sí | — | FK → `identity_useraccount.id` (SET_NULL) | Cuenta que realizó la acción. Queda vacía si la cuenta se elimina. | Sensible especial |

## 16. Operación

Registro de ejecución de tareas programadas.

### `common_taskrun` — Ejecución de tarea

Una ejecución de una tarea programada: cuándo corrió, cuánto tardó y cómo terminó.

- **Clasificación:** Interno.
- **Historia:** Solo inserción y cierre de la propia ejecución; no se elimina.

| Campo | Tipo | Nulo | Defecto | Clave | Descripción y regla | Clasif. |
| --- | --- | --- | --- | --- | --- | --- |
| `id` | `bigint` | No | Autogenerado | PK | Identificador interno secuencial. Clave primaria. | Interno |
| `public_id` | `uuid` | No | UUID aleatorio | UQ | Identificador público opaco que expone la API. Único, no editable. | Interno |
| `created_at` | `timestamp with time zone` | No | Al crear | — | Fecha y hora de creación del registro. | Interno |
| `updated_at` | `timestamp with time zone` | No | Al guardar | — | Fecha y hora de la última modificación. | Interno |
| `is_active` | `boolean` | No | `true` | — | Vigencia del registro; `false` equivale a baja lógica. | Interno |
| `name` | `character varying(100)` | No | — | — | Identificador estable de la tarea, normalmente el comando que la ejecuta. | Interno |
| `status` | `character varying(20)` | No | `running` | — | Estado de la ejecución. Valores: `running`, `succeeded`, `failed`. | Interno |
| `started_at` | `timestamp with time zone` | No | — | — | Momento de inicio. | Interno |
| `finished_at` | `timestamp with time zone` | Sí | — | — | Momento de fin; vacío mientras corre. | Interno |
| `duration_ms` | `integer` | Sí | — | — | Duración en milisegundos. No negativo. | Interno |
| `host` | `character varying(255)` | No | Vacío | — | Equipo donde corrió la tarea. | Interno |
| `process_id` | `integer` | Sí | — | — | Identificador del proceso del sistema operativo. No negativo. | Interno |
| `summary` | `jsonb` | No | `{}` | — | Resumen del resultado en JSON. | Interno |
| `error_type` | `character varying(150)` | No | Vacío | — | Tipo de error, si falló. | Interno |
| `error_message` | `text` | No | Vacío | — | Mensaje de error, si falló. | Interno |

Restricciones e índices:

| Tipo | Nombre | Definición | Regla |
| --- | --- | --- | --- |
| Índice | `task_run_name_recent_idx` | `btree (name, started_at DESC)` | Acelera la consulta de las ejecuciones más recientes de cada tarea. |

## 17. Plataforma Django

Tablas del framework: permisos, tipos de contenido, sesiones y migraciones.

### `auth_group` — Grupo

Grupos de Django. El sistema no los usa para autorizar.

- **Clasificación:** Interno.
- **Historia:** Gestionada por Django; no la administra el dominio.
- **La referencian:** `auth_group_permissions`, `identity_useraccount_groups`.

| Campo | Tipo | Nulo | Defecto | Clave | Descripción y regla | Clasif. |
| --- | --- | --- | --- | --- | --- | --- |
| `id` | `integer` | No | Autogenerado | PK | Identificador interno secuencial. Clave primaria. | Interno |
| `name` | `character varying(150)` | No | — | UQ | Nombre del grupo. Único. | Interno |

### `auth_group_permissions` — Permisos del grupo

Relación entre grupos y permisos de Django.

- **Clasificación:** Interno.
- **Historia:** Gestionada por Django; no la administra el dominio.

| Campo | Tipo | Nulo | Defecto | Clave | Descripción y regla | Clasif. |
| --- | --- | --- | --- | --- | --- | --- |
| `id` | `bigint` | No | Autogenerado | PK | Identificador interno secuencial. Clave primaria. | Interno |
| `group_id` | `integer` | No | — | FK → `auth_group.id` (CASCADE) | Grupo asociado. | Interno |
| `permission_id` | `integer` | No | — | FK → `auth_permission.id` (CASCADE) | Permiso asociado. | Interno |

Restricciones e índices:

| Tipo | Nombre | Definición | Regla |
| --- | --- | --- | --- |
| Única compuesta | `auth_group_permissions_group_id_permission_id_0cd325b0_uniq` | `group_id`, `permission_id` | La combinación no se repite. |

### `auth_permission` — Permiso

Catálogo de permisos de Django. Contiene los permisos atómicos del sistema, sembrados por migración.

- **Clasificación:** Interno.
- **Historia:** Gestionada por Django; no la administra el dominio.
- **La referencian:** `auth_group_permissions`, `identity_role_permissions`, `identity_useraccount_user_permissions`.

| Campo | Tipo | Nulo | Defecto | Clave | Descripción y regla | Clasif. |
| --- | --- | --- | --- | --- | --- | --- |
| `id` | `integer` | No | Autogenerado | PK | Identificador interno secuencial. Clave primaria. | Interno |
| `name` | `character varying(255)` | No | — | — | Nombre legible del permiso. | Interno |
| `content_type_id` | `integer` | No | — | FK → `django_content_type.id` (CASCADE) | Modelo al que Django asocia el permiso. | Interno |
| `codename` | `character varying(100)` | No | — | — | Código del permiso; los atómicos usan guion bajo en lugar de punto (`student_view_basic`). | Interno |

Restricciones e índices:

| Tipo | Nombre | Definición | Regla |
| --- | --- | --- | --- |
| Única compuesta | `auth_permission_content_type_id_codename_01ab375a_uniq` | `content_type_id`, `codename` | La combinación no se repite. |

### `django_admin_log` — Bitácora del admin

Acciones realizadas desde el sitio de administración de Django. No sustituye a la bitácora de auditoría.

- **Clasificación:** Restringido.
- **Historia:** Gestionada por Django; no la administra el dominio.

| Campo | Tipo | Nulo | Defecto | Clave | Descripción y regla | Clasif. |
| --- | --- | --- | --- | --- | --- | --- |
| `id` | `integer` | No | Autogenerado | PK | Identificador interno secuencial. Clave primaria. | Restringido |
| `action_time` | `timestamp with time zone` | No | Momento actual | — | Momento de la acción. | Restringido |
| `object_id` | `text` | Sí | — | — | Identificador del objeto afectado. | Restringido |
| `object_repr` | `character varying(200)` | No | — | — | Representación en texto del objeto. | Restringido |
| `action_flag` | `smallint` | No | — | — | Tipo de acción: 1 alta, 2 cambio, 3 borrado. No negativo. | Restringido |
| `change_message` | `text` | No | — | — | Detalle del cambio. | Restringido |
| `content_type_id` | `integer` | Sí | — | FK → `django_content_type.id` (SET_NULL) | Modelo del objeto afectado. | Restringido |
| `user_id` | `bigint` | No | — | FK → `identity_useraccount.id` (CASCADE) | Cuenta que realizó la acción en el admin. | Restringido |

### `django_content_type` — Tipo de contenido

Registro interno de Django con cada modelo instalado.

- **Clasificación:** Interno.
- **Historia:** Gestionada por Django; no la administra el dominio.
- **La referencian:** `auth_permission`, `django_admin_log`.

| Campo | Tipo | Nulo | Defecto | Clave | Descripción y regla | Clasif. |
| --- | --- | --- | --- | --- | --- | --- |
| `id` | `integer` | No | Autogenerado | PK | Identificador interno secuencial. Clave primaria. | Interno |
| `app_label` | `character varying(100)` | No | — | — | Nombre de la app Django. | Interno |
| `model` | `character varying(100)` | No | — | — | Nombre del modelo en minúsculas. | Interno |

Restricciones e índices:

| Tipo | Nombre | Definición | Regla |
| --- | --- | --- | --- |
| Única compuesta | `django_content_type_app_label_model_76bd3d3b_uniq` | `app_label`, `model` | La combinación no se repite. |

### `django_migrations` — Migraciones aplicadas

Historial de migraciones aplicadas al esquema.

- **Clasificación:** Interno.
- **Historia:** Gestionada por Django; no la administra el dominio.

| Campo | Tipo | Nulo | Defecto | Clave | Descripción y regla | Clasif. |
| --- | --- | --- | --- | --- | --- | --- |
| `id` | `bigint` | No | Autogenerado | PK | Identificador interno secuencial. Clave primaria. | Interno |
| `app` | `character varying(255)` | No | — | — | App a la que pertenece la migración. | Interno |
| `name` | `character varying(255)` | No | — | — | Nombre de la migración. | Interno |
| `applied` | `timestamp with time zone` | No | — | — | Momento en que se aplicó. | Interno |

### `django_session` — Sesión

Sesiones de usuario del lado del servidor. La cookie del navegador solo lleva la clave.

- **Clasificación:** Sensible especial.
- **Historia:** Las sesiones vencen por `expire_date`; se vacían al cerrar sesión o expirar por inactividad.

| Campo | Tipo | Nulo | Defecto | Clave | Descripción y regla | Clasif. |
| --- | --- | --- | --- | --- | --- | --- |
| `session_key` | `character varying(40)` | No | — | PK | Clave de la sesión. Clave primaria; es el valor de la cookie. | Sensible especial |
| `session_data` | `text` | No | — | — | Datos de la sesión, serializados y firmados. | Sensible especial |
| `expire_date` | `timestamp with time zone` | No | — | — | Momento de vencimiento de la sesión. | Sensible especial |

## 18. Datos de archivo fuera de la base

Estas columnas guardan una ruta o metadatos; el contenido binario no está en PostgreSQL.
Por eso la base y los archivos se respaldan y restauran por separado, y tras restaurar solo
una de las dos pilas hay que verificar la correspondencia con
`check_document_storage_integrity`. Ver [plan de respaldo](09-final-backup-and-recovery-plan.md).

| Tabla y columna | Qué referencia | Metadatos de integridad en la base |
| --- | --- | --- |
| `students_student.photo` | Fotografía del estudiante, bajo `student_photos/`. | Ninguno. |
| `teachers_teacher.photo` | Fotografía del docente, bajo `teacher_photos/`. | Ninguno. |
| `documents_documentrecord.storage_key` | Documento del expediente, con ruta aleatoria. | `checksum` SHA-256, `size_bytes`, `content_type`. |
| `attendance_justificationattachment.storage_key` | Adjunto de una justificación. | `checksum` SHA-256, `size_bytes`, `content_type`. |

## 19. Cambios frente al inventario del manual técnico

El [manual técnico](02-technical-manual.md) inventarió 69 modelos propios sobre el commit
`0996960` (29 de septiembre de 2026). Frente a ese inventario, el esquema actual tiene las
mismas tablas y un cambio de columnas:

| Tabla | Cambio | Migración |
| --- | --- | --- |
| `people_person` | Nuevas columnas `cui`, `sex`, `nationality`, `address`, `department` y `municipality`. | `people/0003_person_institutional_profile` |

## 20. Pendientes antes del cierre

- Regenerar este diccionario sobre el commit candidato final y confirmar que no cambia.
- Revisión cruzada de Santiago: descripciones funcionales y clasificación por tabla.
- Contrastar con el diagrama entidad-relación del manual técnico y con los scripts finales de
  base de datos (manual 06, aún sin documento final).
- La clasificación de `people_person.cui` y `people_person.birth_date` como sensible especial
  quedó registrada en `data-classification.md`, acordada con Santiago en la revisión de este
  manual. Falta la confirmación institucional que coordina Pablo.
- El generador de este diccionario no está versionado. Si se quiere regenerar de forma
  repetible, requiere una decisión sobre dónde alojarlo.
