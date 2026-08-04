# Modelo de datos implementado

Diagrama de las tablas que existen hoy en el codigo. Refleja los modelos de
`backend/apps/*/models.py` y las migraciones aplicadas hasta
`academics/0004_grade_institution_uniqueness`, no el modelo objetivo completo:
para ese, ver `initial-data-model.md`.

## Campos heredados

Todas las tablas salvo `UserAccount` heredan de `TimeStampedModel`
(`apps/common/models.py`) y por eso comparten cuatro columnas que **no se
repiten en el diagrama**:

| Columna | Tipo | Uso |
| --- | --- | --- |
| `public_id` | UUID unico | Identificador opaco hacia el cliente; los `id` internos no se exponen |
| `created_at` | datetime | Alta del registro |
| `updated_at` | datetime | Ultima modificacion |
| `is_active` | bool | Desactivacion en lugar de borrado (RF-EST-012, ADR-0006) |

`UserAccount` extiende `AbstractUser` de Django, asi que trae `username`,
`password`, `email`, `is_active`, `is_staff` y `is_superuser`.

## Diagrama completo

```mermaid
erDiagram
    Institution ||--o{ Campus : "tiene sedes"
    Institution ||--o{ Level : "define niveles"
    Institution ||--o{ Subject : "define cursos"
    Institution ||--o{ AcademicCycle : "abre ciclos"
    Institution ||--o{ Grade : "columna derivada del nivel"

    Campus ||--o{ Shift : "tiene jornadas"
    Level ||--o{ Grade : "agrupa grados"
    Level ||--o{ LevelSubject : ""
    Subject ||--o{ LevelSubject : ""

    AcademicCycle ||--o{ GradeOffering : "publica oferta"
    Shift ||--o{ GradeOffering : "se imparte en"
    Grade ||--o{ GradeOffering : "se oferta como"
    GradeOffering ||--o{ Section : "se divide en"

    AcademicCycle ||--o{ CurriculumPlan : ""
    Grade ||--o{ CurriculumPlan : ""
    Subject ||--o{ CurriculumPlan : ""

    AcademicCycle ||--o{ TeachingAssignment : ""
    Section ||--o{ TeachingAssignment : ""
    Subject ||--o{ TeachingAssignment : ""
    Person ||--o{ TeachingAssignment : "imparte"

    Person ||--o| Student : "perfil estudiante"
    Person ||--o| Guardian : "perfil encargado"
    Person ||--o| UserAccount : "cuenta"
    Student ||--o{ StudentGuardianRelation : ""
    Guardian ||--o{ StudentGuardianRelation : ""
    Student ||--o{ EmergencyContact : ""

    Student ||--o{ Enrolment : "se matricula"
    AcademicCycle ||--o{ Enrolment : ""
    Grade ||--o{ Enrolment : ""
    Section ||--o{ Enrolment : "ocupa cupo"

    UserAccount ||--o{ RoleAssignment : ""
    Role ||--o{ RoleAssignment : ""
    Role }o--o{ Permission : "permisos atomicos"
    RoleAssignment ||--o{ ScopeGrant : "acota"
    ScopeGrant }o--o| Institution : ""
    ScopeGrant }o--o| AcademicCycle : ""
    ScopeGrant }o--o| Grade : ""
    ScopeGrant }o--o| Section : ""
    ScopeGrant }o--o| Subject : ""
    ScopeGrant }o--o| TeachingAssignment : ""
    ScopeGrant }o--o| Student : ""

    UserAccount |o--o{ AuditEvent : "actor"

    Institution {
        string name
        string short_name
    }

    Campus {
        int institution_id FK
        string name
        string code UK "unico por institucion"
        string address
        bool is_main "unico por institucion via indice parcial"
    }

    Shift {
        int campus_id FK
        string name
        string code UK "unico por sede"
    }

    Level {
        int institution_id FK
        string name
        string code UK "unico por institucion"
        int sequence UK "orden pedagogico, unico por institucion"
    }

    Grade {
        int level_id FK
        int institution_id FK "derivado del nivel, no editable"
        string name
        string code UK "unico por institucion"
        int sequence UK "unico por nivel"
    }

    Subject {
        int institution_id FK
        string name
        string code UK "unico por institucion"
    }

    LevelSubject {
        int level_id FK "unico junto a subject_id"
        int subject_id FK "unico junto a level_id"
        bool is_required
        int weekly_hours "0 significa sin definir"
    }

    AcademicCycle {
        int institution_id FK
        string name UK "unico por institucion"
        date starts_on
        date ends_on
        string status "draft active closed"
    }

    GradeOffering {
        int academic_cycle_id FK "la terna es unica"
        int shift_id FK
        int grade_id FK
    }

    Section {
        int offering_id FK
        string name UK "unico por oferta"
        int capacity "0 significa sin limite"
    }

    CurriculumPlan {
        int academic_cycle_id FK "la terna es unica"
        int grade_id FK
        int subject_id FK
        bool is_required
    }

    TeachingAssignment {
        int academic_cycle_id FK "ciclo+seccion+curso+docente+inicio es unico"
        int section_id FK
        int subject_id FK
        int teacher_id FK "people.Person"
        date starts_on
        date ends_on
    }

    Person {
        string first_name
        string last_name
        string email
        string phone_number
        string institutional_identifier
    }

    Student {
        int person_id FK "one to one"
        string student_code UK
        string status "pre_enrolled active inactive withdrawn"
        string photo_path
    }

    Guardian {
        int person_id FK "one to one"
    }

    StudentGuardianRelation {
        int student_id FK
        int guardian_id FK
        string relationship_label
        bool is_primary
        date starts_at
        date ends_at
    }

    EmergencyContact {
        int student_id FK
        string name
        string phone_number
        string relationship_label
    }

    Enrolment {
        int student_id FK "una sola matricula activa por ciclo"
        int academic_cycle_id FK
        int grade_id FK
        int section_id FK
        date effective_on
        date ends_on
        string status "active withdrawn completed cancelled"
    }

    UserAccount {
        int person_id FK "one to one, opcional"
        string username UK
        string password
        string status "active blocked disabled"
        int failed_login_attempts
        datetime locked_until
    }

    Role {
        string name UK
        string slug UK
        text description
        bool is_system
    }

    Permission {
        string codename "modelo propio de Django"
    }

    RoleAssignment {
        int user_id FK "usuario+rol+inicio es unico"
        int role_id FK
        datetime starts_at
        datetime ends_at
    }

    ScopeGrant {
        int assignment_id FK
        int institution_id FK "opcional"
        int academic_cycle_id FK "opcional"
        int grade_id FK "opcional"
        int section_id FK "opcional"
        int subject_id FK "opcional"
        int teaching_assignment_id FK "opcional"
        int student_id FK "opcional"
        string module_key
        datetime starts_at
        datetime ends_at
    }

    AuditEvent {
        int actor_id FK "nulo si el actor se borra"
        string actor_label
        string action
        string resource
        string resource_identifier
        string ip_address
        json context
    }
```

## El camino que importa

La matricula no se asigna a un grado suelto: se asigna a una seccion, y esa
seccion cuelga de una oferta que ya fija ciclo, jornada, sede y grado.

```mermaid
flowchart LR
    C["AcademicCycle<br/>ciclo 2026"]
    S["Shift<br/>jornada matutina"]
    G["Grade<br/>primero primaria"]
    O["GradeOffering"]
    SEC["Section<br/>A, cupo 30"]
    E["Enrolment"]

    C --> O
    S --> O
    G --> O
    O --> SEC
    SEC --> E

    CAM["Campus<br/>sede central"] --> S
    L["Level<br/>primaria"] --> G
```

`Section` no guarda ciclo, grado ni jornada: los expone como propiedades de su
oferta. Por eso no existe forma de crear una seccion cuyo grado contradiga su
ciclo. `Enrolment` si guarda `grade` y `academic_cycle` de forma redundante, y
el servicio rechaza cualquier matricula donde esos tres no concuerden con la
oferta de la seccion.

## Notas sobre relaciones que no se ven en el diagrama

- **`Grade.institution` es una copia deliberada** de `level.institution`. Un
  indice unico no puede abarcar un join, y sin esa columna la unicidad del
  codigo de grado en toda la institucion solo podria comprobarse en Python. Una
  clave foranea compuesta `(level_id, institution_id)` contra
  `Level (id, institution_id)` impide que la copia se desvie.
- **`Subject.levels`** es un many-to-many hacia `Level` a traves de
  `LevelSubject`; el diagrama muestra la tabla intermedia porque lleva datos
  propios (`is_required`, `weekly_hours`).
- **`CurriculumPlan` y `LevelSubject` se solapan** y todavia no estan
  reconciliados: el primero es el plan por ciclo y grado (RF-EST-005), el
  segundo el catalogo de cursos del nivel. Ver PD-012.
- **`ScopeGrant` no esta en uso todavia.** Los endpoints del catalogo solo
  exigen sesion; la autorizacion por permiso y alcance es PD-013.
- **`AuditEvent` es inmutable**: el modelo bloquea `save` sobre un registro
  existente y `delete`.
- `TeachingAssignment` y `CurriculumPlan` existen desde la fundacion pero aun
  no tienen servicios ni API.
