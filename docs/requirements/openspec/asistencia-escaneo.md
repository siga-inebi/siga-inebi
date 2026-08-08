# asistencia-escaneo

## ADDED Requirements

### Requirement: Captura mediada por operador

Todo movimiento capturado en un punto de control DEBE ser registrado por un usuario
autenticado con permiso vigente. El sistema NO DEBE ofrecer ninguna forma de captura por
autoservicio en la que el estudiante registre su propio movimiento sin intervención de
personal de la institución.

#### Scenario: Intento de captura sin sesión

- **GIVEN** un dispositivo sin sesión de usuario autenticada
- **WHEN** se intenta registrar un movimiento
- **THEN** el sistema rechaza la operación y solicita autenticación

### Requirement: Registro de movimiento por escaneo

El sistema DEBE crear un evento de movimiento cuando un operador autorizado escanee una
credencial vigente, persistiendo el estudiante identificado, el tipo de movimiento, la hora de
captura, la hora de registro del servidor, el punto de control, el operador, el origen y la
transmisión.

#### Scenario: Escaneo válido de ingreso

- **GIVEN** un estudiante con inscripción activa y credencial vigente
- **AND** no existe un movimiento del mismo tipo dentro de la ventana de supresión
- **WHEN** el operador escanea la credencial en un punto de control que admite ingresos
- **THEN** el sistema registra un evento de tipo ingreso con origen de escaneo
- **AND** el evento queda asociado al operador y al punto de control

### Requirement: Confirmación visual del portador

Al resolver un escaneo válido, el sistema DEBE presentar al operador la fotografía, el nombre
completo y el grado y sección del estudiante, para que verifique que corresponden a la persona
que tiene enfrente. El sistema NO DEBE mostrar en esa pantalla información de salud,
calificaciones, datos de contacto de la familia ni dirección del domicilio.

#### Scenario: Confirmación tras escaneo válido

- **WHEN** el operador escanea una credencial vigente
- **THEN** el sistema muestra fotografía, nombre completo y grado y sección del estudiante
- **AND** no muestra información de salud, académica ni de contacto

### Requirement: Supresión de duplicados por estudiante

El sistema DEBE rechazar un movimiento del mismo tipo para el mismo estudiante y la misma
jornada dentro de la ventana de supresión configurada, informando al operador la hora del
movimiento ya registrado. La supresión DEBE evaluarse sobre el estudiante, con independencia
del operador, del dispositivo y del punto de control que originen el intento. El intento
rechazado DEBE registrarse como evento auditable sin crear un movimiento de asistencia.

#### Scenario: Dos operadores escanean al mismo estudiante

- **GIVEN** un estudiante con un ingreso registrado hace un minuto por un operador
- **WHEN** un operador distinto, en el mismo punto de control, escanea su credencial
- **THEN** el sistema rechaza el movimiento e informa la hora del ingreso ya registrado
- **AND** deja constancia del intento sin crear un segundo movimiento

### Requirement: Tipos de movimiento admitidos por punto de control

El sistema DEBE permitir configurar, para cada punto de control, qué tipos de movimiento
admite. Un intento de registrar un tipo no admitido en ese punto DEBE ser rechazado. Todo
cambio de configuración DEBE quedar en bitácora con el usuario responsable.

#### Scenario: Tipo no admitido en el punto de control

- **GIVEN** un punto de control configurado para admitir únicamente egresos
- **WHEN** un operador intenta registrar un ingreso desde ese punto
- **THEN** el sistema rechaza la operación indicando que el punto no admite ingresos

### Requirement: Autorización por tipo de movimiento y modo de captura

El sistema DEBE verificar, en cada intento de captura, que el usuario tenga permiso tanto para
el tipo de movimiento como para el modo de captura empleado, y DEBE rechazar el intento
registrándolo como evento auditable cuando falte cualquiera de los dos. El permiso de cierre
declarado por sección DEBE estar restringido al rol docente y a los roles que la institución
autorice explícitamente; NO DEBE concederse a roles de apoyo sin función académica.

#### Scenario: Operador sin permiso para egresos

- **GIVEN** un usuario cuyo rol permite registrar ingresos pero no egresos
- **WHEN** intenta registrar un egreso
- **THEN** el sistema rechaza la operación y deja constancia del intento

#### Scenario: Rol sin función académica

- **GIVEN** un usuario de un rol de apoyo sin permiso de cierre declarado
- **WHEN** intenta declarar el cierre de una sección
- **THEN** el sistema rechaza la operación y deja constancia del intento

### Requirement: Origen y transmisión como atributos independientes

Todo evento DEBE almacenar su origen y su transmisión como atributos separados. La transmisión
NO DEBE afectar la confianza atribuida al evento: un movimiento escaneado y enviado en lote
DEBE tratarse igual que uno escaneado y enviado de inmediato. Ninguna consulta ni reporte DEBE
presentar como equivalentes un movimiento de origen escaneado y uno de origen declarado.

#### Scenario: Escaneo enviado en lote conserva su origen

- **GIVEN** un operador que acumuló movimientos escaneados en un lote
- **WHEN** confirma el lote
- **THEN** cada evento conserva origen de escaneo y transmisión por lote
- **AND** en los reportes se distingue de los movimientos de origen declarado

### Requirement: Autoridad del reloj y hora de captura

El sistema DEBE registrar la hora de registro tomándola del servidor. La hora de captura DEBE
corresponder al instante del escaneo individual y NO DEBE sustituirse por la hora de
confirmación de un lote.

#### Scenario: Lote confirmado después del escaneo

- **GIVEN** un movimiento escaneado a las 12:20 dentro de un lote abierto
- **WHEN** el operador confirma el lote a las 12:35
- **THEN** el evento conserva 12:20 como hora de captura
- **AND** registra 12:35 como hora de registro

### Requirement: Lote de captura recuperable

El sistema DEBE permitir a un operador autorizado acumular movimientos en un lote abierto y
confirmarlos en una sola operación. Si su sesión se interrumpe antes de confirmar, el operador
DEBE poder recuperar el lote pendiente al reanudar sesión, con sus elementos y sus horas de
captura intactos, desde cualquier dispositivo.

#### Scenario: Recuperación tras pérdida de sesión

- **GIVEN** un operador con un lote abierto que contiene doce movimientos escaneados
- **WHEN** pierde la sesión y vuelve a autenticarse
- **THEN** el sistema le presenta el lote pendiente con sus doce elementos
- **AND** cada elemento conserva su hora de captura original

### Requirement: Idempotencia de lotes y elementos

Cada lote y cada elemento DEBEN portar un identificador único generado por el cliente. El
sistema DEBE ignorar sin error el reenvío de elementos o lotes ya registrados, de modo que un
reintento por fallo de red no produzca movimientos duplicados.

#### Scenario: Reenvío por fallo de red

- **GIVEN** un lote ya confirmado por el servidor cuya respuesta no llegó al cliente
- **WHEN** el cliente reenvía el mismo lote con el mismo identificador
- **THEN** el sistema responde con éxito sin crear movimientos adicionales

### Requirement: Cierre declarado por sección

El sistema DEBE permitir a cualquier usuario con permiso de cierre declarado registrar el
egreso de los estudiantes de cualquier sección, con independencia de si tiene esa sección
asignada en su horario. La operación DEBE omitir a los estudiantes que ya tengan un egreso
registrado, a los que tengan una salida anticipada autorizada y a los que estén marcados como
ausentes ese día, y DEBE informar al usuario qué estudiantes fueron omitidos y por qué antes
de confirmar.

En el nivel básico una sección recibe clases de varios docentes a lo largo de la jornada y las
coberturas entre docentes son frecuentes, por lo que restringir esta operación al docente
asignado impediría cerrar la jornada en los casos más comunes.

#### Scenario: Docente que cubre a un colega

- **GIVEN** un docente que no tiene asignada la última franja horaria de una sección
- **WHEN** declara el cierre de esa sección
- **THEN** el sistema registra los egresos declarados
- **AND** deja constancia de que el declarante no era el docente asignado

#### Scenario: Estudiante con egreso ya escaneado

- **GIVEN** una sección donde un estudiante ya tiene egreso registrado por escaneo
- **WHEN** un docente declara el cierre de la sección
- **THEN** el sistema omite a ese estudiante y lo informa en el resumen previo a la
  confirmación
- **AND** el egreso escaneado permanece sin cambios

### Requirement: Trazabilidad y confirmación del cierre por cobertura

Todo evento generado por cierre declarado DEBE registrar la identidad del declarante, la
sección y la franja horaria cerrada. El sistema DEBE derivar y almacenar si el declarante era
el docente asignado a esa franja según el horario vigente, de modo que la proporción de
cierres por cobertura sea consultable sin inspeccionar los horarios a mano.

Cuando el declarante no sea el docente asignado, el sistema DEBE solicitar una confirmación
adicional que muestre la sección, el grado y la cantidad de estudiantes afectados antes de
registrar los eventos. Esta confirmación NO DEBE bloquear la operación.

#### Scenario: Confirmación adicional al cubrir

- **GIVEN** un docente que declara el cierre de una sección que no tiene asignada
- **WHEN** confirma la operación
- **THEN** el sistema muestra sección, grado y cantidad de estudiantes afectados
- **AND** registra los eventos solo después de la confirmación explícita

#### Scenario: Consulta de cierres por cobertura

- **GIVEN** un ciclo con cierres declarados por docentes asignados y por docentes que cubrieron
- **WHEN** un usuario autorizado consulta el indicador de cobertura del período
- **THEN** el sistema informa la proporción de cierres declarados por un docente distinto al
  asignado

### Requirement: Registro manual autorizado

El sistema DEBE permitir a un usuario con permiso elevado registrar un movimiento sin escaneo,
exigiendo un motivo tomado de una lista configurable, y DEBE almacenar el evento con origen
manual junto con la identidad de quien lo autorizó. Los eventos manuales DEBEN ser
distinguibles de los demás en toda consulta y reporte.

#### Scenario: Estudiante sin credencial a mano

- **GIVEN** un estudiante que olvidó su credencial
- **WHEN** un usuario con permiso elevado registra su ingreso indicando el motivo
- **THEN** el sistema crea un evento con origen manual, el motivo y la identidad del
  autorizador

### Requirement: Rendimiento del punto de control

El percentil 95 del tiempo transcurrido entre la lectura del código y la presentación de la
confirmación visual DEBE ser menor o igual a 2 segundos, medido sobre la infraestructura
objetivo descrita en el contexto del proyecto, con el número de operadores concurrentes y la
tasa de escaneo por operador definidos como parámetros institucionales.

#### Scenario: Medición en condiciones de pico

- **GIVEN** la infraestructura objetivo y el número de operadores concurrentes acordado
- **WHEN** se sostiene la tasa de escaneo de pico durante diez minutos
- **THEN** el percentil 95 de la latencia de confirmación se mantiene en 2 segundos o menos
