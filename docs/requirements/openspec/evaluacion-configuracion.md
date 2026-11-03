# evaluacion-configuracion

## ADDED Requirements

### Requirement: Estructura de unidades del ciclo

El sistema DEBE permitir configurar, para cada ciclo escolar, la cantidad de unidades de
evaluación y las fechas de inicio y finalización de cada una. La cantidad NO DEBE estar fijada
en el código. Las unidades de un mismo ciclo NO DEBEN solaparse en el tiempo.

#### Scenario: Configuración de cuatro unidades

- **GIVEN** un ciclo escolar sin unidades configuradas
- **WHEN** un usuario autorizado define cuatro unidades con sus fechas
- **THEN** el sistema las registra como la estructura de evaluación de ese ciclo

#### Scenario: Unidades solapadas

- **GIVEN** un ciclo con una unidad ya configurada
- **WHEN** se intenta crear otra cuyo rango de fechas se solapa con la anterior
- **THEN** el sistema rechaza la operación indicando el conflicto

### Requirement: Ventana de captura de notas

Cada unidad DEBE tener una ventana de captura con fecha de apertura y fecha de cierre,
independiente de las fechas lectivas de la unidad. Fuera de esa ventana el sistema NO DEBE
aceptar el registro ni la modificación de notas de esa unidad.

#### Scenario: Captura dentro de la ventana

- **GIVEN** una unidad cuya ventana de captura está abierta
- **WHEN** un docente registra una nota de una subárea a su cargo
- **THEN** el sistema la acepta

#### Scenario: Captura con la ventana cerrada

- **GIVEN** una unidad cuya ventana de captura ya cerró
- **WHEN** un docente intenta registrar una nota de esa unidad
- **THEN** el sistema rechaza la operación indicando que la ventana está cerrada

### Requirement: Ventana de recuperación

El sistema DEBE permitir configurar una ventana de recuperación con sus propias fechas de
apertura y cierre, independiente de las ventanas de captura de las unidades. Las notas de
recuperación NO DEBEN registrarse fuera de esa ventana.

#### Scenario: Recuperación fuera de fecha

- **GIVEN** una ventana de recuperación aún no abierta
- **WHEN** un docente intenta registrar una nota de recuperación
- **THEN** el sistema rechaza la operación

### Requirement: Brecha excepcional autorizada

El sistema DEBE permitir a un usuario con permiso de autorización académica habilitar una
brecha excepcional de captura, acotada a un docente, una subárea, una unidad y un plazo
determinado, exigiendo un motivo. La brecha DEBE registrarse en la bitácora y DEBE expirar
sola al vencer su plazo, sin requerir que alguien la cierre.

#### Scenario: Docente que no alcanzó a subir notas

- **GIVEN** una unidad con la ventana de captura cerrada
- **WHEN** un usuario con permiso de autorización académica habilita una brecha para un
  docente y una subárea indicando el motivo
- **THEN** ese docente puede registrar las notas de esa subárea durante el plazo concedido
- **AND** ningún otro docente obtiene acceso por esa brecha

#### Scenario: Expiración automática

- **GIVEN** una brecha excepcional cuyo plazo venció
- **WHEN** el docente intenta registrar una nota
- **THEN** el sistema rechaza la operación sin que nadie haya tenido que revocar la brecha

### Requirement: Configuración global heredable

El sistema DEBE mantener una configuración global de evaluación que sirva como valor inicial
para los ciclos nuevos. Un ciclo PODRÁ apartarse de la configuración global editando sus
propios valores, y esa edición NO DEBE alterar la configuración global ni la de otros ciclos.

#### Scenario: Ciclo que se aparta del valor global

- **GIVEN** una configuración global de cuatro unidades
- **WHEN** un usuario autorizado edita un ciclo determinado para que tenga otra cantidad
- **THEN** ese ciclo conserva su propia configuración
- **AND** los demás ciclos y la configuración global permanecen sin cambios

### Requirement: Clonación de la configuración entre ciclos

El sistema DEBE permitir crear la configuración de un ciclo copiando la de un ciclo anterior,
incluyendo unidades, ventanas y estructura académica asociada, con las fechas trasladadas al
ciclo destino. La configuración clonada DEBE quedar editable antes de su activación.

#### Scenario: Preparación del ciclo siguiente

- **GIVEN** un ciclo con su configuración completa
- **WHEN** un usuario autorizado clona esa configuración hacia el ciclo siguiente
- **THEN** el nuevo ciclo queda con la misma estructura y las fechas trasladadas
- **AND** puede editarse antes de activarse

### Requirement: Estados de la unidad

Cada unidad DEBE tener un estado explícito que determine si admite captura de notas y si sus
resultados son definitivos. El cambio de estado DEBE registrarse en la bitácora con el usuario
responsable y el momento.

#### Scenario: Cierre de una unidad

- **GIVEN** una unidad con su ventana de captura vencida
- **WHEN** un usuario autorizado la cierra
- **THEN** el sistema registra el cambio de estado en la bitácora
- **AND** las notas de esa unidad dejan de admitir modificación salvo brecha excepcional
