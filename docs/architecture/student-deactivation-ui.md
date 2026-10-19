# E7: desactivar estudiante desde el expediente

Issue #632, RF-EXP-008 y RF-ALC-001; ADR-0004/0005/0006/0008. Parte de develop con
#647 integrado (`ba879da`). Es independiente de #648/#649 y no modifica esos PR.

## Flujo

Datos ofrece **Desactivar estudiante** según capacidad del servidor. Abre una
confirmación en línea con nombre, foco inicial y aviso de conservación de persona,
vínculos, matrículas y registros. El retiro académico continúa en Matrículas.
Cancelar no escribe. Durante el envío se bloquean formulario, pestañas y retorno
desde la ficha; un rechazo conserva confirmación y error para reintentar.

Se reutiliza DELETE por id entero, seguido de recarga de la ficha por UUID. La UI
muestra el estado devuelto por el servidor. Una vez recibido 204, comunica el éxito.
Si falla la recarga, conserva ese resultado y reintenta solo GET, sin repetir DELETE.
La ficha inactiva deja de ofrecer la acción. No agrega reactivación ni cambia
matrículas, formulario general o el cambio de estado D5/E9, todavía pendiente.

## Contratos y arquitectura

- `DELETE /api/v1/students/{id}/` conserva sesión, `student.edit_basic`, alcance y
  respuesta **204 sin cuerpo**. El servicio existente establece `is_active=false`
  y `status=inactive`, sin borrar personas, relaciones, matrículas ni otros registros.
- Desactivación y auditoría pasan a ser atómicas con bloqueo de fila. Si falla la
  auditoría, se revierte la escritura. Evento `students.student.deactivated`, actor,
  recurso y código conservados, sin copiar datos sensibles ni alterar asientos.
- GET/HEAD `/students/records/{public_id}/`, bajo `/api/v1`, agrega
  `actions: {deactivate: boolean}`. GET y HEAD usan `student.view_basic` y alcance
  de lectura. La ficha inactiva sigue disponible cuando el alcance efectivo lo permite.
- La capacidad usa consultas centrales de edición/alcance y actividad del perfil;
  no audita una escritura no intentada. Cada DELETE revalida autorización: 403 sin
  permiso/alcance habilitado, 404 fuera del queryset autorizado. Si el actor pierde
  acceso derivado, la lectura se deniega según la política existente.
- CUI/nacimiento siguen write-only. Conserva `Cache-Control: no-store`, sin datos
  del expediente en almacenamiento persistente. No duplica infraestructura de #630.
- Lecturas en queries, reglas/atomicidad en servicios, HTTP en API, confirmación y
  navegación en React. Sin modelos, migraciones, variables, dependencias o permisos nuevos.

## Evidencia

- PostgreSQL completo: **1966 aprobadas, 23 omitidas, cobertura 95.37%**.
- Frontend completo: **418 pruebas / 51 archivos, cobertura 86.53%**.
- API/ciclo de vida/expediente: **36 aprobadas**. Permisos y alcance, capacidades
  sin falsa denegación, HEAD con lectura, rollback por falla de auditoría y conservación
  de persona, vínculo, matrícula activa, documento, salud, observación, contacto y asistencia.
- UI: confirmación/cancelación, solo lectura, rechazo, doble envío, recarga y fallo
  posterior de GET sin repetir DELETE. Contrato del servicio verifica verbo y cuerpo vacío.
- HTTP con sesión/CSRF: 204, ficha inactiva/capacidad false, persona y colecciones
  relacionadas exactamente conservadas. Otro estudiante sigue activo y la ruta directa funciona.
- Chromium **1440 × 1000** y **390 × 844**: confirmación/cancelación, sin desbordamiento
  horizontal móvil y ficha inactiva sin acción. Solo datos sintéticos.
- Ruff/formato, ESLint, Prettier, build y presupuestos aprobados: inicial
  **222407/230000 bytes gzip**, mayor entrada con ruta **237608/250000 bytes gzip**.
- Django check y migraciones aprobados. OpenAPI: **0 errores**, 28 avisos (24 únicos)
  del esquema completo. **69 pruebas de herramientas y 7 de políticas** aprobadas.

Preview: frontend **5188**, backend **8016**, base aislada
`siga_inebi_student_deactivation_preview`. Un alumno sintético se desactivó por HTTP;
otro queda activo para revisar la confirmación. Capturas ignoradas `tmp/local-runtime/632-e7-*.png`.
Cookies, medios, logs privados y base no se versionan. Docker no se ejecutó localmente;
el PR conserva resultados separados de CI. La aceptación del usuario queda pendiente.

## Reversión

Revertir los commits propios de E7 restaura la interfaz y contratos previos. No hay
migración que deshacer. No borrar filas, archivos o auditoría ni reactivar perfiles
con SQL para deshacer historia. La matriz enlaza código/pruebas sin cambiar estados
RF ni cerrar el epic.
