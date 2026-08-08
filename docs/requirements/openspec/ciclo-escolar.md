# ciclo-escolar

## ADDED Requirements

### Requirement: Registro del ciclo escolar

El sistema DEBE permitir registrar ciclos escolares con su identificación, su fecha de inicio
y su fecha de finalización. Los ciclos NO DEBEN solaparse entre sí.

#### Scenario: Alta de un ciclo

- **GIVEN** un establecimiento sin ciclo registrado para un año
- **WHEN** un usuario autorizado registra el ciclo con sus fechas
- **THEN** el sistema lo crea en estado de preparación

### Requirement: Estados del ciclo

Cada ciclo DEBE tener un estado explícito entre preparación, activo y cerrado. Solo un ciclo
DEBE poder estar activo a la vez. Un ciclo en preparación DEBE admitir la configuración de su
estructura sin que esa información sea visible para docentes ni encargados. Un ciclo cerrado
NO DEBE admitir escritura de información académica.

#### Scenario: Preparación del ciclo siguiente durante el ciclo en curso

- **GIVEN** un ciclo activo y otro en preparación
- **WHEN** un usuario autorizado configura la estructura del ciclo en preparación
- **THEN** el sistema acepta los cambios
- **AND** esa información no aparece en los portales de docentes ni de encargados

#### Scenario: Intento de activar un segundo ciclo

- **GIVEN** un ciclo ya activo
- **WHEN** se intenta activar otro
- **THEN** el sistema rechaza la operación indicando que debe cerrarse el vigente

### Requirement: Apertura del ciclo

La activación de un ciclo DEBE requerir que su estructura académica esté completa: grados,
secciones, plan de estudios por grado y unidades de evaluación configuradas. El sistema DEBE
informar qué elementos faltan cuando la activación no proceda.

#### Scenario: Activación con estructura incompleta

- **GIVEN** un ciclo en preparación sin plan de estudios definido para un grado
- **WHEN** se intenta activarlo
- **THEN** el sistema rechaza la activación e indica el grado sin plan de estudios

### Requirement: Cierre del ciclo

El cierre de un ciclo DEBE requerir que todas las unidades de evaluación estén cerradas y que
la ventana de recuperación haya vencido. El cierre DEBE disparar el congelamiento de los
resultados académicos definido en la capacidad de resultados, y DEBE registrarse en la
bitácora con el usuario responsable.

#### Scenario: Cierre con unidades abiertas

- **GIVEN** un ciclo activo con una unidad de evaluación aún abierta
- **WHEN** se intenta cerrarlo
- **THEN** el sistema rechaza la operación e indica la unidad pendiente

#### Scenario: Cierre correcto

- **GIVEN** un ciclo con todas sus unidades cerradas y la ventana de recuperación vencida
- **WHEN** un usuario autorizado lo cierra
- **THEN** los resultados académicos quedan congelados
- **AND** el cierre queda registrado en la bitácora

### Requirement: Reapertura excepcional

El sistema DEBE permitir reabrir un ciclo cerrado únicamente a un usuario con permiso de
autorización académica, exigiendo un motivo y dejando registro en la bitácora. La reapertura
NO DEBE descartar los resultados congelados: estos DEBEN conservarse y el nuevo cierre DEBE
generar un resultado adicional que preserve la traza del anterior.

#### Scenario: Corrección de un error detectado tras el cierre

- **GIVEN** un ciclo cerrado en el que se detectó un error de calificación
- **WHEN** un usuario con permiso de autorización académica lo reabre indicando el motivo
- **THEN** el sistema registra la reapertura en la bitácora
- **AND** conserva los resultados congelados previos

### Requirement: Conservación de la información histórica

La información de ciclos cerrados NO DEBE eliminarse ni depurarse. El sistema DEBE mantenerla
consultable indefinidamente para los usuarios cuyo alcance la comprenda.

#### Scenario: Consulta de un ciclo de años anteriores

- **GIVEN** un ciclo cerrado hace varios años
- **WHEN** un usuario autorizado consulta su información académica
- **THEN** el sistema la presenta completa

### Requirement: Clonación hacia el ciclo siguiente

El sistema DEBE permitir crear un ciclo nuevo copiando la estructura académica de un ciclo
anterior, incluyendo grados, jornadas, secciones y plan de estudios. Las asignaciones de
docentes PODRÁN incluirse o no en la clonación, a elección de quien la ejecuta. El ciclo
resultante DEBE quedar en estado de preparación y ser editable antes de su activación.

La clonación NO DEBE crear vínculos vivos con el ciclo de origen: un cambio posterior en el
ciclo nuevo NO DEBE alterar el anterior.

#### Scenario: Clonación con asignaciones docentes

- **GIVEN** un ciclo con su estructura y sus asignaciones docentes completas
- **WHEN** un usuario autorizado lo clona incluyendo las asignaciones
- **THEN** el ciclo nuevo queda en preparación con la misma estructura y las mismas
  asignaciones
- **AND** puede editarse antes de activarse

#### Scenario: Independencia entre ciclos clonados

- **GIVEN** un ciclo creado por clonación de otro
- **WHEN** se modifica la estructura del ciclo nuevo
- **THEN** el ciclo de origen permanece sin cambios
