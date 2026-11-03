# E6: corrección y desactivación de registros del expediente

Entrega del issue #632 para Salud, Observaciones y Contactos. Aplica RF-EXP-005,
RF-EXP-006, RF-EXP-009, RNF-AUD-003 y ADR-0004/0005/0006/0008. Continúa el expediente
del PR #647 y los vínculos del #648. No implementa E7/E8, D5 ni nuevos roles.

## Experiencia

- Cada registro ofrece **Editar** y **Desactivar** según capacidades del servidor.
  Los datos de registro y el contenido seleccionado se muestran antes de confirmar.
- Edición en línea de contenido de salud, descripción de observación o nombre,
  teléfono y relación del contacto. Conserva estudiante, autor y fecha originales
  cuando esos campos existen. Se enfoca el título de la acción al abrirla.
- Desactivación con confirmación explícita; cancelar no escribe. Es un soft delete,
  nunca un borrado físico. El contenido desactivado sigue disponible bajo permiso.
- **Mostrar desactivados** usa `include_inactive=true` y paginación del servidor.
  Reinicia página al cambiar el filtro; al guardar conserva el filtro y vuelve a
  la primera página. Los registros desactivados tienen su etiqueta y no ofrecen
  una segunda desactivación. Pueden corregirse sin reactivarlos.
- Error de guardado conserva valores/confirmación y permite reintentar. Durante
  el envío se bloquean formulario, filtro, paginación y cambio de pestaña/retorno
  desde el expediente. No hay ventanas apiladas, descarga completa ni otro paginador.
- Los paneles visitados conservan página, filtro y borrador en memoria al cambiar
  de pestaña. No se guardan datos sensibles en almacenamiento local o en la URL.

## Contratos API

### Edición

Rutas bajo `/api/v1/students/`:

| Recurso | PATCH | Campos aceptados |
| --- | --- | --- |
| Salud | `health-notes/{public_id}/` | `content`, obligatorio y no vacío |
| Observaciones | `observations/{public_id}/` | `description`, obligatorio y no vacío |
| Contactos | `emergency-contacts/{public_id}/` | `name`, `phone_number`, `relationship_label`, parciales según contrato existente |

Salud y observaciones antes respondían 405. Los PATCH nuevos rechazan campos
adicionales con 400, incluidos autor, estudiante, fechas y actividad. No habilitan
PUT ni cambios de identidad. Contactos conserva su contrato previo, incluido PATCH
vacío sin escritura. Respuesta 200 con el serializador de detalle existente.

Las tres rutas exigen sesión, `student.view_sensitive`, `student.edit_basic` y
alcance del estudiante en ambas operaciones. La falta de permiso/alcance responde
403; UUID inexistente, 404; contenido vacío/incorrecto, 400. La UI envía solo campos
editables: no reutiliza una fila completa como payload.

Los servicios actualizan únicamente el contenido suministrado. Correcciones y
desactivaciones usan transacción y bloqueo de la fila: si falla la auditoría, la
escritura se revierte. Corregir un registro desactivado conserva `is_active=false`.

### Desactivación

`DELETE` sobre las mismas tres rutas conserva el contrato existente: **204**, sin
cuerpo JSON, y registro persistente con `is_active=false`. No hay reactivación nueva.

### Listados

Se conservan las rutas anidadas `students/{student_public_id}/health-notes/`,
`observations/` y `emergency-contacts/`, sobre `{count,next,previous,results}` y
páginas de 25. Se aplica filtro del estudiante y actividad antes de contar/paginar.
Los listados agregan `actions: {edit, deactivate}` calculadas en servidor. Sin
alcance de edición ambas son falsas y la lectura autorizada sigue funcionando.

Las capacidades usan las consultas centrales de alcance sin auditar una edición
no intentada. Esta corrección se aplica también a las capacidades de Encargados
de E5. Las escrituras siguen usando autorización y auditoría de denegación reales.
Una selección antigua no sustituye la comprobación de permisos al enviar.

POST conserva su respuesta anterior sin `actions`; se separa el serializador de
respuesta de creación del listado. OpenAPI documenta los sobres y PATCH nuevos.
Todas las respuestas conservan `Cache-Control: no-store`.

## Privacidad e historial

Se reutilizan auditorías de lectura y escritura del dominio. Las correcciones
de salud/observaciones registran `students.health_note.updated` y
`students.observation.updated`; contactos mantiene su evento `updated` existente.
La auditoría incluye actor, recurso y nombres de campos cambiados; no copia textos
médicos, observaciones, teléfonos ni nombres de contactos. Una corrección no cambia
el autor de la nota: el responsable de corregir queda en el evento de auditoría.

La edición corrige la fila existente; no agrega versionado de textos ni guarda
su contenido anterior en bitácora. La conservación de historial de esta entrega
comprende registros desactivados, autor/fechas originales y eventos auditables.
No se elimina ningún asiento. Las decisiones de asignación exacta de roles de
PD-005 permanecen vigentes; no se amplía el acceso sensible ni se resuelven aquí.

## Validación

- PostgreSQL local completo: **1845 aprobadas, 23 omitidas, cobertura 95.27%**.
- API/unidad específica: **68 pruebas aprobadas** (registros, contratos anteriores
  y rollback por falla de auditoría). Regresión de auditoría/vínculos/registros:
  **68 aprobadas**, sin eventos falsos de denegación al consultar capacidades.
- Frontend completo: **337 pruebas / 41 archivos, cobertura 85.79%**.
- HTTP real con sesión/CSRF en las tres colecciones: páginas 1/2, edición y
  metadatos originales, campos protegidos, 204, contenido desactivado conservado,
  corrección histórica sin reactivación y POST compatible.
- Chromium real: guardado de edición y confirmación/cancelación de desactivación
  en las tres pestañas, historial en página dos a 1440 × 1000 y editor de contacto
  a 390 × 844 sin desbordamiento horizontal. Solo datos sintéticos.
- Ruff/formato, ESLint, Prettier, build y presupuestos aprobados: inicial
  **222288/230000 bytes gzip**, mayor entrada con ruta **237125/250000 bytes gzip**.
- Django check y migraciones aprobados, sin cambios de modelos. OpenAPI validado:
  **0 errores, 25 avisos (21 únicos)**; dos menos al declarar respuestas existentes.
- **69 pruebas de herramientas y 7 de política PR/archivos aprobadas**. No se repiten
  las nueve pruebas auxiliares incompatibles con Windows (`os.getuid/getgid`), ya
  documentadas en E5; sus archivos no cambian.

Preview local: frontend **5187**, backend **8015**, base aislada
`siga_inebi_record_actions_preview`. Capturas ignoradas `tmp/local-runtime/632-e6-*.png`.
No se versionan cookies, medios, logs privados, base ni información real. Docker
no se ejecutó localmente; el PR conserva evidencia separada del CI.

## Integración y reversión

Rama creada desde develop actualizado `5f8630d`, incorporando por fast-forward el
PR #648 (`092aba7`), que incluye #647. Orden: **#647 → #648 → E6**. Mientras sigan
abiertos, el diff hacia develop contiene esas dependencias; revisar el cambio
propio comparando contra `feat/632-guardian-relation-actions`. Si se integran con
squash, rebasar para retirar commits ya incorporados. Conservar las resoluciones
anteriores frente a #633/#634/#635 documentadas en el expediente.

Sin modelos, migraciones, permisos, variables ni dependencias nuevos. La matriz
enlaza implementación/pruebas sin cambiar estados RF ni cerrar el epic. Aceptación
del usuario e integración pendientes. Revertir solo el commit propio de E6 mantiene
el expediente y vínculos anteriores. No borrar auditoría ni registros y no reactivar
filas mediante SQL para intentar deshacer operaciones históricas.
