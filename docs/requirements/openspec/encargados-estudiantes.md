# encargados-estudiantes

## ADDED Requirements

### Requirement: Consultar y vincular estudiantes desde el encargado (RF-EXP-004, RF-ALC-001)

La ficha del encargado DEBE permitir consultar sus relaciones actuales e históricas
con estudiantes mediante paginación en servidor, sin mostrar ni contar estudiantes
fuera del alcance de lectura del actor. La creación de un vínculo DEBE exigir además
edición sobre el estudiante y preservar el historial, reglas de principal y auditoría.

#### Scenario: Consulta con alcance parcial

- **GIVEN** un encargado con relaciones hacia estudiantes de distintos alcances
- **WHEN** un actor consulta su ficha con permiso de lectura
- **THEN** solo recibe relaciones y su total dentro del alcance autorizado
- **AND** puede paginar y abrir sus expedientes por UUID

#### Scenario: Crear un vínculo desde el encargado

- **GIVEN** un actor con lectura y edición sobre un estudiante activo
- **WHEN** selecciona un encargado activo y confirma el parentesco
- **THEN** se crea y audita una relación, manteniendo la regla del primer principal
- **AND** un vínculo vigente duplicado se rechaza sin crear otro
- **AND** relaciones finalizadas anteriores permanecen sin sobrescribirse

#### Scenario: Selección obsoleta o fallo de auditoría

- **GIVEN** un formulario de vínculo abierto
- **WHEN** el alcance o estado deja de permitirlo, o falla su auditoría
- **THEN** no se crea una relación parcial y la interfaz conserva el formulario
