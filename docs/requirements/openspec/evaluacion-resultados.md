# evaluacion-resultados

## ADDED Requirements

### Requirement: Nota final de la subárea

El sistema DEBE calcular la nota final de cada subárea como el promedio de las notas de las
unidades del ciclo. Mientras el ciclo esté abierto, el valor DEBE derivarse de las notas
registradas y recalcularse ante cualquier corrección.

#### Scenario: Promedio de las unidades

- **GIVEN** un estudiante con todas las unidades calificadas en una subárea
- **WHEN** se calcula su nota final
- **THEN** el resultado es el promedio de esas notas

### Requirement: Punto único de redondeo

El sistema DEBE conservar la precisión completa en los cálculos intermedios y DEBE aplicar el
redondeo una sola vez, sobre el resultado final. Cuando la fracción sea exactamente la mitad,
el redondeo DEBE ser hacia el entero superior. El valor presentado al usuario y el valor
comparado contra el umbral de aprobación DEBEN ser el mismo número.

#### Scenario: Fracción exacta de un medio

- **GIVEN** un estudiante cuyo promedio de unidades es 59.5
- **WHEN** se calcula su nota final
- **THEN** el resultado es 60

#### Scenario: Coherencia entre boleta y estado

- **GIVEN** una nota final calculada
- **WHEN** se presenta en la boleta y se evalúa la aprobación
- **THEN** ambas operaciones usan el mismo valor redondeado

### Requirement: Aprobación de la subárea

El sistema DEBE considerar aprobada una subárea cuando la nota final alcance al menos sesenta
puntos, conforme al Reglamento de Evaluación de los Aprendizajes. El umbral NO DEBE ser
configurable por la institución.

#### Scenario: Nota final en el umbral

- **GIVEN** un estudiante con nota final de exactamente sesenta en una subárea
- **WHEN** se determina su condición
- **THEN** la subárea queda aprobada

### Requirement: Elegibilidad de recuperación

El sistema DEBE determinar si un estudiante tiene derecho a recuperación evaluando tres
condiciones de forma conjunta: que su porcentaje de asistencia del ciclo sea de al menos
ochenta por ciento; que la cantidad de subáreas reprobadas no supere tres cuando el total de
subáreas de su grado sea nueve o menos, ni cuatro cuando el total supere nueve; y que no haya
utilizado ya su oportunidad de recuperación en ese ciclo. El límite DEBE calcularse a partir
de la cantidad de subáreas configurada para el grado y el ciclo, no de un valor fijo.

#### Scenario: Estudiante elegible

- **GIVEN** un estudiante con asistencia del ochenta y cinco por ciento, dos subáreas
  reprobadas y un plan de estudios de ocho subáreas
- **WHEN** se evalúa su elegibilidad
- **THEN** el sistema lo declara con derecho a recuperación

#### Scenario: Asistencia insuficiente

- **GIVEN** un estudiante con asistencia del setenta y cinco por ciento y dos subáreas
  reprobadas
- **WHEN** se evalúa su elegibilidad
- **THEN** el sistema lo declara sin derecho a recuperación e indica la asistencia como causa

#### Scenario: Exceso de subáreas reprobadas

- **GIVEN** un estudiante con cinco subáreas reprobadas en un plan de doce subáreas
- **WHEN** se evalúa su elegibilidad
- **THEN** el sistema lo declara sin derecho a recuperación e indica la cantidad como causa

### Requirement: Registro de la nota de recuperación

El sistema DEBE permitir registrar la nota de recuperación de una subárea reprobada,
únicamente para estudiantes declarados elegibles y dentro de la ventana de recuperación. La
nota de recuperación DEBE conservarse junto a la nota final original sin sustituirla, y la
condición de la subárea DEBE recalcularse a partir de la recuperación.

#### Scenario: Recuperación aprobada

- **GIVEN** un estudiante elegible con una subárea reprobada
- **WHEN** se registra una nota de recuperación de al menos sesenta puntos
- **THEN** la subárea pasa a condición aprobada por recuperación
- **AND** la nota final original permanece consultable

#### Scenario: Intento sobre un estudiante no elegible

- **GIVEN** un estudiante sin derecho a recuperación
- **WHEN** se intenta registrar una nota de recuperación
- **THEN** el sistema rechaza la operación indicando la causa de la no elegibilidad

### Requirement: Promoción al grado siguiente

El sistema DEBE determinar la promoción de un estudiante del nivel medio exigiendo al menos
sesenta puntos en cada una de las subáreas de su plan de estudios, considerando las notas de
recuperación cuando existan. El sistema NO DEBE promover con base en un promedio general de
todas las subáreas.

#### Scenario: Una subárea reprobada impide la promoción

- **GIVEN** un estudiante con promedio general superior a setenta y una subárea con cincuenta
  y cinco puntos tras la recuperación
- **WHEN** se determina su condición final
- **THEN** el sistema lo declara no promovido

#### Scenario: Todas las subáreas aprobadas

- **GIVEN** un estudiante con al menos sesenta puntos en cada subárea
- **WHEN** se determina su condición final
- **THEN** el sistema lo declara promovido al grado inmediato superior

### Requirement: Congelamiento al cierre del ciclo

Al cerrar un ciclo escolar, el sistema DEBE fijar las notas finales, las condiciones de
aprobación y la condición de promoción como valores definitivos. Esos valores NO DEBEN
recalcularse por cambios posteriores en la configuración de evaluación, en la estructura
académica ni en los parámetros del sistema.

#### Scenario: Cambio de configuración posterior al cierre

- **GIVEN** un ciclo cerrado con resultados fijados
- **WHEN** se modifica la configuración de unidades de la institución
- **THEN** los resultados del ciclo cerrado permanecen inalterados

#### Scenario: Corrección posterior al congelamiento

- **GIVEN** un ciclo cerrado y una nota que se determinó errónea
- **WHEN** un usuario con permiso de autorización académica la corrige mediante brecha
  excepcional
- **THEN** el sistema registra la corrección y el nuevo resultado
- **AND** conserva el resultado congelado anterior con la traza del cambio

### Requirement: Boleta de calificaciones

El sistema DEBE generar la boleta de un estudiante con las notas de cada unidad por subárea,
la nota final, la condición de cada subárea y la condición de promoción cuando el ciclo esté
cerrado. Los valores impresos DEBEN coincidir con los que el sistema usó para determinar cada
condición.

#### Scenario: Boleta de un ciclo cerrado

- **GIVEN** un estudiante de un ciclo cerrado
- **WHEN** se genera su boleta
- **THEN** incluye notas por unidad, nota final, condición por subárea y condición de promoción

### Requirement: Trazabilidad del resultado

El sistema DEBE permitir a un usuario autorizado consultar, para cualquier nota final, las
notas de unidad que la originaron, las correcciones aplicadas con su motivo y autor, y la nota
de recuperación cuando exista.

#### Scenario: Auditoría de una nota final

- **GIVEN** una nota final con una corrección aplicada durante el ciclo
- **WHEN** un usuario autorizado consulta su trazabilidad
- **THEN** el sistema presenta las notas de unidad, la corrección con su motivo y su autor
