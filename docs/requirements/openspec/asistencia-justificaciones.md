# asistencia-justificaciones

## ADDED Requirements

### Requirement: Solicitud de justificación por el encargado

El sistema DEBE permitir a un encargado registrado solicitar la justificación de una
inasistencia o de una llegada tardía de un estudiante que tenga asociado, indicando la fecha,
el tipo de situación y un motivo tomado de una lista configurable, con la posibilidad de
adjuntar documentos de respaldo. La solicitud DEBE quedar en estado pendiente hasta su
resolución.

#### Scenario: Solicitud con respaldo

- **GIVEN** un encargado con un estudiante asociado que estuvo ausente el día anterior
- **WHEN** registra la solicitud indicando fecha, motivo y adjuntando una constancia médica
- **THEN** el sistema crea la solicitud en estado pendiente
- **AND** conserva el documento asociado a la solicitud

### Requirement: Alcance del encargado

Un encargado NO DEBE poder consultar ni justificar ausencias de estudiantes que no tenga
asociados. El sistema DEBE verificar la asociación vigente en cada operación.

#### Scenario: Intento sobre un estudiante ajeno

- **GIVEN** un encargado sin asociación con un estudiante determinado
- **WHEN** intenta registrar una justificación para ese estudiante
- **THEN** el sistema rechaza la operación
- **AND** no revela información alguna sobre ese estudiante

### Requirement: Ventana de justificación

El sistema DEBE aceptar solicitudes únicamente dentro de la ventana configurada, contada desde
la fecha de la inasistencia. Fuera de esa ventana, la solicitud DEBE rechazarse indicando el
plazo vencido, salvo que un usuario con permiso elevado la registre en nombre del encargado
dejando constancia del motivo de la excepción.

#### Scenario: Solicitud fuera de plazo

- **GIVEN** una ventana de justificación de cinco días hábiles
- **WHEN** un encargado intenta justificar una ausencia de hace dos semanas
- **THEN** el sistema rechaza la solicitud indicando que el plazo venció

### Requirement: Revisión y resolución

El sistema DEBE permitir a un usuario autorizado aprobar o rechazar una solicitud pendiente,
exigiendo un comentario cuando la rechace. La resolución DEBE registrar la identidad de quien
resolvió y el momento en que lo hizo. Una solicitud resuelta NO DEBE poder modificarse; para
corregir una resolución se registra una nueva revisión que deja trazabilidad de ambas.

#### Scenario: Rechazo con comentario

- **GIVEN** una solicitud pendiente sin documento de respaldo
- **WHEN** un usuario autorizado la rechaza indicando el motivo
- **THEN** el sistema registra el rechazo con su comentario, autor y fecha
- **AND** el encargado puede consultar el estado y el motivo desde su perfil

### Requirement: Efecto sobre el estado derivado

La aprobación de una justificación DEBE cambiar el estado derivado del día a ausencia
justificada o a llegada tardía justificada, según corresponda, sin eliminar ni modificar los
eventos de movimiento del día ni el registro original de la inasistencia. El rechazo NO DEBE
alterar el estado derivado.

#### Scenario: Aprobación de una ausencia

- **GIVEN** un día con estado derivado de ausencia pendiente de justificar
- **WHEN** se aprueba la justificación correspondiente
- **THEN** el estado derivado del día pasa a ausencia justificada
- **AND** el registro original de la inasistencia permanece consultable

### Requirement: Notificación del cambio de estado

El sistema DEBE notificar al encargado cuando su solicitud cambie de estado, indicando el
resultado y, cuando exista, el comentario de quien resolvió.

#### Scenario: Notificación tras resolución

- **GIVEN** una solicitud pendiente de un encargado
- **WHEN** un usuario autorizado la resuelve
- **THEN** el encargado recibe la notificación con el resultado y el comentario asociado

### Requirement: Permiso prospectivo de salida anticipada o ingreso tardío

El sistema DEBE distinguir un permiso, que se solicita antes de que el hecho ocurra, de una
justificación, que se presenta después. Un encargado con asociación vigente o un usuario
autorizado DEBE poder registrar un permiso de salida anticipada o de ingreso tardío para una
fecha determinada, indicando el motivo y el horario previsto.

Un permiso DEBE quedar en estado pendiente hasta que un usuario autorizado lo apruebe o lo
rechace. Un permiso aprobado y vigente DEBE evitar que el movimiento correspondiente genere
alertas de inconsistencia y NO DEBE reducir el porcentaje de asistencia de ese día.

#### Scenario: Salida anticipada por cita médica

- **GIVEN** un encargado que registra un permiso de salida anticipada para el día siguiente
- **WHEN** un usuario autorizado lo aprueba
- **THEN** el permiso queda vigente para esa fecha
- **AND** la salida anticipada de ese estudiante no genera alerta de inconsistencia

#### Scenario: Ingreso tardío autorizado

- **GIVEN** un estudiante con un permiso de ingreso tardío aprobado para una fecha
- **WHEN** registra su ingreso después de la hora límite de su jornada
- **THEN** el estado derivado del día no lo penaliza como llegada tardía

#### Scenario: Permiso pendiente al momento del movimiento

- **GIVEN** un permiso solicitado y aún no aprobado
- **WHEN** el estudiante sale antes del horario de cierre
- **THEN** el sistema registra el movimiento y lo trata como salida anticipada sin autorizar

### Requirement: Efecto del permiso sobre el cierre declarado

El sistema DEBE excluir del cierre declarado por sección a los estudiantes que tengan un
permiso de salida anticipada aprobado y vigente para esa fecha, informándolo en el resumen
previo a la confirmación.

#### Scenario: Cierre de sección con un permiso vigente

- **GIVEN** una sección donde un estudiante tiene permiso de salida anticipada aprobado
- **WHEN** un docente declara el cierre de esa sección
- **THEN** el sistema omite a ese estudiante y lo informa como omitido por permiso vigente

### Requirement: Confidencialidad de los respaldos

Los documentos adjuntos a una justificación PUEDEN contener información de salud, por lo que
DEBEN ser accesibles únicamente para el encargado que los cargó y para los usuarios con
permiso de revisión. Toda lectura de un documento adjunto DEBE quedar registrada en la
bitácora de auditoría.

#### Scenario: Lectura auditada de una constancia médica

- **GIVEN** una solicitud con una constancia médica adjunta
- **WHEN** un usuario con permiso de revisión abre el documento
- **THEN** el sistema registra en bitácora la lectura con el usuario, la fecha y la hora
