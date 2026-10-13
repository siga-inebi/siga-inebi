# Casos de integración en pareja — Diana

Fuente: `docs/planning/tests_plan.md`, sección 10.3 (E2E manual obligatorio) y
tareas D2–D3 de Diana. Estado de los cuatro casos: **No ejecutado**. Este archivo
define pasos y reparto; no registra resultados.

Todos se ejecutan a mano, en navegador real, sobre el QA integrado
(`docs/quality/fase-7/despliegue-cloud-qa.md`), con cuentas QA y datos sintéticos.
No usar superusuario como única cuenta. Cada ejecución se anota en
`ejecuciones.csv` con SHA, ejecutor, revisor y evidencia sin datos sensibles.

## Reparto por persona

| Persona | Caso | Qué prepara | Qué ejecuta | Qué verifica |
| --- | --- | --- | --- | --- |
| **Josué** | CP-INT-MAT-001 | Ciclo activo y ciclo cerrado; sede, jornada, grado y dos secciones (una con cupo, una llena). | Pasos 5 a 8: matrícula, cupo, segundo intento y ciclo cerrado. | Vigencia de la matrícula, historial y rechazo por cupo/ciclo. |
| **Santiago** | CP-INT-ALC-DIA-001 | Rol QA de encargado con `auth_login`, `auth_logout` y `student_view_basic`, y **sin** `student_view_sensitive` (los datos demo solo traen administrador y director), cuenta QA de encargado sin `ScopeGrant` propio, cuenta de secretaría con permiso y alcance, y cuenta sin alcance. No hay pantalla de roles: se crean y asignan por API. | Pasos 2, 4 y 6: consultas con la sesión del encargado antes y después del corte. | Respuesta 200/403/404 conforme al contrato y evento `identity.authorization.denied` en la bitácora. |
| **Emilio** | CP-INT-JUS-001 | Jornada con parámetros vigentes, punto de control y una ausencia registrada del estudiante. | Pasos 3 a 6: resolución de la justificación y consulta del estado del día. | Estado derivado antes y después; el evento original de asistencia no cambia. |
| **Roí** | CP-INT-DOC-001 | Tipo de documento, archivos sintéticos válido, inválido y alterado. | Pasos 3 a 6: integridad, descarga y auditoría de lectura. | Hash, rechazo de token ajeno o vencido y evento `documents.document.read`. |
| **Diana** | Los cuatro | Persona, estudiante, encargado con vínculo vigente y otro terminado, contacto, nota de salud y observación. | Los pasos de expediente de cada caso (marcados **D**). | Datos del expediente, vínculos, baja lógica y auditoría de lecturas sensibles. |

## Datos sintéticos que prepara Diana (una vez, sirven para los cuatro casos)

| Dato | Detalle |
| --- | --- |
| Persona A + estudiante A | Con código sugerido por el sistema, fotografía válida, estado activo. |
| Persona B + estudiante B | Estudiante ajeno: sin vínculo con el encargado de prueba. |
| Encargado 1 | Vínculo **vigente** y principal con el estudiante A. |
| Encargado 2 | Vínculo **terminado** con el estudiante A (creado y luego finalizado con reemplazo). |
| Encargado 3 (reemplazo) | Vínculo **vigente** y secundario (no principal) con el estudiante A, creado **antes** de terminar el principal. Permanece vigente y secundario hasta el cambio del paso 5. |
| Contacto de emergencia | Uno para el estudiante A. |
| Nota de salud y observación | Una de cada una para el estudiante A, con texto sintético. |

Anotar los identificadores públicos en la ficha de entorno, no nombres reales.

---

## CP-INT-MAT-001 — Persona → estudiante → matrícula → consulta autorizada

- **Pareja:** Diana / Josué. **Tipo:** INT. **Prioridad:** crítica.
- **Requisitos:** RF-EXP-001, RF-EXP-002, RF-EXP-003, RF-CIC-002, RF-MAT-001, RF-MAT-002, RF-MAT-004, RF-MAT-007, RF-MAT-008, RF-ALC-001, RF-ALC-005.
- **Nota:** el plan cita `RF-EST` para este caso; ese prefijo es Estructura Académica. La parte de expediente corresponde a `RF-EXP`.
- **Precondición:** ciclo activo con oferta y secciones (Josué); sesión de secretaría con permiso y alcance.

| # | Quién | Paso | Resultado esperado |
| --- | --- | --- | --- |
| 1 | **D** | En `/app/personas`, crear la persona A. | Se guarda y aparece en el listado. |
| 2 | **D** | En `/app/alumnos`, crear el estudiante A sobre esa persona con el código sugerido. | Alta correcta; estado inicial del expediente. |
| 3 | **D** | Repetir el alta con el mismo código. | Rechazo con mensaje claro; no se crea un segundo expediente. |
| 4 | **D** | Subir una fotografía válida y luego un archivo que no es imagen. | La válida se guarda; la inválida se rechaza y la foto anterior se conserva. |
| 5 | Josué | En `/app/matriculas`, matricular al estudiante A en la sección con cupo. | Matrícula activa con fecha de vigencia. |
| 6 | Josué | Intentar una segunda matrícula activa del mismo estudiante. | Rechazo: una sola matrícula activa por estudiante. |
| 7 | Josué | Intentar matricular al estudiante B en la sección llena. | Comportamiento conforme a RF-MAT-004 (aviso o rechazo según el criterio). |
| 8 | Josué | Intentar matricular en el ciclo cerrado. | Rechazo: escritura limitada al ciclo activo. |
| 9 | **D** | Con una cuenta **sin alcance** sobre esa sección, consultar al estudiante A. | Acceso denegado; no se muestran datos. |
| 10 | **D** | Con la cuenta con alcance, consultar el estudiante A y su historial de matrícula. | Datos visibles; historial con la matrícula del paso 5. |
| 11 | **D** + Josué | Revisar la bitácora de las operaciones anteriores. | Altas, matrícula y rechazo de acceso quedaron registrados con usuario y fecha. |

**Limpieza:** no borrar; el estudiante A se reutiliza en los demás casos.

---

## CP-INT-ALC-DIA-001 — Pérdida de alcance al terminar el vínculo

- **Pareja:** Diana / Santiago. **Tipo:** SEG. **Prioridad:** crítica.
- **Requisitos:** RF-ALC-006, RF-ALC-008, RF-EXP-004, RF-EXP-008.
- **Origen:** tarea D3 de Diana; el plan no le asigna identificador, se propone este.
- **Precondición:** el encargado 1 tiene cuenta QA activa y vínculo vigente y principal con el
  estudiante A. Su rol QA tiene exactamente `auth_login`, `auth_logout` y `student_view_basic`, y excluye
  explícitamente `student_view_sensitive`. El encargado 3 (reemplazo) tiene un vínculo vigente
  y secundario con el estudiante A, que permanece así hasta el cambio del paso 5.
- **Cuenta no reutilizable:** la cuenta local de encargado usada en EJ-D1-041 llevaba
  `student_view_sensitive`; no sirve para este caso. Ver la
  [revisión cruzada de EJ-D1-041](revision-cruzada-ej-d1-041.md).

| # | Quién | Paso | Resultado esperado |
| --- | --- | --- | --- |
| 1 | **D** | Confirmar en `/app/padres-de-familia` el vínculo vigente y principal. | Vínculo visible con parentesco y fecha de inicio. |
| 2 | Santiago | Con la sesión del encargado 1, consultar al estudiante A. | Acceso permitido, solo datos básicos. |
| 3 | **D** | Con esa misma sesión, intentar ver la nota de salud y la observación. | Denegado (403): el rol QA del encargado no incluye `student_view_sensitive`. |
| 4 | Santiago | Con la sesión del encargado 1, consultar al estudiante B (ajeno). | Denegado, sin revelar si el estudiante existe. |
| 5 | **D** | Terminar el vínculo del encargado 1 designando como reemplazo al encargado 3, cuyo vínculo sigue vigente y secundario hasta este paso. | El vínculo queda con fecha de fin; el encargado 3 pasa a principal y es el único principal vigente. |
| 6 | Santiago | Sin cerrar la sesión del encargado 1, repetir la consulta del paso 2. | Denegado **de inmediato**, en la siguiente petición. |
| 7 | **D** | Intentar terminar el vínculo principal sin reemplazo (con otro estudiante de prueba). | Rechazo: el principal exige reemplazo vigente. |
| 8 | **D** | Consultar el historial de vínculos del estudiante A. | El vínculo terminado sigue visible; nada se borró. |
| 9 | Santiago | Revisar la bitácora. | Cierre del paso 5 y rechazo del paso 6 registrados. Anotar si los rechazos de los pasos 3 y 4 dejan evento: en la revisión de EJ-D1-041 no todos lo dejaron. |

---

## CP-INT-JUS-001 — Justificación del encargado y efecto en la jornada

- **Pareja:** Diana / Emilio. **Tipo:** INT. **Prioridad:** alta.
- **Requisitos:** RF-JUS-001, RF-JUS-002, RF-JUS-004, RF-JUS-005, RF-JUS-007, RF-ALC-006, RNF-AUD-001, RNF-PRI-004.
- **Limitación a decidir (DEC-QA pendiente):** el frontend no tiene pantalla de justificaciones. El flujo solo puede ejecutarse contra la API (`/api/v1/docs/` con la sesión del navegador). Pablo debe decidir si eso basta como evidencia o si el caso queda bloqueado por interfaz.
- **Precondición:** ausencia registrada del estudiante A en una fecha dentro de la ventana de justificación (Emilio).

| # | Quién | Paso | Resultado esperado |
| --- | --- | --- | --- |
| 1 | **D** | Con la sesión del encargado vigente, enviar una justificación para el estudiante A (`POST attendance/justifications/`) con motivo del catálogo. | Solicitud creada en estado pendiente. |
| 2 | **D** | Con la misma sesión, intentar justificar al estudiante B (ajeno). | 403 con mensaje genérico; sin `student_code` ni `public_id`; no se crea nada. |
| 3 | **D** | Adjuntar un PDF sintético a la justificación. | Adjunto aceptado; solo metadatos en la respuesta. |
| 4 | Emilio | Consultar el estado del día del estudiante A antes de resolver. | Ausencia sin justificar. |
| 5 | Emilio | Con una cuenta con permiso de revisión, aprobar la justificación. | Estado aprobado; se genera el aviso al encargado. |
| 6 | Emilio | Consultar de nuevo el estado del día y los eventos de asistencia. | El estado derivado refleja la justificación; el evento original no cambió. |
| 7 | **D** | Con una cuenta ajena (ni autora ni revisora), intentar leer el adjunto. | Denegado. |
| 8 | **D** | Con la cuenta revisora, leer el adjunto y revisar la bitácora. | Lectura permitida y evento `attendance.justification_attachment.read` con usuario y hora. |

---

## CP-INT-DOC-001 — Expediente documental, descarga y auditoría

- **Pareja:** Diana / Roí. **Tipo:** INT. **Prioridad:** alta.
- **Requisitos:** RF-DOC-001, RF-DOC-004, RF-DOC-005, RF-DOC-006, RF-DOC-009, RF-ARC-001, RF-ARC-003, RF-ARC-007, RNF-SEG-005.
- **Limitación a decidir (DEC-QA pendiente):** la API valida el token de descarga (`GET documents/records/{id}/download/?token=`) pero **ninguna vista lo emite**. La descarga autorizada no puede completarse desde el cliente. Queda fuera `RF-EMI` salvo decisión: la emisión oficial tampoco tiene pantalla.
- **Precondición:** estudiante A con matrícula activa (CP-INT-MAT-001).

| # | Quién | Paso | Resultado esperado |
| --- | --- | --- | --- |
| 1 | **D** | Desde la matrícula del estudiante A (ventana de documentos), subir un PDF sintético válido. | Documento vinculado al estudiante y a la matrícula. |
| 2 | **D** | Intentar subir un archivo con extensión o tipo no admitido. | Rechazo; no se crea registro. |
| 3 | Roí | Verificar la integridad del documento subido. | Hash coincidente. |
| 4 | Roí | Subir una nueva versión del mismo documento. | Nuevo registro con número de versión; el anterior se conserva. |
| 5 | Roí | Intentar la descarga sin token, con token inventado y con token de otra cuenta. | Rechazo en los tres casos y evento `documents.document.read_denied`. |
| 6 | Roí | Descarga autorizada con token válido. | **Bloqueado** hasta que exista el endpoint que entrega el token; registrar como tal. |
| 7 | **D** | Con una cuenta sin alcance sobre el estudiante A, consultar su expediente documental. | Denegado. |
| 8 | **D** | Con la cuenta con alcance, consultar el expediente documental. | Lista con ambas versiones; ningún documento eliminado. |
| 9 | **D** + Roí | Revisar la bitácora. | Subidas, lecturas y rechazos registrados. |

---

## Pendientes antes de ejecutar

1. Pablo confirma las dos limitaciones (justificaciones sin pantalla; token de descarga sin endpoint) y registra la decisión.
2. Santiago crea las cuentas QA y asigna roles y alcances por API.
3. Josué y Emilio confirman que su estructura y su jornada están cargadas en QA.
4. Diana carga los datos sintéticos de la tabla anterior y anota los identificadores.
5. Acordar con cada pareja una ventana de 30 a 45 minutos.
