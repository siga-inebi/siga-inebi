# identidad-cuentas

## ADDED Requirements

### Requirement: Creación exclusivamente administrativa

El sistema DEBE permitir la creación de cuentas únicamente a usuarios con permiso de
administración de cuentas. NO DEBE existir ninguna vía de autorregistro ni ningún camino por
el que una persona externa obtenga una cuenta sin intervención de la institución.

#### Scenario: No hay autorregistro

- **GIVEN** una persona sin cuenta en el sistema
- **WHEN** intenta acceder a un formulario de creación de cuenta propia
- **THEN** el sistema no ofrece ninguna vía de autorregistro

### Requirement: Vinculación de la cuenta a una persona registrada

Toda cuenta DEBE vincularse a una persona previamente registrada en el sistema, sea estudiante,
docente, encargado o personal administrativo. El sistema NO DEBE permitir crear cuentas
huérfanas sin persona asociada.

#### Scenario: Encargado no registrado

- **GIVEN** una persona que no está registrada como encargado de ningún estudiante
- **WHEN** un usuario autorizado intenta crearle una cuenta de encargado
- **THEN** el sistema rechaza la operación e indica que debe registrarse primero como
  encargado

### Requirement: Activación mediante código de un solo uso

Una cuenta recién creada DEBE quedar en estado pendiente de activación. El sistema DEBE emitir
un código de activación de un solo uso, con vigencia limitada, que el titular canjea para
definir su contraseña. Al canjearse, el código DEBE invalidarse y la cuenta DEBE pasar a
estado activo. Un código vencido o ya canjeado NO DEBE permitir la activación.

#### Scenario: Activación por el titular

- **GIVEN** una cuenta pendiente con un código de activación vigente
- **WHEN** el titular canjea el código y define su contraseña
- **THEN** la cuenta pasa a estado activo
- **AND** el código queda invalidado para usos posteriores

#### Scenario: Código ya canjeado

- **GIVEN** un código de activación que ya fue canjeado
- **WHEN** alguien intenta usarlo de nuevo
- **THEN** el sistema rechaza la activación indicando que el código no es válido

### Requirement: Política de contraseñas

El sistema DEBE exigir una longitud mínima configurable y DEBE rechazar contraseñas presentes
en una lista de contraseñas comunes conocidas. NO DEBE exigir la combinación obligatoria de
mayúsculas, números y símbolos, NO DEBE forzar la rotación periódica de contraseñas y NO DEBE
utilizar preguntas de seguridad como mecanismo de recuperación.

#### Scenario: Contraseña común rechazada

- **GIVEN** un titular definiendo su contraseña
- **WHEN** introduce una contraseña presente en la lista de contraseñas comunes
- **THEN** el sistema la rechaza e indica el motivo

#### Scenario: Contraseña larga sin símbolos aceptada

- **GIVEN** un titular definiendo su contraseña
- **WHEN** introduce una contraseña que supera la longitud mínima y no figura en la lista de
  comunes
- **THEN** el sistema la acepta aunque no incluya mayúsculas, números ni símbolos

### Requirement: Restablecimiento asistido

El sistema DEBE permitir a un usuario con permiso de administración de cuentas emitir un
enlace de restablecimiento de un solo uso y vigencia limitada para una cuenta existente. La
contraseña resultante DEBE definirla el titular; el sistema NO DEBE mostrar ni comunicar en
ningún momento la contraseña resultante a quien emitió el enlace. El consumo del enlace DEBE
cerrar todas las sesiones activas de esa cuenta. La emisión y el consumo DEBEN registrarse en
la bitácora con la identidad de quien los originó.

#### Scenario: Restablecimiento emitido por secretaría

- **GIVEN** un encargado que olvidó su contraseña
- **WHEN** un usuario con permiso de administración emite el enlace de restablecimiento
- **THEN** el sistema registra la emisión en bitácora con la identidad del emisor
- **AND** no revela al emisor ninguna contraseña

#### Scenario: Cierre de sesiones al restablecer

- **GIVEN** una cuenta con sesiones activas en varios dispositivos
- **WHEN** el titular consume el enlace y define una contraseña nueva
- **THEN** todas las sesiones previas de esa cuenta quedan cerradas

### Requirement: Desactivación con verificación de dependencias

El sistema DEBE permitir desactivar una cuenta impidiendo su acceso sin eliminar el registro
histórico de las acciones que ejecutó. Antes de completar la desactivación, el sistema DEBE
advertir si la persona tiene asignaciones vigentes de cursos, secciones o puntos de control
que quedarían sin responsable.

#### Scenario: Docente con secciones vigentes

- **GIVEN** un docente con cursos asignados en el ciclo activo
- **WHEN** un usuario autorizado intenta desactivar su cuenta
- **THEN** el sistema advierte las asignaciones vigentes antes de completar la operación

#### Scenario: Los eventos previos sobreviven

- **GIVEN** una cuenta desactivada que había registrado movimientos y calificaciones
- **WHEN** se consultan esos registros
- **THEN** siguen atribuidos a la identidad de esa cuenta

### Requirement: Prohibición de autoescalamiento

Un usuario NO DEBE poder modificar sus propios roles ni sus propios permisos, ni activar o
desactivar su propia cuenta. Todo intento DEBE rechazarse y registrarse en la bitácora.

#### Scenario: Intento de asignarse un rol

- **GIVEN** un usuario con permiso de administración de cuentas
- **WHEN** intenta asignarse a sí mismo un rol adicional
- **THEN** el sistema rechaza la operación y deja constancia del intento
