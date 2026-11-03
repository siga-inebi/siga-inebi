# autorizacion-alcance

## ADDED Requirements

### Requirement: El alcance acompaña siempre al permiso

Toda operación sobre registros que pertenezcan a un estudiante, curso, sección o punto de
control DEBE evaluar, además del permiso, si el objeto cae dentro del alcance del usuario. El
sistema DEBE denegar cuando falte cualquiera de las dos condiciones. La evaluación del alcance
DEBE resolverse mediante un mecanismo único y compartido, y NO DEBE depender de filtros
escritos por separado en cada operación.

#### Scenario: Permiso sin alcance

- **GIVEN** un docente con permiso para registrar calificaciones
- **WHEN** intenta registrar una calificación de un curso que no tiene asignado
- **THEN** el sistema deniega la operación pese a que el permiso existe

#### Scenario: Listados acotados al alcance

- **GIVEN** un docente que consulta el listado de estudiantes
- **WHEN** el sistema devuelve el resultado
- **THEN** contiene únicamente estudiantes de las secciones dentro de su alcance

### Requirement: Alcance del docente por asignación

El alcance de un docente DEBE derivarse de sus asignaciones de curso y sección. El sistema
NO DEBE requerir que un administrador declare el alcance por separado de la asignación
académica.

#### Scenario: Alta de una asignación

- **GIVEN** un docente sin asignaciones en el ciclo activo
- **WHEN** se le asigna un curso de una sección
- **THEN** ese curso y esa sección quedan dentro de su alcance sin configuración adicional

### Requirement: Asignaciones versionadas

Las asignaciones de curso y sección a docentes DEBEN registrarse con fecha de inicio y fecha
de fin de vigencia. Una reasignación DEBE cerrar el registro vigente y abrir uno nuevo; NO
DEBE sobrescribir el registro anterior. El historial completo de asignaciones de un docente
DEBE ser consultable por ciclo.

#### Scenario: Reasignación a mitad de ciclo

- **GIVEN** un docente con un curso asignado desde el inicio del ciclo
- **WHEN** ese curso se reasigna a otro docente
- **THEN** el registro del primer docente se cierra con su fecha de fin
- **AND** el historial conserva que impartió ese curso durante ese período

#### Scenario: Trayectoria del docente

- **GIVEN** un docente con asignaciones en varios ciclos escolares
- **WHEN** un usuario autorizado consulta su historial
- **THEN** el sistema presenta los cursos y secciones que impartió en cada ciclo

### Requirement: Alcance de lectura histórica

El alcance de lectura sobre información de ciclos anteriores DEBE determinarse por las
asignaciones que el usuario tuvo vigentes en el ciclo al que pertenece esa información, no por
sus asignaciones actuales.

#### Scenario: Consulta de un ciclo anterior

- **GIVEN** un docente que impartió un curso en el ciclo anterior y ya no lo imparte
- **WHEN** consulta las calificaciones que registró en aquel ciclo
- **THEN** el sistema se las muestra

#### Scenario: Ciclo anterior fuera del alcance

- **GIVEN** un docente que nunca tuvo asignada una sección determinada
- **WHEN** intenta consultar la información de esa sección en un ciclo anterior
- **THEN** el sistema deniega la consulta

### Requirement: Alcance de escritura limitado al ciclo activo

El alcance de escritura DEBE limitarse a las asignaciones vigentes en el ciclo activo y, para
las calificaciones, a los períodos de evaluación abiertos. El sistema NO DEBE permitir
modificar información de ciclos cerrados ni de unidades bloqueadas, con independencia de las
asignaciones que el usuario tuviera entonces.

#### Scenario: Intento de corregir un ciclo cerrado

- **GIVEN** un docente que impartió un curso en un ciclo ya cerrado
- **WHEN** intenta modificar una calificación de aquel ciclo
- **THEN** el sistema deniega la operación

### Requirement: Alcance del encargado

La relación entre encargados y estudiantes DEBE modelarse como muchos a muchos: un encargado
puede estar asociado a varios estudiantes y un estudiante puede tener varios encargados. El
alcance de un encargado DEBE comprender únicamente los estudiantes con asociación vigente.

#### Scenario: Encargado con dos hijos

- **GIVEN** un encargado asociado a dos estudiantes del establecimiento
- **WHEN** consulta la información disponible en su portal
- **THEN** el sistema le presenta la de ambos estudiantes y la de ningún otro

### Requirement: Asociación principal del estudiante

Cada estudiante DEBE tener exactamente una asociación marcada como principal entre sus
encargados. La asociación principal DEBE ser la destinataria por defecto de las notificaciones
y la primera referencia de contacto en caso de emergencia. El sistema DEBE exigir designar una
nueva asociación principal antes de terminar la vigente.

#### Scenario: Baja de la asociación principal

- **GIVEN** un estudiante con dos encargados, uno de ellos marcado como principal
- **WHEN** se intenta terminar la asociación principal sin designar otra
- **THEN** el sistema rechaza la operación e indica que debe designarse una nueva principal

### Requirement: Corte total al terminar la asociación

Cuando una asociación entre un encargado y un estudiante termine, el acceso del encargado a la
información de ese estudiante DEBE cesar por completo, incluida la información del período en
que la asociación estuvo vigente. El sistema NO DEBE conservar acceso histórico para
asociaciones terminadas.

#### Scenario: Cambio de responsable

- **GIVEN** un encargado cuya asociación con un estudiante fue terminada
- **WHEN** intenta consultar la información de ese estudiante, incluida la de meses anteriores
- **THEN** el sistema deniega la consulta

#### Scenario: Otras asociaciones no se ven afectadas

- **GIVEN** un encargado con asociaciones a dos estudiantes, una de ellas terminada
- **WHEN** consulta su portal
- **THEN** el sistema le presenta únicamente la información del estudiante con asociación
  vigente

### Requirement: Unión de alcances en cuentas con varios roles

Cuando una cuenta tenga varios roles, su alcance efectivo DEBE ser la unión de los alcances que
cada rol le confiera. Ningún rol DEBE reducir el alcance conferido por otro.

#### Scenario: Docente y coordinador a la vez

- **GIVEN** una cuenta que es docente de una sección y coordinadora de otra
- **WHEN** se calcula su alcance efectivo
- **THEN** comprende ambas secciones
