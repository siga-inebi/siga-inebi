# evaluacion-calificaciones

## ADDED Requirements

### Requirement: Registro de la nota de unidad

El sistema DEBE permitir registrar, para cada estudiante, subárea y unidad, una única nota
consolidada entregada por el docente. El sistema NO DEBE calcular esa nota a partir de
actividades; la recibe ya calculada.

El modelo de datos DEBE admitir que una nota de unidad se descomponga en actividades en una
fase posterior sin requerir migración de las notas ya registradas.

#### Scenario: Registro de una nota por el docente

- **GIVEN** un docente con una subárea a su cargo y la ventana de captura abierta
- **WHEN** registra la nota de un estudiante para la unidad en curso
- **THEN** el sistema la almacena asociada al estudiante, la subárea, la unidad y el ciclo

### Requirement: Escala y validación de la nota

La nota DEBE expresarse en la escala de cero a cien puntos. El sistema DEBE rechazar valores
fuera de ese rango y valores no numéricos.

#### Scenario: Nota fuera de rango

- **GIVEN** un docente registrando notas
- **WHEN** introduce un valor superior a cien
- **THEN** el sistema rechaza el valor indicando el rango admitido

### Requirement: Distinción entre sin calificar y cero

El sistema DEBE distinguir una nota no registrada de una nota registrada con valor cero. Una
nota no registrada DEBE excluirse de cualquier promedio en curso y NO DEBE presentarse como
cero en las consultas de estudiantes ni de encargados.

#### Scenario: Promedio en curso con notas pendientes

- **GIVEN** un estudiante con dos unidades calificadas y dos sin registrar
- **WHEN** consulta su promedio en curso
- **THEN** el sistema lo calcula únicamente sobre las unidades calificadas
- **AND** indica cuántas unidades están pendientes de registrar

### Requirement: Carga masiva desde archivo

El sistema DEBE permitir registrar notas de forma masiva a partir de un archivo, validando
antes de guardar que cada estudiante exista y pertenezca a la sección, que la subárea
corresponda al alcance del docente, que la unidad admita captura y que los valores estén en la
escala válida. Ninguna fila DEBE guardarse si la validación falla; el sistema DEBE presentar
el detalle de los errores por fila.

#### Scenario: Archivo con filas inválidas

- **GIVEN** un archivo de notas con una fila cuyo estudiante no pertenece a la sección
- **WHEN** el docente lo carga
- **THEN** el sistema no guarda ninguna nota del archivo
- **AND** informa qué fila falló y por qué

#### Scenario: Archivo válido

- **GIVEN** un archivo cuyas filas superan todas las validaciones
- **WHEN** el docente lo carga
- **THEN** el sistema registra todas las notas
- **AND** informa la cantidad de registros incorporados

### Requirement: Corrección de notas registradas

El sistema DEBE permitir modificar una nota mientras la ventana de captura de su unidad esté
abierta. Con la ventana cerrada, la modificación DEBE requerir una brecha excepcional vigente.
Toda modificación DEBE registrar en la bitácora el valor anterior, el nuevo, el usuario y el
momento.

#### Scenario: Corrección con la ventana abierta

- **GIVEN** una nota registrada y una ventana de captura abierta
- **WHEN** el docente la corrige
- **THEN** el sistema acepta el cambio y registra en bitácora el valor anterior y el nuevo

#### Scenario: Corrección con la ventana cerrada y sin brecha

- **GIVEN** una nota de una unidad cerrada, sin brecha excepcional vigente
- **WHEN** el docente intenta corregirla
- **THEN** el sistema rechaza la operación

### Requirement: Alcance del docente sobre las notas

Un docente NO DEBE poder registrar ni consultar notas de subáreas que no tenga asignadas en el
ciclo correspondiente. La evaluación de este alcance DEBE resolverse mediante el mecanismo
único de política definido en la capacidad de alcance.

#### Scenario: Subárea ajena

- **GIVEN** un docente sin asignación sobre una subárea
- **WHEN** intenta registrar una nota de esa subárea
- **THEN** el sistema deniega la operación

### Requirement: Visibilidad de las notas

Un estudiante DEBE poder consultar únicamente sus propias notas y un encargado únicamente las
de los estudiantes con asociación vigente. El sistema NO DEBE exponer a estudiantes ni
encargados las notas de otros estudiantes, ni listados comparativos de la sección.

#### Scenario: Encargado consulta el portal

- **GIVEN** un encargado con un estudiante asociado
- **WHEN** consulta las notas en su portal
- **THEN** el sistema presenta únicamente las de ese estudiante

### Requirement: Seguimiento de notas pendientes

El sistema DEBE permitir a la Dirección y a los coordinadores consultar qué subáreas y
secciones tienen notas pendientes de registrar por unidad, con el docente responsable de cada
una, mientras la ventana de captura esté abierta.

#### Scenario: Consulta antes del cierre de la ventana

- **GIVEN** una unidad con la ventana de captura próxima a cerrar
- **WHEN** la Dirección consulta el estado de la captura
- **THEN** el sistema lista las subáreas sin notas registradas y su docente responsable
