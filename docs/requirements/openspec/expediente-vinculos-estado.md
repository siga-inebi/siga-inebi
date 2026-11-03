# expediente-vinculos-estado

## ADDED Requirements

### Requirement: Crear y vincular encargado en el expediente (RF-EXP-004)

El sistema DEBE buscar encargados mediante consultas paginadas en servidor y
permitir crear y vincular uno sin abandonar el expediente. Persona, encargado,
relación y auditoría DEBEN guardarse atómicamente, bajo permiso y alcance del alumno.

#### Scenario: Error al registrar el vínculo

- **GIVEN** un actor autorizado y un formulario de encargado nuevo válido
- **WHEN** falla la creación del vínculo o su auditoría
- **THEN** no queda persona, encargado o relación de esa operación
- **AND** la interfaz conserva los datos para corregir o reintentar

### Requirement: Cambio manual de estado con confirmación (RF-EXP-003)

El sistema DEBE ofrecer una acción independiente del formulario general para
cambiar estado, con confirmación y advertencias no bloqueantes de inconsistencia
con matrícula. DEBE conservar la matrícula y mostrar autor y fecha del último
cambio manual registrado, sin modificar la auditoría histórica.

#### Scenario: Estado Retirado con matrícula vigente

- **GIVEN** un actor autorizado, un estudiante activo y una matrícula vigente
- **WHEN** revisa y confirma el estado Retirado
- **THEN** recibe una advertencia y puede confirmar
- **AND** el expediente cambia, la matrícula se conserva y se audita anterior/nuevo

#### Scenario: Confirmación obsoleta

- **GIVEN** una revisión con un estado de origen
- **WHEN** otro proceso cambia el estado antes de confirmar
- **THEN** la operación se rechaza sin sobrescribir el nuevo estado

### Requirement: Auditoría atómica y alcance (RF-ALC-001, RF-BIT-002)

La escritura DEBE exigir permiso de edición y alcance sobre el alumno; una falla
de auditoría DEBE revertir el cambio. La ficha DEBE exponer solamente el resumen
del cambio de su alumno, sin contexto privado ni eventos de otros estudiantes.

#### Scenario: Fallo de auditoría

- **GIVEN** un cambio de estado autorizado
- **WHEN** falla la escritura del evento de auditoría
- **THEN** el estado del expediente anterior se conserva
