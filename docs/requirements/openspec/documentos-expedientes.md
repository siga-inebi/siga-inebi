# documentos-expedientes

## ADDED Requirements

### Requirement: Vinculación del documento al expediente del estudiante o del docente (RF-DOC-001)

El sistema DEBE asociar cada archivo subido al expediente institucional de exactamente un dueño:
un estudiante o un docente. Un registro documental NO DEBE quedar sin dueño ni pertenecer a dos
expedientes a la vez; la base de datos DEBE rechazarlo. El dueño de un registro NO DEBE cambiar
después de creado.

El expediente del docente DEBE ofrecer las mismas garantías que el del estudiante: tipos y tamaño
según el catálogo de almacenamiento, binario fuera de la base de datos, checksum SHA-256,
versionado inmutable que conserva las versiones anteriores, descarga con token breve de un solo
uso ligado al usuario y auditoría de cargas, lecturas, descargas y denegaciones.

#### Scenario: Carga al expediente del docente

- **GIVEN** un usuario administrativo con `document.upload` y alcance sobre el módulo `teachers`
- **WHEN** adjunta un PDF al expediente de un docente
- **THEN** el registro queda vinculado al docente, sin estudiante, con su SHA-256 y versión 1
- **AND** el archivo se guarda fuera de la base de datos y se audita `documents.document.uploaded`

#### Scenario: Sustitución conserva el historial

- **GIVEN** un documento vigente del expediente de un docente
- **WHEN** un usuario autorizado carga una nueva versión
- **THEN** se crea la versión 2 del mismo grupo y la versión 1 queda archivada, no eliminada

#### Scenario: Registro sin dueño o con dos dueños

- **WHEN** se intenta persistir un registro sin estudiante ni docente, o con ambos
- **THEN** la base de datos rechaza la escritura

### Requirement: Acceso al expediente del docente según el alcance (RF-DOC-001, RF-DOC-004)

El acceso DEBE denegarse por defecto. Leer el expediente de un docente DEBE exigir
`document.read` y, además, ser el propio docente (cuenta vinculada a la misma persona) o tener
el permiso con alcance sobre el módulo `teachers`. Cargar DEBE exigir `document.upload` con
alcance sobre el módulo `teachers`; el docente NO DEBE cargar en su propio expediente. Un alcance
sobre estudiantes, instituciones o secciones NO DEBE alcanzar expedientes de docentes.

#### Scenario: El docente consulta su expediente

- **GIVEN** un docente con cuenta y permiso `document.read`
- **WHEN** consulta sus documentos
- **THEN** recibe solo los documentos de su propio expediente

#### Scenario: Docente fuera de alcance

- **GIVEN** un docente con `document.read`
- **WHEN** intenta consultar el expediente de otro docente
- **THEN** el sistema responde 403 y registra `documents.document.read_denied` con motivo
  `missing_scope`

### Requirement: Emisión individual de constancia y certificado (RF-EMI-001)

El sistema DEBE permitir a un usuario con `document.issue` y alcance sobre el estudiante generar de
forma individual una constancia de inscripción (`enrolment_certificate`) o un certificado de
estudios (`study_certificate`). La boleta individual sigue en
`GET /api/v1/documents/historical-cycle-reports/` (RF-EMI-005).

El PDF DEBE compilarse en memoria con el generador común, con tabla de referencias cruzada
correcta para abrir sin reparación (QA4-PDF-01), y NO DEBE almacenarse (RF-DOC-008). Cada emisión
DEBE quedar registrada de forma inmutable con folio correlativo institucional (RF-EMI-003), código
de verificación público (RF-EMI-009), versión de plantilla usada, SHA-256 y tamaño de los bytes
entregados, actor y fecha, y DEBE auditarse (RF-EMI-007).

Si existe una plantilla activa del tipo institucional `constancia` (constancia) o `certificate`
(certificado), su contenido con marcadores del catálogo cerrado DEBE usarse como cuerpo; si no,
se usa un texto base.

#### Scenario: Constancia de una matrícula vigente

- **GIVEN** una matrícula activa sin requisitos obligatorios pendientes
- **WHEN** la secretaría emite la constancia
- **THEN** recibe un PDF válido con folio y código de verificación impresos
- **AND** queda un registro de emisión con el SHA-256 del PDF y sin archivo almacenado

#### Scenario: Certificado de un ciclo abierto

- **GIVEN** una matrícula cuyo ciclo sigue activo
- **WHEN** se solicita el certificado de estudios
- **THEN** el sistema responde 400 y no registra emisión ni consume folio

#### Scenario: Verificación de integridad de la copia

- **GIVEN** un documento emitido y descargado
- **WHEN** un usuario con `document.read` sobre el estudiante envía la copia a verificar
- **THEN** el sistema responde 204 si el SHA-256 coincide y 400 si la copia fue alterada

#### Scenario: Emisión fuera de alcance

- **GIVEN** un usuario con `document.issue` sobre otro estudiante
- **WHEN** intenta emitir para este estudiante
- **THEN** el sistema responde 403 y audita `documents.official_issuance.denied`
