# identidad-autenticacion

## ADDED Requirements

### Requirement: Inicio de sesión

El sistema DEBE autenticar a un usuario contra las credenciales de una cuenta en estado activo.
Ante credenciales inválidas, cuenta inexistente, cuenta pendiente de activación o cuenta
desactivada, el sistema DEBE responder con un mensaje uniforme que no permita distinguir cuál
de esas condiciones se produjo.

#### Scenario: Credenciales válidas

- **GIVEN** una cuenta activa con credenciales correctas
- **WHEN** el usuario inicia sesión
- **THEN** el sistema establece una sesión autenticada

#### Scenario: Cuenta desactivada no se distingue de credencial errónea

- **GIVEN** una cuenta desactivada
- **WHEN** alguien intenta iniciar sesión con sus credenciales correctas
- **THEN** el sistema responde con el mismo mensaje que ante credenciales inválidas

### Requirement: Bloqueo temporal por intentos fallidos

El sistema DEBE bloquear temporalmente el acceso a una cuenta tras superar el número
configurado de intentos fallidos consecutivos, durante el lapso configurado. El bloqueo DEBE
levantarse solo, sin intervención administrativa. Los intentos fallidos y el bloqueo DEBEN
registrarse en la bitácora.

#### Scenario: Bloqueo tras intentos consecutivos

- **GIVEN** una cuenta que alcanzó el número configurado de intentos fallidos
- **WHEN** se intenta iniciar sesión nuevamente con la contraseña correcta
- **THEN** el sistema rechaza el acceso indicando que la cuenta está bloqueada temporalmente

#### Scenario: Levantamiento automático

- **GIVEN** una cuenta bloqueada temporalmente
- **WHEN** transcurre el lapso configurado
- **THEN** la cuenta admite nuevamente intentos de inicio de sesión

### Requirement: Duración de sesión configurable por rol

El sistema DEBE cerrar la sesión tras el período de inactividad configurado para el rol del
usuario. La duración DEBE poder configurarse de forma distinta por rol, de modo que el
personal que captura movimientos en el punto de control disponga de un período más amplio que
el personal administrativo. Cuando un usuario tenga varios roles, DEBE aplicarse la duración
más amplia entre las de sus roles vigentes.

#### Scenario: Operador durante la ventana de ingreso

- **GIVEN** un operador con un rol cuya duración de inactividad es amplia
- **WHEN** transcurre un período de inactividad menor a esa duración entre dos escaneos
- **THEN** la sesión permanece abierta

#### Scenario: Sesión administrativa desatendida

- **GIVEN** un usuario administrativo con una sesión abierta
- **WHEN** transcurre su período de inactividad configurado sin actividad
- **THEN** el sistema cierra la sesión y exige autenticarse nuevamente

### Requirement: Cierre de sesión

El sistema DEBE permitir al usuario cerrar su sesión actual y DEBE permitirle cerrar todas sus
sesiones activas en cualquier dispositivo. Un usuario con permiso de administración de cuentas
DEBE poder cerrar las sesiones activas de otra cuenta, dejando constancia en la bitácora.

#### Scenario: Cierre de todas las sesiones por el titular

- **GIVEN** un usuario con sesiones abiertas en dos dispositivos
- **WHEN** solicita cerrar todas sus sesiones
- **THEN** ninguna de las sesiones previas permite continuar operando

### Requirement: Cierre del turno de captura

El sistema DEBE permitir a un operador finalizar explícitamente su turno de captura, lo que
DEBE cerrar su sesión y desvincularlo del punto de control. Un turno de captura NO DEBE
permanecer abierto más allá del cierre de la jornada configurada.

#### Scenario: Turno abierto al cerrar la jornada

- **GIVEN** un operador con un turno de captura abierto
- **WHEN** se ejecuta el cierre de la jornada
- **THEN** el sistema cierra el turno y la sesión asociada

### Requirement: Cambio de contraseña por el titular

El sistema DEBE permitir al titular cambiar su contraseña exigiendo la contraseña vigente. El
cambio DEBE cerrar las demás sesiones activas de esa cuenta y DEBE registrarse en la bitácora
sin almacenar en ningún momento la contraseña en texto claro.

#### Scenario: Cambio con contraseña vigente correcta

- **GIVEN** un usuario autenticado
- **WHEN** cambia su contraseña proporcionando la vigente y una nueva válida
- **THEN** el sistema acepta el cambio
- **AND** cierra las demás sesiones activas de esa cuenta
