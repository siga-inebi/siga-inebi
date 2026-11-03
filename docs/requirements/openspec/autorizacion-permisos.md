# autorizacion-permisos

## ADDED Requirements

### Requirement: Catálogo de permisos atómicos

El sistema DEBE mantener un catálogo de permisos, donde cada permiso representa una acción
concreta sobre una capacidad y no un módulo completo. El catálogo DEBE ser consultable por los
usuarios con permiso de administración.

#### Scenario: Distinción entre acciones de una misma capacidad

- **GIVEN** la capacidad de captura de asistencia
- **WHEN** se consulta el catálogo de permisos
- **THEN** el registro de ingresos, el de egresos y el cierre declarado figuran como permisos
  distintos y asignables por separado

### Requirement: Roles como agrupación de permisos

El sistema DEBE permitir definir roles como conjuntos de permisos, y modificar la composición
de un rol sin recrear las cuentas que lo tienen asignado. Todo cambio en la composición de un
rol DEBE registrarse en la bitácora con el usuario responsable.

#### Scenario: Modificación de un rol existente

- **GIVEN** un rol asignado a varias cuentas
- **WHEN** un usuario autorizado agrega un permiso a ese rol
- **THEN** las cuentas que lo tienen asignado obtienen el permiso sin recrearse
- **AND** el cambio queda en bitácora

### Requirement: Asignación de múltiples roles

El sistema DEBE permitir asignar más de un rol a una misma cuenta. Los permisos efectivos de
un usuario DEBEN ser la unión de los permisos de todos sus roles vigentes.

#### Scenario: Docente que además coordina

- **GIVEN** una cuenta con el rol de docente y el rol de coordinador de aula
- **WHEN** se calculan sus permisos efectivos
- **THEN** el resultado incluye los permisos de ambos roles

### Requirement: Denegación por defecto

El sistema DEBE denegar toda operación para la que el usuario no tenga el permiso
correspondiente. Ninguna ruta, vista, endpoint ni proceso DEBE conceder acceso por la ausencia
de una regla explícita.

#### Scenario: Operación sin permiso declarado

- **GIVEN** una operación cuyo permiso requerido no figura entre los permisos efectivos del
  usuario
- **WHEN** el usuario la invoca
- **THEN** el sistema deniega la operación

### Requirement: Evaluación en cada operación

El sistema DEBE evaluar los permisos en el momento de ejecutar cada operación y no únicamente
al presentar la interfaz. Ocultar una opción en pantalla NO DEBE ser el único mecanismo que
impida ejecutar la acción correspondiente.

#### Scenario: Invocación directa sin pasar por la interfaz

- **GIVEN** un usuario sin permiso para una operación cuya opción no se le muestra
- **WHEN** invoca esa operación directamente
- **THEN** el sistema la deniega y registra el intento

### Requirement: Vigencia inmediata de los cambios de autorización

Los cambios en los roles de una cuenta o en la composición de un rol DEBEN surtir efecto en
las sesiones activas sin requerir que el usuario cierre e inicie sesión nuevamente.

#### Scenario: Revocación durante una sesión abierta

- **GIVEN** un usuario con una sesión abierta y un permiso vigente
- **WHEN** un administrador le retira el rol que le confería ese permiso
- **THEN** la siguiente operación que lo requiera es denegada en esa misma sesión

### Requirement: Roles del sistema protegidos

El sistema DEBE impedir que se elimine el último rol con permiso de administración de cuentas
y que se desactive la última cuenta que lo posee, para evitar dejar la institución sin
capacidad de administrar el sistema.

#### Scenario: Intento de dejar el sistema sin administrador

- **GIVEN** una única cuenta activa con permiso de administración de cuentas
- **WHEN** se intenta retirarle ese rol
- **THEN** el sistema rechaza la operación indicando el motivo
