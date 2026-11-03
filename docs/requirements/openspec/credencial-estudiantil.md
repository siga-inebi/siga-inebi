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

## MODIFIED Requirements

Cambio registrado en `docs/requirements/change-control.md` (CC-001). Antes, el código QR solo
viajaba en la respuesta de emisión y reimprimir exigía revocar y emitir de nuevo (#631, AS2).

### Requirement: Reimpresión del código QR con permiso propio

El sistema DEBE permitir volver a obtener el código QR de una credencial vigente sin revocarla,
únicamente a usuarios con el permiso `attendance.credential.print` y alcance sobre el
estudiante. Cada reimpresión DEBE quedar en la bitácora con el actor y el estudiante, y el
asiento NO DEBE contener el identificador opaco. Revocar queda reservado para extravío, retiro
o cualquier causa que invalide la credencial (RF-CRE-003).

#### Scenario: Reimpresión de una credencial vigente

- **GIVEN** un estudiante con credencial vigente
- **WHEN** un usuario con `attendance.credential.print` y alcance solicita su QR
- **THEN** el sistema devuelve la imagen del mismo QR emitido
- **AND** registra `attendance.credential.qr_revealed` sin el identificador opaco

#### Scenario: Reimpresión sin permiso

- **GIVEN** un usuario con `attendance.credential.issue` pero sin `attendance.credential.print`
- **WHEN** solicita el QR de una credencial vigente
- **THEN** el sistema rechaza la operación con 403

### Requirement: Formato imprimible de la credencial

El material imprimible DEBE generarse en el servidor como un wireframe de 96 × 54 mm (16:9) a
300 dpi: fondo transparente, guía de corte, nombre de la institución arriba, recuadro de
fotografía a la izquierda (o un recuadro punteado «FOTO» si no hay fotografía), nombre, grado y
sección y ciclo escolar al centro, y el código QR a la derecha. Solo DEBE mostrar los campos del
requerimiento «Contenido visible de la credencial». El diseño gráfico se agrega encima, fuera del
sistema.

### Requirement: Exportación individual y por lote

El sistema DEBE exportar carnés de 1 a 100 estudiantes distintos por solicitud, en PDF (hoja
carta con 8 carnés a tamaño real y marcas de corte), en PNG (un solo estudiante) o en un ZIP con
un PNG por estudiante. Antes de exportar DEBE ofrecer una vista previa que clasifique cada
estudiante como listo, por emitir u omitido con su motivo, sin emitir nada. Al confirmar, DEBE
emitir las credenciales faltantes solo donde el usuario tenga además
`attendance.credential.issue`, y omitir el resto. La exportación DEBE auditarse con la cantidad
y los estudiantes, nunca con los identificadores opacos.

La selección se hace en el diálogo «Exportar carnés» del listado de estudiantes, no en la tabla
principal: filtros en cascada nivel → grado → sección (del ciclo activo, por matrícula activa) más
búsqueda por nombre o código; la elección uno a uno se conserva entre filtros y páginas, y
«Seleccionar los N del filtro» solo se ofrece cuando el filtro no supera los 100.

#### Scenario: Exportación por lote con estudiantes sin credencial

- **GIVEN** una selección con un estudiante con credencial vigente, uno sin credencial y uno sin
  inscripción activa
- **WHEN** un usuario con permisos de impresión y emisión confirma la exportación en PDF
- **THEN** el sistema emite la credencial faltante y devuelve un PDF con dos carnés
- **AND** omite al estudiante sin inscripción activa indicando el motivo

#### Scenario: Vista previa sin efectos

- **GIVEN** una selección con estudiantes sin credencial
- **WHEN** el usuario solicita la vista previa
- **THEN** el sistema informa qué se emitiría
- **AND** no emite ninguna credencial
