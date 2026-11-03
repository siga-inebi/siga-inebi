# auditoria-bitacora

## ADDED Requirements

### Requirement: Registro de operaciones de escritura

El sistema DEBE registrar en la bitácora toda operación que cree, modifique o dé de baja
información institucional, académica o personal.

#### Scenario: Modificación de una calificación

- **GIVEN** un docente que modifica una calificación ya registrada
- **WHEN** confirma el cambio
- **THEN** el sistema crea un asiento de bitácora para esa operación

### Requirement: Contenido del asiento

Cada asiento DEBE registrar la identidad del usuario, la acción, la fecha y hora, la capacidad
afectada, el registro concreto sobre el que se actuó, el valor anterior y el nuevo cuando
corresponda, el dispositivo o punto de acceso empleado y el motivo declarado en las
operaciones que lo exijan.

#### Scenario: Asiento de un registro manual de asistencia

- **GIVEN** un usuario que registra manualmente un movimiento indicando el motivo
- **WHEN** se consulta el asiento correspondiente
- **THEN** incluye usuario, acción, fecha y hora, registro afectado, dispositivo y motivo

### Requirement: Catálogo de lecturas sensibles

El sistema DEBE registrar en la bitácora la consulta de la ficha de salud de un estudiante, la
apertura de documentos de respaldo de justificaciones, la consulta del historial de entradas y
salidas de un estudiante individual y la consulta de los datos de contacto de la familia. Las
consultas agregadas que no identifiquen a un estudiante en particular NO DEBEN registrarse,
para no degradar la utilidad de la bitácora.

#### Scenario: Consulta del historial de movimientos de un estudiante

- **GIVEN** un usuario autorizado que consulta el historial de entradas y salidas de un
  estudiante
- **WHEN** el sistema presenta el resultado
- **THEN** registra un asiento de lectura sensible con el usuario, el estudiante y el momento

#### Scenario: Listado agregado de asistencia

- **GIVEN** un usuario que consulta el porcentaje de asistencia de una sección
- **WHEN** el sistema presenta el resultado
- **THEN** no genera un asiento de lectura sensible

### Requirement: Registro de intentos denegados

El sistema DEBE registrar los intentos de operación denegados por falta de permiso o por
alcance insuficiente, los intentos de autenticación fallidos y los intentos de
autoescalamiento de privilegios.

#### Scenario: Encargado que intenta ver a un estudiante ajeno

- **GIVEN** un encargado sin asociación con un estudiante
- **WHEN** intenta acceder a la información de ese estudiante
- **THEN** el sistema deniega la operación y crea un asiento del intento

### Requirement: Inmutabilidad de la bitácora

Los asientos de bitácora NO DEBEN poder modificarse ni eliminarse por ningún usuario, con
independencia de su rol. El sistema NO DEBE ofrecer ninguna operación de edición o borrado
sobre la bitácora.

#### Scenario: Intento de borrar un asiento

- **GIVEN** un usuario con el rol de mayor privilegio
- **WHEN** intenta eliminar un asiento de bitácora
- **THEN** el sistema no ofrece esa operación y la rechaza si se invoca directamente

### Requirement: Consulta y exportación restringidas

La consulta de la bitácora DEBE estar restringida a los usuarios con permiso de auditoría y
DEBE permitir filtrar por usuario, rango de fechas, capacidad afectada y tipo de acción. La
exportación de asientos DEBE quedar a su vez registrada en la bitácora.

#### Scenario: Exportación auditada

- **GIVEN** un usuario con permiso de auditoría
- **WHEN** exporta un rango de asientos
- **THEN** el sistema genera el archivo
- **AND** registra la exportación con el usuario, el rango y el momento

### Requirement: Atribución persistente

Los asientos DEBEN conservar la atribución a la identidad que ejecutó la acción aunque la
cuenta se desactive posteriormente. La desactivación de una cuenta NO DEBE alterar ni anonimizar
los asientos existentes.

#### Scenario: Consulta tras la baja de un docente

- **GIVEN** asientos generados por un docente cuya cuenta fue desactivada
- **WHEN** un auditor los consulta
- **THEN** siguen atribuidos a esa identidad
