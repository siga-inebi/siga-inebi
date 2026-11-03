# Initial Data Model

## Objetivo

Definir entidades y relaciones base para fundacion.

## Entidades principales

### Identidad y acceso

- `Person`
- `UserAccount`
- `Role`
- `Permission`
- `RoleAssignment`
- `ScopeGrant`
- `Session`

### Estructura y ciclo

- `SchoolCycle`
- `CycleState`
- `Grade`
- `Section`
- `AcademicSubarea`
- `StudyPlan`
- `TeachingAssignment`
- `ClassScheduleBlock`

### Estudiantes y matricula

- `Student`
- `GuardianLink`
- `EmergencyContact`
- `StudentHealthNote`
- `Enrollment`
- `EnrollmentDocumentRequirement`
- `StudentMovement`

### Asistencia

- `Credential`
- `ControlPoint`
- `CaptureShift`
- `CaptureBatch`
- `AttendanceEvent`
- `AttendanceDayStatus`
- `AttendanceJustification`

### Documentos y archivos

- `DocumentType`
- `DocumentRecord`
- `DocumentVersion`
- `FileObject`
- `GeneratedDocument`
- `Template`
- `OfficialFolio`

### Auditoria

- `AuditLog`
- `SensitiveReadLog`
- `DeniedAttemptLog`

## Relaciones clave

- `UserAccount` referencia `Person`.
- `Student` referencia `Person` o extiende identidad institucional segun implementacion futura.
- `GuardianLink` une estudiante con persona encargada y vigencia.
- `Enrollment` une estudiante, ciclo, grado y seccion.
- `TeachingAssignment` une docente, subarea, seccion y ciclo.
- `AttendanceEvent` referencia estudiante activo, credencial y lote.
- `AttendanceDayStatus` deriva de eventos, reglas y justificaciones.
- `DocumentRecord` referencia sujeto documental y `FileObject`.
- `GeneratedDocument` no implica archivado automatico en expediente.

## Invariantes

- Historia primero: no eliminar registros con trazabilidad.
- Estados y vigencias preferidos sobre borrado fisico.
- Correcciones sensibles agregan evidencia, no pisan historia.
- Archivo binario vive fuera DB; DB guarda metadatos y referencia.
