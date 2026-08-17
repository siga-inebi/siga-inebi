# Validacion del prototipo con la institucion

Guia para conducir las sesiones de validacion de wireframes y prototipo con
INEBI Salcaja.

Material a usar en sesion: [`prototipo-siga.html`](prototipo-siga.html) abierto
en un navegador, con la barra superior visible para cambiar de rol. Wireframes
impresos o proyectados: [`wireframes.md`](wireframes.md). Estructura de rutas y
roles: [`navigation-map.md`](navigation-map.md).

El registro de lo observado se lleva en
[`validation-observations.md`](validation-observations.md).

## Objetivo de la validacion

Confirmar tres cosas antes de implementar:

1. Que las pantallas contienen la informacion que la institucion necesita.
2. Que el recorrido para las tareas frecuentes es el correcto.
3. Que cada tipo de usuario ve lo que debe ver, y nada mas.

No se valida color, tipografia ni estilo: el prototipo es deliberadamente neutro
para que la conversacion no se desvie hacia lo estetico.

## Que se valida y que no

| Si se valida | No se valida en esta sesion |
| --- | --- |
| Que existan las pantallas necesarias | Colores, tipografia y logotipo final |
| Que la informacion mostrada sea la correcta | Velocidad y rendimiento |
| Que el orden de los pasos coincida con el proceso real | Calculos y reglas internas de negocio |
| Que cada rol vea lo que le corresponde | Integraciones y reportes oficiales al ministerio |
| Que los nombres y terminos sean los que usa la institucion | Migracion de datos existentes |

Conviene decirlo en voz alta al abrir la sesion. Evita que la conversacion se
desvie a temas de otra fase.

## Participantes sugeridos

| Perfil institucional | Rol del sistema que valida | Imprescindible |
| --- | --- | --- |
| Direccion | Director | Si |
| Coordinacion academica | Coordinador academico | Si |
| Secretaria o registro | Personal administrativo | Si |
| Un docente guia | Docente | Deseable |
| Encargado de informatica | Administrador del sistema | Deseable |
| Representante de familias | Encargado o tutor | Opcional |

## Preparacion

1. Abrir `prototipo-siga.html` en un navegador. No requiere internet ni instalacion.
2. Tener a mano los wireframes del modulo a revisar.
3. Preparar la bitacora de observaciones en blanco.
4. Confirmar quien asiste y que rol representa cada persona.
5. Reservar entre 60 y 90 minutos.

## Guion de sesion, 60 minutos

| Tiempo | Bloque | Contenido |
| --- | --- | --- |
| 0–5 | Encuadre | Que es un prototipo y que no es. No hay datos reales ni funciones completas. |
| 5–10 | Mapa de navegacion | Recorrer `#/mapa` y confirmar la estructura de modulos. |
| 10–25 | Recorrido 1 | Matricular un estudiante de reingreso, de inicio a fin. |
| 25–35 | Recorrido 2 | Buscar un estudiante y consultar su expediente. |
| 35–45 | Recorrido 3 | Preparar el ciclo siguiente: crear ciclo, ofertar grados, secciones. |
| 45–55 | Roles | Cambiar de rol y confirmar que cada perfil ve lo correcto. |
| 55–60 | Cierre | Recoger prioridades y acordar la siguiente revision. |

Recomendacion para el recorrido: navegar el prototipo en vivo en lugar de
describirlo. Pedir a un participante que intente completar la tarea sin guia y
observar donde duda. Las dudas son la observacion mas valiosa de la sesion.

## Recorridos a probar

Cada recorrido se pide como tarea, no como demostracion.

### R1. Matricular un estudiante de reingreso

`Login` → `Panel` → `Matriculas` → `Nueva matricula` → pasos 1 a 4.

Observar: si busca al estudiante por nombre o por codigo; si entiende en que
paso esta; si espera confirmar antes del paso 4; si el orden de los pasos
coincide con el proceso real del establecimiento.

### R2. Consultar el expediente de un estudiante

`Panel` → `Estudiantes` → filtro → `Ver` → pestanas del expediente.

Observar: que pestana abre primero; si echa en falta algun dato; si entiende por
que la pestana de salud no aparece en ciertos roles.

### R3. Preparar el ciclo siguiente

`Panel` → `Estructura academica` → `Ciclos` → `Ver oferta` → secciones y
asignaciones docentes.

Observar: si el concepto abierto y cerrado se entiende sin explicacion; si
esperan poder reabrir un ciclo cerrado; quien consideran que debe autorizarlo.

### R4. Ver el sistema como docente y como encargado

Cambiar de rol en la barra superior y recorrer el menu.

Observar: si consideran correcto lo que se oculta; si falta algun acceso; si el
rotulo `Mis estudiantes` para el encargado se entiende.

### R5. Alta de persona y creacion de cuenta

`Panel` → `Personas` → `Crear cuenta` → `Usuarios y permisos` → `Matriz de accesos`.

Observar: si el concepto de persona separada de cuenta de usuario resulta
natural; si la matriz de accesos corresponde a la realidad del establecimiento.

## Preguntas para cada pantalla

1. Con esta pantalla delante, sabria que hacer sin que se lo expliquen?
2. Falta algun dato que use a diario? Sobra alguno?
3. El nombre del modulo y de los botones coincide con como lo llaman aqui?
4. Quien de la institucion deberia poder ver esta pantalla? Quien no?
5. Que pasa cuando algo sale mal en este paso hoy, en papel?

## Preguntas de apoyo por modulo

Preguntas abiertas, para que la institucion describa su proceso real.

### Login

- Quien tendra usuario y quien no.
- Que se hace hoy cuando alguien olvida su contrasena.
- Es aceptable que la cuenta se bloquee diez minutos tras cinco intentos fallidos.

### Panel

- Que informacion necesita ver al iniciar el dia cada perfil.
- Cuales son las tres tareas mas frecuentes de su puesto.
- Los pendientes mostrados corresponden a problemas reales del establecimiento.

### Estudiantes y expediente

- Que datos del estudiante son obligatorios al registrarlo.
- Como se llama el codigo del estudiante y que formato tiene.
- Quien puede consultar informacion de salud.
- Que documentos forman el expediente y cuales son obligatorios.
- Faltan datos que hoy se registran en papel o en hojas de calculo.

### Personas

- Se registra a la misma persona mas de una vez hoy.
- Como se identifica a un encargado sin documento.
- Que pasa cuando un docente tambien es encargado de un estudiante.

### Estructura academica

- Cuantas sedes y jornadas maneja el establecimiento.
- Como se nombran los grados y las secciones oficialmente.
- En que momento del ano se abre y se cierra un ciclo.
- Quien autoriza el cierre de un ciclo.
- Sedes, niveles, cursos y ciclos deben ir separados en el menu o agrupados.

### Matriculas

- El orden de los cuatro pasos coincide con el proceso real.
- Se puede matricular con documentos pendientes. Quien lo autoriza.
- Que ocurre cuando una seccion llega a su cupo: se bloquea o solo se advierte.
- Como se registra hoy un traslado o un retiro.
- Que constancia se entrega al terminar la matricula.

### Reportes

- Que reportes se entregan hoy y a quien.
- Con que frecuencia se piden.
- En que formato se necesitan.
- Falta algun reporte obligatorio en el catalogo propuesto.

### Usuarios y permisos

- La matriz de accesos refleja la realidad del establecimiento.
- Hay algun caso donde una persona necesite mas de un rol.
- Quien administra las cuentas cuando direccion no esta disponible.

## Checklist de validacion

Marcar durante la sesion. Una fila sin marcar es una observacion pendiente.

### Navegacion general

- [ ] El recorrido del sistema se entiende sin explicacion previa.
- [ ] Los nombres de los modulos corresponden al lenguaje institucional.
- [ ] Ninguna tarea frecuente exige mas de tres clics desde el panel.
- [ ] Los accesos rapidos del panel son los correctos.
- [ ] Se entiende como volver atras desde cualquier pantalla.

### Por modulo

- [ ] Login: entrada, error y bloqueo se comprenden.
- [ ] Panel: la informacion mostrada es util para el puesto.
- [ ] Estudiantes: la busqueda y los filtros cubren lo que se necesita.
- [ ] Expediente: las pestanas contienen la informacion esperada.
- [ ] Personas: el registro base evita duplicar personas.
- [ ] Estructura academica: sedes, grados, cursos y ciclos estan completos.
- [ ] Oferta: secciones y asignaciones docentes reflejan la organizacion real.
- [ ] Matriculas: el asistente sigue el proceso real del establecimiento.
- [ ] Reportes: el catalogo cubre lo que hoy se entrega.
- [ ] Usuarios: la matriz de accesos es correcta rol por rol.

### Roles

- [ ] Direccion confirma lo que ve el rol Director.
- [ ] Secretaria confirma lo que ve el rol Personal administrativo.
- [ ] Coordinacion confirma lo que ve el rol Coordinador academico.
- [ ] Docencia confirma lo que ve el rol Docente.
- [ ] Direccion confirma el alcance del rol Encargado o tutor.
- [ ] Informatica confirma lo que ve el rol Administrador del sistema.
- [ ] Se confirma que ningun rol ve informacion que no le corresponde.

### Terminologia

- [ ] Los terminos del [glosario](../requirements/glossary.md) coinciden con el uso institucional.
- [ ] Los rotulos de botones se entienden sin ambiguedad.
- [ ] Los mensajes de error y de estado se comprenden.

## Como registrar las observaciones

Cada observacion se anota en el momento, sin filtrar y sin discutir la solucion
durante la sesion. La clasificacion se hace despues, en
[`validation-observations.md`](validation-observations.md).

Clasificacion de tipos:

- **contenido**: falta o sobra un dato en la pantalla.
- **flujo**: el recorrido no encaja con el proceso real.
- **terminologia**: el nombre no es el que usa la institucion.
- **permiso**: quien debe ver que.
- **alcance**: valido, pero queda fuera de la fase fundacional.

Regla de prioridad:

| Prioridad | Criterio |
| --- | --- |
| Alta | Bloquea una tarea diaria o expone datos a quien no corresponde |
| Media | Genera trabajo adicional o confusion, pero la tarea se completa |
| Baja | Preferencia, mejora o detalle de forma |

## Puntos ya identificados que requieren decision institucional

Estos ya estan marcados como pendientes dentro del prototipo y de
[`wireframes.md`](wireframes.md). Se llevan a la primera sesion.

| # | Pantalla | Pregunta abierta | Responde |
| --- | --- | --- | --- |
| P1 | Panel | Que indicadores deben ir en la parte superior | Direccion |
| P2 | Expediente | Que campos son obligatorios al crear el expediente | Institucion |
| P3 | Expediente | Formato y regla del correlativo del codigo de estudiante | Institucion |
| P4 | Estructura academica | Quien autoriza el cierre de un ciclo escolar | Direccion |
| P5 | Estructura academica | Sedes, niveles, cursos y ciclos separados o agrupados en el menu | Institucion |
| P6 | Matriculas | Lista oficial de requisitos documentales por tipo de ingreso | Institucion |
| P7 | Matriculas | Si documentos incompletos permiten matricula provisional y quien la autoriza | Direccion |
| P8 | Matriculas | Al exceder el cupo de una seccion, el sistema bloquea o solo advierte | Institucion |
| P9 | Matriculas | Formato oficial y firma de la constancia de matricula | Institucion |
| P10 | Reportes | Formato oficial exigido por el Ministerio para la nomina | Institucion |
| P11 | Expediente | Quien registra y quien consulta datos de salud del estudiante | Direccion |
| P12 | Panel | El portal de encargados entra en esta fase o se pospone | Direccion |

Las que sigan abiertas al cerrar la validacion pasan a
[`pending-decisions`](../decisions/pending-decisions.md).

## Despues de la sesion

Dentro de las 48 horas siguientes:

1. Pasar las notas a la bitacora de observaciones, sin editar el contenido.
2. Clasificar tipo y prioridad de cada observacion.
3. Aplicar las correcciones de prioridad alta a wireframes, mapa y prototipo.
4. Registrar en la bitacora que archivo se modifico por cada observacion aplicada.
5. Mover las dudas sin definicion a `docs/decisions/pending-decisions.md`.
6. Enviar a la institucion un resumen de una pagina con lo acordado y lo pendiente.
7. Agendar una segunda pasada corta solo sobre lo corregido.

## Criterio de cierre

La validacion se da por completada cuando:

- Los cinco recorridos se completan sin bloqueo por parte de al menos un
  participante de cada perfil.
- Todas las observaciones de prioridad alta tienen decision registrada.
- Los puntos P1 a P12 estan resueltos o trasladados formalmente a decisiones
  pendientes, con responsable y fecha comprometida.
- Cada rol institucional confirmo lo que ve su perfil.
- El acta de la sesion esta firmada por direccion.

Validado no significa cerrado. Significa que hay acuerdo suficiente para avanzar
a la siguiente fase sin rehacer lo hecho.
