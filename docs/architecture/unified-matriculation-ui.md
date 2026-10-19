# Alta unificada de matrícula — M6

Entrega parcial del issue #632. Resuelve el acceso individual de M6 y reúne las
altas disponibles en **Matricular**, sin declarar completo el epic.

## Experiencia

- La cabecera ofrece un único acceso **Matricular**. El menú distingue
  **Un estudiante** de **Altas iniciales por lotes** y explica cada opción.
- El formulario individual sirve para primera matrícula y reinscripción. No
  pregunta al operador cuál corresponde ni descarga el historial para decidir.
- Antes de confirmar explica que una reinscripción cierra la matrícula anterior
  que siga activa, como ya hacía el caso de uso existente.
- Se conserva la selección de estudiante, ciclo, sección y fecha. Grado y jornada
  se obtienen de la sección; el servidor comprueba su coherencia.
- Un rechazo conserva los datos y permite corregir/reintentar. Durante el envío
  se deshabilita la confirmación. Tras éxito se cierra y actualiza el listado.
- Escape cierra el menú sin iniciar operaciones y devuelve foco al botón.
- **Movimientos** conserva su acceso independiente: no es un alta.

## Selección de operación y contrato

`POST /api/v1/enrolments/registrations/` recibe los mismos campos que la matrícula
individual existente: UUID públicos `student_id`, `academic_cycle_id`, `grade_id`,
`shift_id`, `section_id` y fecha `effective_on`.

El servicio `register_student` consulta si existe matrícula de otro ciclo cuyo
estado sea distinto de `cancelled`. Es el mismo criterio de antecedente válido
que usa `reenrol_student`; no usa el estado manual del expediente para decidir.

- Con antecedente: delega en `reenrol_student` y devuelve
  `registration_mode=reenrolment`.
- Sin antecedente: delega en `matriculate_student` y devuelve
  `registration_mode=matriculation`.
- La respuesta 201 contiene los campos de `MatriculationSerializer` y el modo
  elegido. No crea una persona ni un expediente nuevo.
- Un registro del mismo ciclo no habilita una reinscripción en ese ciclo ni
  permite saltarse las restricciones de duplicados.
- No cambia la elegibilidad de promoción ni asigna grado automáticamente.

La selección y escritura ocurren dentro de una transacción. Se conservan los
guards de ciclo, baja lógica, cupo y jornada, las restricciones de duplicados y
la auditoría de los casos de uso. Si falla la nueva inscripción, se revierte el
cierre de la anterior y sus eventos. No se reserva cupo al abrir el formulario.

La vista exige sesión, `enrollment_create` y alcance sobre la sección destino
antes de resolver el estudiante o consultar su historial. Reutiliza
`require_section_scope`; no amplía permisos ni duplica su implementación.

Las rutas `/matriculations/`, `/re-enrolments/` y `/re-enrolments/bulk/` conservan
contrato y comportamiento. El lote inicial sigue usando su operación existente;
M2 y su contrato de altas iniciales masivas se entregan por separado.

## Arquitectura y pruebas

Aplican ADR-0004 (REST), ADR-0005 (autorización), ADR-0006 (historial) y ADR-0008
(capas). No cambia una regla de dominio: el nuevo servicio compone las existentes.
No requiere migraciones, dependencias, variables ni permisos nuevos.

`EnrolmentCreateWindow` se carga al abrir el alta. `EnrolmentEntryMenu` solo
selecciona ventanas; no consulta historial ni decide matrícula/reinscripción.
El `register` del servicio frontend realiza una sola escritura.

- `backend/tests/api/test_unified_matriculation_api.py`: 16 casos con primera
  matrícula, antecedentes activos/completados/retirados, anulaciones, duplicados,
  rollback y rechazos de sesión/permiso/alcance.
- `frontend/src/test/UnifiedEnrolmentWindow.test.jsx`: conservación de datos,
  reintento y bloqueo durante confirmación.
- `frontend/src/test/EnrolmentEntryMenu.test.jsx`: rutas individuales/masivas,
  Escape y foco; no presenta opciones desconectadas.
- `newModulePages.test.jsx` y `moduleServices.test.js`: entrada desde la página,
  payload, refresco y conservación del lote inicial y rutas explícitas.

## Integración con entregas abiertas

La rama nace de `develop` y no fusiona automáticamente otros PR.

- **#636/M1:** ambos extraen `EnrolmentCreateWindow`. Al resolver el add/add,
  conservar el formulario M6 que envía `register`, el listado con nombres
  anidados/búsqueda remota M1 y el acceso diferido. Retirar la prop `creating`
  de modo manual y los botones individuales separados.
- **#638/M2–M4:** conectar `onReenrolBulk` del menú al estado que abre su ventana
  existente; retirar de la cabecera el botón duplicado de reinscripción masiva.
  La acción, vista previa y contrato del lote no cambian. La opción está probada
  y se oculta si no se conecta; no se ofrece una ventana ausente en `develop`.
- **#644/M7:** conservar el aviso como hijo contextual del formulario extraído,
  con ciclo/sección y `submitting`. Tras un rechazo permanece la ventana, por
  lo que el aviso puede renovar su lectura. No restaurar el formulario en la página.
- **#642/M5:** mantener sus filtros y la recarga de la página tras éxito.
- Mantener las acciones de movimientos y promoción de #639/#640/#641.

Los tests de ramas anteriores que buscan «Nueva matrícula» o «Reinscribir»
deben abrir **Matricular → Un estudiante** y confirmar en el diálogo. Los tests
de cupo para dos modos manuales se consolidan en ese único acceso; las dos
decisiones del servidor quedan verificadas por API.

La adopción de `useServerList`, URL y selectores comunes depende de #630.
Esta entrega no sustituye esa infraestructura ni afirma resolver sus catálogos.

## Evidencia de validación

- Rama independiente sobre `develop` (`5f8630d`): backend completo con PostgreSQL,
  **1792 aprobadas y 23 omitidas**, cobertura **95,18 %**; frontend completo,
  **316 aprobadas en 38 archivos**, cobertura **85,10 %**.
- Documentación/requerimientos: **49 pruebas aprobadas**. Ruff lint/formato,
  ESLint, build/presupuesto de bundles, Django check y detección de migraciones
  aprobados. OpenAPI sin errores, con las 27 advertencias preexistentes
  (23 únicas). No se cambian dependencias locales para igualar CI.
- Integración local M1 + M5 + M7 + M6: **341 pruebas frontend en 41 archivos**,
  cobertura **85,51 %**, y **35 pruebas API** aprobadas; lint y build aprobados.
  Resolución local en `2f7807e` y adaptación de pruebas en `dd46bdf`. Es evidencia
  de compatibilidad, sin fusionar ni modificar las ramas públicas de otros PR.
- Preview aislada en `http://127.0.0.1:5183/`, backend 8011, con datos sintéticos
  y ciclos 2026/2027. Por HTTP real se verificaron login/CSRF, primera matrícula,
  reinscripción automática, duplicado rechazado con 400, origen conservado como
  completado y cupo actualizado a 2 ocupadas de 35.
- Revisión DOM/HTTP y compilación no equivalen a aceptación visual institucional.
  La ejecución local nativa tampoco se presenta como ejecución local de Docker.

## Reversión

Revertir el código del PR restaura las entradas explícitas. No borrar matrículas,
expedientes, eventos ni cierres ya confirmados para revertir la interfaz.
