# credencial-estudiantil

## ADDED Requirements

### Requirement: Emisión de credencial con identificador opaco

El sistema DEBE emitir para cada estudiante una credencial con un código QR que codifique
únicamente un identificador opaco, generado aleatoriamente, que no DEBE ser derivable del
código estudiantil, del número de identificación ni de ningún otro dato personal. El código
QR NO DEBE codificar nombres, fechas de nacimiento, información de contacto, información
académica ni información de salud.

#### Scenario: Emisión para un estudiante inscrito

- **GIVEN** un estudiante con inscripción activa y sin credencial vigente
- **WHEN** un usuario autorizado emite su credencial
- **THEN** el sistema genera un identificador opaco único y lo asocia al estudiante
- **AND** la credencial queda en estado vigente

#### Scenario: El identificador no revela datos personales

- **GIVEN** una credencial emitida
- **WHEN** se inspecciona el contenido codificado en el código QR
- **THEN** contiene solo el identificador opaco
- **AND** no permite deducir el código estudiantil ni ningún dato personal del portador

### Requirement: Contenido visible de la credencial

El material impreso de la credencial DEBE mostrar el nombre del estudiante, su fotografía, su
grado y sección, el ciclo escolar y el nombre de la institución. NO DEBE mostrar información
de salud, dirección del domicilio ni datos de contacto de la familia.

#### Scenario: Generación del material imprimible

- **GIVEN** un estudiante con credencial vigente
- **WHEN** un usuario autorizado genera el material imprimible
- **THEN** el documento incluye nombre, fotografía, grado y sección, ciclo e institución
- **AND** no incluye información de salud ni datos de contacto de la familia

### Requirement: Vigencia y revocación

El sistema DEBE mantener el estado de cada credencial como vigente o revocada, y DEBE permitir
a un usuario autorizado revocarla de forma inmediata indicando un motivo. Una credencial
revocada NO DEBE poder usarse para registrar movimientos.

#### Scenario: Revocación por extravío

- **GIVEN** una credencial vigente reportada como extraviada
- **WHEN** un usuario autorizado la revoca indicando el motivo
- **THEN** la credencial queda en estado revocado con su motivo y la identidad de quien revocó
- **AND** cualquier intento posterior de usarla es rechazado

### Requirement: Reposición sin pérdida de historial

El sistema DEBE permitir emitir una credencial de reposición generando un identificador opaco
nuevo, conservando en el expediente del estudiante el registro de todas sus credenciales
anteriores con sus fechas de emisión, revocación y motivos.

#### Scenario: Reposición tras extravío

- **GIVEN** un estudiante cuya credencial fue revocada
- **WHEN** un usuario autorizado emite la reposición
- **THEN** el sistema genera un identificador opaco distinto del anterior
- **AND** el historial de credenciales del estudiante conserva la credencial revocada

### Requirement: Persistencia de los movimientos ante revocación

Los movimientos registrados con una credencial que posteriormente sea revocada DEBEN
permanecer válidos e inalterados. La revocación DEBE aplicar únicamente hacia adelante.

#### Scenario: Revocación posterior a movimientos registrados

- **GIVEN** un estudiante con movimientos registrados durante la semana
- **WHEN** su credencial se revoca por extravío
- **THEN** los movimientos previos permanecen sin cambios
- **AND** el estado diario derivado de los días anteriores no se modifica

### Requirement: Resolución de identificador

El sistema DEBE resolver un identificador opaco al estudiante correspondiente únicamente para
usuarios y procesos autorizados. Ante un identificador desconocido, revocado o perteneciente
a un estudiante sin inscripción activa, el sistema DEBE rechazar la operación indicando la
causa sin revelar información de ningún estudiante.

#### Scenario: Identificador desconocido

- **GIVEN** un código QR que no corresponde a ninguna credencial emitida
- **WHEN** un operador lo escanea
- **THEN** el sistema informa que la credencial no es reconocida
- **AND** no muestra información de ningún estudiante

#### Scenario: Estudiante retirado

- **GIVEN** una credencial vigente cuyo estudiante fue retirado del establecimiento
- **WHEN** un operador la escanea
- **THEN** el sistema rechaza el movimiento indicando que el estudiante no tiene inscripción
  activa
