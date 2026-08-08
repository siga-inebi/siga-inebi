# asistencia-jornada

## ADDED Requirements

### Requirement: Parámetros de jornada configurables

El sistema DEBE permitir configurar, por jornada y por ciclo escolar, la hora límite de
ingreso, la tolerancia de llegada tardía, la hora de cierre de jornada, la ventana de
supresión de duplicados y los días lectivos. Los cambios DEBEN registrarse en bitácora con el
usuario responsable y la fecha desde la que rigen. Ninguno de estos valores DEBE requerir
intervención de desarrollo para modificarse.

#### Scenario: Dos jornadas con horarios distintos

- **GIVEN** una institución con jornada matutina y jornada vespertina
- **WHEN** se configura una hora límite de ingreso distinta para cada una
- **THEN** el estado diario de cada estudiante se evalúa contra los parámetros de su propia
  jornada

### Requirement: Derivación del estado diario

El sistema DEBE determinar el estado de asistencia de cada estudiante con inscripción activa,
para cada día lectivo, a partir de sus eventos de movimiento y de los parámetros vigentes de
su jornada. El estado NO DEBE capturarse manualmente y DEBE poder recalcularse en cualquier
momento sin alterar los eventos que lo originan.

#### Scenario: Ingreso dentro del horario

- **GIVEN** un estudiante con un ingreso cuya hora de captura es anterior a la hora límite
- **WHEN** se deriva su estado del día
- **THEN** el estado resultante es presente

#### Scenario: Ingreso dentro de la tolerancia

- **GIVEN** un estudiante con un ingreso posterior a la hora límite pero dentro de la
  tolerancia configurada
- **WHEN** se deriva su estado del día
- **THEN** el estado resultante es tarde

#### Scenario: Sin eventos en el día

- **GIVEN** un estudiante con inscripción activa y sin ningún evento en un día lectivo
- **WHEN** se ejecuta el cierre de jornada
- **THEN** el estado resultante es ausente pendiente de justificar

### Requirement: Precedencia entre eventos

Cuando existan varios eventos aplicables al mismo estudiante, tipo de movimiento y jornada, el
sistema DEBE determinar el estado derivado aplicando el siguiente orden de precedencia
descendente: origen de escaneo, origen manual, origen declarado. Dentro del mismo origen
prevalece el evento más reciente por hora de captura. La transmisión NO DEBE influir en la
precedencia. Ningún evento DEBE eliminarse ni sobrescribirse al aplicar esta regla.

#### Scenario: Escaneo prevalece sobre declaración

- **GIVEN** un estudiante con un egreso de origen escaneado y un egreso de origen declarado
  para la misma jornada
- **WHEN** se deriva su estado del día
- **THEN** el estado se calcula con el evento de origen escaneado
- **AND** el evento declarado permanece almacenado y consultable

### Requirement: Cierre de jornada

El sistema DEBE ejecutar un cierre diario a la hora configurada que consolide el estado de
todos los estudiantes con inscripción activa de esa jornada, identificando a quienes no
registraron ingreso y a quienes registraron ingreso sin egreso correspondiente, y generando
las alertas asociadas.

#### Scenario: Permanencia sin cierre

- **GIVEN** un estudiante con ingreso registrado y sin ningún egreso
- **WHEN** se ejecuta el cierre de la jornada
- **THEN** el sistema marca el día con la condición de permanencia sin cierre
- **AND** genera una alerta dirigida al personal del punto de control y al coordinador de aula

### Requirement: Detección de inconsistencias entre fuentes

Cuando los eventos de un estudiante para una misma jornada se contradigan entre sí, el sistema
DEBE conservar todos los eventos sin descartar ninguno, aplicar la regla de precedencia para
determinar el estado derivado y generar una alerta de inconsistencia dirigida al coordinador
de aula que identifique las fuentes en conflicto.

#### Scenario: Egreso declarado para un estudiante sin ingreso

- **GIVEN** un estudiante sin ingreso registrado en el día
- **WHEN** un docente lo incluye en el cierre declarado de su sección
- **THEN** el sistema conserva ambos hechos y genera una alerta de inconsistencia
- **AND** identifica al docente y a la sección como fuente de la declaración

### Requirement: Recálculo ante cambios

El sistema DEBE recalcular el estado derivado de los días afectados cuando se agregue un
evento con fecha anterior, cuando se resuelva una justificación o cuando cambien los
parámetros de la jornada. Los cambios de parámetros DEBEN aplicar únicamente a los días
comprendidos en su vigencia.

#### Scenario: Cambio de tolerancia a mitad de ciclo

- **GIVEN** un ciclo escolar con estados ya derivados bajo una tolerancia de diez minutos
- **WHEN** la tolerancia cambia a quince minutos con vigencia a partir de una fecha
- **THEN** los días anteriores a esa fecha conservan su estado original
- **AND** los días desde esa fecha se derivan con el nuevo valor

### Requirement: Alertas de asistencia

El sistema DEBE generar alertas para estudiantes que no registraron ingreso en el día, para
quienes registraron ingreso sin egreso, para quienes acumulen ausencias frecuentes según el
umbral configurado y para las inconsistencias entre fuentes. Cada alerta DEBE dirigirse a los
roles configurados y DEBE poder marcarse como atendida dejando constancia de quién la atendió.

#### Scenario: Alerta por ausencia no registrada

- **GIVEN** un estudiante sin ingreso registrado al vencer la hora límite de su jornada
- **WHEN** el sistema evalúa las alertas del día
- **THEN** genera una alerta de ausencia dirigida al coordinador de aula correspondiente

### Requirement: Consulta de presencia en tiempo real

El sistema DEBE permitir a los usuarios autorizados consultar, en cualquier momento de la
jornada, qué estudiantes tienen ingreso registrado sin egreso posterior, con filtro por grado
y sección.

#### Scenario: Consulta durante una emergencia

- **GIVEN** una jornada en curso con movimientos registrados
- **WHEN** un usuario autorizado consulta la presencia por sección
- **THEN** el sistema lista los estudiantes con ingreso y sin egreso de esa sección
- **AND** indica la hora de ingreso de cada uno
