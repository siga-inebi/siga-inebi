# E5: acciones de vínculos con encargados

Entrega del issue #632 sobre la pestaña Encargados del expediente del PR #647.
Aplican RF-EXP-004, RF-ALC-007/008 y ADR-0004/0005/0006/0008. No implementa E6,
desactivaciones de personas, alta/búsqueda de encargados E8 ni cambios D5/E9.

## Experiencia y reglas conservadas

- **Editar vínculo:** corregir únicamente `relationship_label` (parentesco o
  responsabilidad), entre 1 y 100 caracteres después de quitar espacios exteriores.
  No cambia estudiante, encargado, principal, fechas ni actividad. Permite corregir
  la descripción de un vínculo histórico sin reabrirlo ni restaurar su acceso.
  La auditoría conserva actor y valores anterior/nuevo.
- **Marcar como principal:** confirmación en línea, con nombre del encargado.
  Usa el servicio transaccional existente: el principal anterior conserva su vínculo;
  la restricción PostgreSQL mantiene como máximo un principal vigente.
- **Finalizar vínculo:** confirmación con aviso de corte del acceso asociado y
  conservación del historial. La fecha la determina el servicio existente.
  Para un principal se elige primero otro vínculo vigente del mismo estudiante;
  sin reemplazo no se ofrece confirmar. No cambia este requisito del dominio.
- Reemplazos por páginas de servidor, sin descargar el catálogo. La segunda página
  sigue disponible. El servidor excluye el vínculo a finalizar, los terminados,
  inactivos, futuros y los de otros estudiantes antes de contar/paginar.
- Un formulario por vez, sin ventanas apiladas. Cancelar no escribe. El rechazo
  conserva formulario/selección y muestra el error. Durante el envío se bloquean
  formulario, paginación y navegación por pestañas mediante el contrato del expediente.
  Al abrir una acción, su título recibe foco para hacer visible el formulario incluso
  cuando se eligió un vínculo al final de la página.
- Al guardar se recarga la primera página para mostrar el principal actualizado.
  Una finalización conserva la fila en el historial. No hay borrado físico.

Las capacidades de presentación llegan del servidor. No son autorizaciones
persistidas: cada escritura revalida permiso, alcance y estado; una selección
que quedó desactualizada puede rechazarse sin aplicar cambios parciales.

## Contratos API

### Edición aditiva

`PATCH /api/v1/students/guardian-relations/{id}/`

Antes respondía 405. Ahora acepta exclusivamente:

```json
{"relationship_label": "Responsable"}
```

Exige sesión, `student.edit_basic` y alcance sobre el estudiante. Respuesta 200
con el serializador existente; 400 por contenido vacío/largo o campos adicionales;
403 sin permiso/alcance habilitado y 404 para una relación fuera del alcance
autorizado. PUT y DELETE no se habilitan. GET conserva permiso de lectura.

El servicio `update_student_guardian_relation` bloquea estudiante y relación en
ese orden, escribe y audita dentro de la misma transacción. Si falla la auditoría,
se revierte la corrección. Evento `students.student_guardian_relation.updated`,
recurso `StudentGuardianRelation`, identificador y `context.changes.relationship_label`
con `before`/`after`. No audita contenido médico ni documentos.

### Lectura de capacidades y reemplazos

`GET /api/v1/students/records/{public_id}/guardians/?page=1`

Agrega por fila `actions: {edit, make_primary, end, requires_replacement}`.
Las tres primeras son booleanos calculados según alcance de edición y estado del
vínculo; la última indica el requisito del principal. Sin edición, la ficha sigue
siendo consultable y no ofrece las acciones de E5.

El parámetro opcional `replacement_for={id}` limita la colección a reemplazos
válidos según las condiciones del servicio de finalización existente. El vínculo
de referencia debe pertenecer al estudiante solicitado: 404 en caso contrario;
identificador inválido responde 400. Mantiene `{count,next,previous,results}`,
páginas de 25 y `Cache-Control: no-store`. No altera el listado global anterior.

### Operaciones existentes reutilizadas

- `POST /guardian-relations/{id}/make-primary/` con `{}`.
- `POST /guardian-relations/{id}/end/` con `{}` para secundario, o
  `{"replacement_relation": id}` al finalizar principal.

Ambas bajo `/api/v1/students/`, con `student.edit_basic` y alcance. Conservan
validación, transacciones, auditoría y respuestas existentes. La UI no cambia
fechas ni calcula vigencias. `queries.py` resuelve lecturas; `services.py`, reglas
y escrituras; vistas/serializadores adaptan el contrato.

## Evidencia

- PostgreSQL local: **1806 aprobadas, 23 omitidas, cobertura 95.22%**.
- Frontend completo: **324 pruebas / 39 archivos, cobertura 85.59%**.
- Subconjunto de vínculos/expediente: **54 backend y 22 frontend aprobadas**.
- API: corrección histórica sin alterar identidad/estado/fechas, auditoría antes y
  después, rechazo de campos protegidos, permisos/alcance, capacidades, 26 reemplazos
  en dos páginas, aislamiento y rechazo de reemplazo de otro alumno sin escrituras.
- Unidad: falla de auditoría revierte edición; validación del dominio, cambio único
  del principal y requisito de reemplazo existentes conservados.
- UI: reintento conserva borrador, confirmación/cancelación, reemplazo en página dos,
  ausencia de reemplazo, rechazo por estado cambiado, capacidades y doble envío.
- HTTP real con sesión/CSRF: 28 vínculos del estudiante, páginas/reemplazos, edición
  y restauración del texto, cambio de principal, rechazo de finalización sin reemplazo,
  finalización con reemplazo e historial intacto; rechazo de operaciones repetidas.
- Chromium: acciones, edición y confirmación de finalización a 1440 × 1000 y edición
  a 390 × 844; ancho del documento igual al viewport móvil. Capturas locales ignoradas
  `tmp/local-runtime/632-e5-*.png`, únicamente datos sintéticos.
- Lint/formato y build/presupuestos aprobados: inicial **222215/230000 bytes gzip**,
  mayor entrada con ruta **237050/250000 bytes gzip**.
- Django check y migraciones: aprobados, sin cambios de modelos. OpenAPI validado
  con **0 errores y 27 avisos existentes (23 únicos)**, sin agregar avisos.
- Herramientas: **49 pruebas de requerimientos y 20 de carga aprobadas**, más
  **7 pruebas de política de PR/archivos**. Las 9 pruebas auxiliares del ejecutor
  `scripts/quality/tests/test_run_phase7_checks.py` no pasan en Windows nativo por
  `os.getuid`/`os.getgid` ausentes. El ejecutor y sus pruebas son idénticos a
  `origin/develop`; se registra como limitación previa, sin modificar ese alcance.

Preview local: frontend **5186**, backend **8014**, base aislada
`siga_inebi_guardian_actions_preview`. Cookies, medios, logs y base no se versionan.
Docker no se ejecutó localmente; el PR registra el resultado de CI por separado.

## Integración y reversión

Rama creada desde `develop` actualizado (`5f8630d`) e incorporando por fast-forward
el expediente `82aea38` del **PR #647**, todavía abierto. Integrar #647 antes de E5.
El cambio propio de E5 se revisa comparando contra `feat/632-student-record-tabs`;
mientras #647 esté abierto, el diff hacia develop también contiene esa dependencia.
Si #647 se integra con squash, rebasar E5 para retirar los commits ya integrados.
Mantener las resoluciones para #633/#634/#635 documentadas en el expediente.

Sin modelos, migraciones, dependencias, variables ni permisos nuevos. No se cierra
el epic ni se cambian estados RF de la matriz; la aceptación visual del usuario
y la integración quedan pendientes. Revertir los commits propios de E5 conserva
el expediente de #647 y todos los vínculos, estados y eventos de auditoría; no
borrar filas ni intentar deshacer la historia mediante escrituras directas.
