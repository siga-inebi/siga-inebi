# Altas iniciales por lote — M2

Entrega de #632 que completa el envío masivo de altas iniciales. Complementa la
reinscripción masiva del PR #638; no declara completo el epic ni su integración.

## Comportamiento

La ventana conserva ciclo, sección y fecha compartidos. Busca candidatos en el
servidor con un mínimo de dos caracteres y páginas de 25. La selección persiste
entre páginas/búsquedas y se limita a 100 alumnos por solicitud. Cambiar ciclo o
sección limpia la selección; cambiar datos o selección invalida la revisión.

No consulta matrículas activas para descartarlas en React ni descarga el padrón.
Los candidatos son expedientes activos que el operador puede leer, sin matrícula
activa en ningún ciclo ni antecedente en la misma sección (restricciones vigentes).
El DTO expone solo UUID público, nombre completo y código estudiantil.

**Vista previa** envía una sola petición para todos los seleccionados. El servidor
reutiliza `matriculate_student`, acumula ocupación según el orden del lote y revierte
toda la transacción: no quedan matrículas, cambios de estado ni eventos falsos de
alta. Registra únicamente el resumen auditable de revisión. No reserva vacantes.

**Confirmar matrículas** envía otra petición para el lote revisado. Se revalidan
las reglas; cada alumno puede resultar `created`, `existing` o `error`. Las filas
válidas se conservan aunque otras fallen por reglas de dominio. Un fallo técnico
inesperado revierte toda la solicitud. La sección se bloquea durante el lote para
coordinar el cupo con el guard existente de altas individuales.

Una repetición reconoce como `existing` únicamente una matrícula activa con la
misma sección y fecha. No reescribe estados, fechas ni auditoría de alta. Otra fecha,
sección o estado sigue sujeto a las reglas de duplicados; no se trata como éxito.
Si se pierde la respuesta tras confirmar, puede volver a revisar/enviar la selección
sin duplicar las filas ya creadas.

El resultado conserva nombres y motivos por fila. Solo los errores quedan
seleccionados para corregir/revisar de nuevo. Un error de transporte conserva toda
la selección; exige una nueva revisión. Durante la solicitud se bloquean edición,
confirmación y cierre (incluidos Escape y el botón de cabecera).

Este flujo sigue siendo matrícula, sin cerrar antecedentes. La continuación de
matrículas activas corresponde a reinscripción; M6 unifica la elección individual,
sin convertir este contrato en reinscripción masiva.

## Contratos nuevos, aditivos

- `GET /api/v1/enrolments/matriculations/candidates/` recibe `section_id` obligatorio,
  `search` opcional (máximo 100 caracteres) y `page`. Devuelve el sobre paginado
  existente con `{public_id, full_name, student_code}`. Filtra antes de contar/paginar,
  con orden estable por código y PK. La UI permite recorrer todas las coincidencias.
- `POST /api/v1/enrolments/matriculations/bulk/` recibe `section_id`, `effective_on`,
  `student_ids` (1–100 UUID distintos) y `preview` (por defecto `true`). Ciclo, grado
  y jornada se derivan de la sección en el servidor.
- Respuesta 200: `{preview, total, succeeded, failed, results}`; cada resultado contiene
  `{student_id, status, enrolment_id, error}`. Estados: `ready` (solo preview), `created`
  (solo confirmación), `existing`, `error`. `succeeded` incluye las existentes.
- Entrada inválida responde 400 antes de escribir; referencias de sección inexistentes
  responden 404; UUID de alumno inexistente genera un error de fila. No hay cortes
  silenciosos ni división del lote en solicitudes individuales.

## Autorización y arquitectura

Ambos endpoints exigen sesión y `enrollment_create` con alcance sobre sección destino,
mediante `require_section_scope`. La búsqueda exige además `student_view_basic` y su
alcance central, igual que el selector de estudiantes previo. La nueva ruta no amplía
lectura de expedientes ni expone datos personales adicionales. Los permisos de lectura
y escritura son distintos: no se deriva permiso sobre el padrón de poder matricular.

El POST conserva la autorización por destino de la matrícula individual. El nuevo
servicio no exige permisos de lectura adicionales para procesar UUID conocidos, igual
que el endpoint individual. Su respuesta no contiene nombre, CUI, contacto ni salud.

`bulk_initial.py` compone servicios de dominio y transacciones. `queries.py` filtra
candidatos. `api/initial_matriculations.py` contiene adaptadores y serializers. React
solo selecciona, presenta resultados y envía el lote. No sustituye la política central
ni crea otra infraestructura de listas. Aplican ADR-0004/0005/0006/0008.

Sin migraciones, dependencias, permisos ni variables nuevas. Se conservan las rutas
individuales y `/re-enrolments/bulk/`, el expediente único y el historial auditable.

## Pruebas e integración

- `backend/tests/api/test_bulk_initial_matriculation_api.py`: capacidad acumulada de
  preview, reversión, confirmación parcial, reintento sin duplicados, fecha distinta,
  límite/duplicados/UUID, errores por alumno, permisos, búsqueda paginada y alcance,
  cupo consumido entre revisión/confirmación y fallo técnico con rollback total.
- `frontend/src/test/BulkInitialEnrolmentWindow.test.jsx`: selección entre páginas,
  una escritura por etapa, revisión invalidada, errores parciales, transporte, cierre
  bloqueado y reintento de búsqueda. `newModulePages` prueba el acceso real desde la
  página; `moduleServices` verifica rutas/parámetros y la escritura única.
- **#638:** conservar su ventana nueva de reinscripción masiva. En el conflicto de
  `BulkEnrolmentWindow`, usar esta implementación: reemplaza el filtro local de
  matrículas por los candidatos nuevos, no necesita el loader de activas de #638.
- **#644/M7:** conservar `SectionOccupancyNotice` después de los campos, con
  `cycleId`, `sectionId` y `busy={submitting}`. La lectura se renueva al terminar
  revisión/confirmación. Actualizar la prueba antigua de lote para simular el POST
  masivo y el GET de candidatos, conservando la comprobación de refresco del cupo.
- **#645/M6:** conservar su menú y conectar la opción de altas iniciales a esta
  misma ventana. Mantener su formulario individual automático.
- Las ramas públicas no se fusionan automáticamente. La aceptación visual y los
  checks de la rama final integrada se registran por separado. Los catálogos
  académicos y la base `useServerList`/URL/selectores comunes siguen bajo #630.

## Reversión

Revertir el código del PR restaura el envío previo. No eliminar matrículas ni eventos
confirmados para revertir la interfaz. No hay migraciones de datos que deshacer.
