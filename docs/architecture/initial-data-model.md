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
- `Campus` (sede)
- `Shift` (jornada de la sede)
- `Level` (nivel)
- `Grade`
- `GradeOffering` (grado ofertado en una jornada, por ciclo)
- `Section`
- `AcademicSubarea`
- `LevelSubject` (curso impartido en un nivel)
- `StudyPlan`
- `TeachingAssignment`
- `ClassScheduleBlock`

Detalle de esta rama del modelo, con sus invariantes y contrato HTTP, en
`docs/architecture/academic-catalogue.md`.

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
- `Shift` depende de `Campus`; `Grade` depende de `Level`.
- `GradeOffering` une ciclo, jornada y grado; la sede se deriva de la jornada.
- `Section` depende de `GradeOffering` y expone ciclo, grado, jornada y sede como
  atributos derivados.
- `Enrollment` une estudiante, ciclo, grado y seccion; los tres deben concordar
  con la oferta de la seccion.
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
