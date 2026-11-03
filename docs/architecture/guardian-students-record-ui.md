# Estudiantes vinculados al encargado — G4, #632

## Alcance

El detalle de Padres de familia ofrece «Estudiantes vinculados». Sustituye el
detalle por una ventana con relaciones actuales e históricas paginadas, nombres y
códigos de estudiante, parentesco, condición de principal y fechas. Cada estudiante
enlaza a su expediente existente por UUID. «Volver al encargado» restaura el detalle;
alta y edición institucionales se conservan. El formulario de vínculo va en línea,
sin otra ventana apilada.

Rama creada desde `develop` actualizado a `0d6eeab`. Es independiente de #652,
#656 (G2) y #657 (G3). No incorpora paginación del padrón o desactivación. Al integrar
esas entregas se deben conservar sus acciones y refrescos junto con el acceso a
esta ventana. La navegación del padrón en URL corresponde a G2; no se declara
resuelta aquí. No se agregan permisos, migraciones o variables de entorno.

Entrega: [PR #658](https://github.com/siga-inebi/siga-inebi/pull/658), hacia `develop`.
CI, integración y aceptación pendientes al publicar; evidencia local debajo.

Se revisaron AGENTS, ADR-0004/0005/0006/0008, guías de permisos/textos, expediente
con pestañas, requerimientos de vínculos, alcance y bitácora. Se reutiliza la regla
existente de permisos sobre estudiantes; no hay una nueva decisión de autorización.

## Contratos aditivos

### Relaciones del encargado

`GET /api/v1/students/guardians/{id}/students/?page=1&page_size=25`

Exige sesión y `student.view_basic` con alcance vigente. Utiliza
`authorized_student_queryset`, filtrando por encargado y estudiantes autorizados
antes de contar/paginar. Incluye relaciones finalizadas o desactivadas y estudiantes
históricos que sigan dentro del alcance. Un permiso sin alcance se rechaza; un
alcance que no incluya estudiantes puede devolver una colección vacía conforme
al resolver compartido. No revela el total de relaciones fuera de alcance.

Respuesta: `{count, next, previous, results, actions}`. Cada resultado contiene
`id`, `student`, `relationship_label`, `is_primary`, `starts_at`, `ends_at`, `is_active`.
`student` contiene exclusivamente UUID, código, nombre completo, actividad y estado.
Sin CUI, nacimiento, correo, teléfono, salud ni documentos. Orden estable por fecha
de inicio descendente e ID descendente. Paginación compartida: 25 inicial, máximo 100;
no hay corte de 1.000. El total cuenta relaciones, no estudiantes distintos.

`actions.link_student` es verdadero solo si el encargado y su persona están activos
y existe al menos un estudiante elegible con lectura y edición dentro del alcance.
Es una capacidad de presentación; la escritura vuelve a autorizar. La consulta
carga persona/estudiante mediante `select_related`, sin una consulta de nombre por fila.

### Búsqueda de estudiantes elegibles

`GET /api/v1/students/guardians/{id}/student-candidates/?search=texto&page=1`

Exige `student.view_basic` y `student.edit_basic`, con intersección de sus alcances.
Devuelve el sobre paginado estándar y la referencia compacta del estudiante.
Solo ofrece estudiantes activos con estado Activo, sin vínculo vigente con ese
encargado. Encargado o persona desactivados producen cero candidatos. Busca por
nombre o código en el servidor; con menos de dos caracteres devuelve cero filas.
La UI usa `RemoteSearchSelect`, espera 300 ms y consulta la primera página de una
búsqueda acotada; hay que afinar el nombre/código si existen más coincidencias.
No descarga el padrón ni resuelve UUID con catálogos globales.

### Vinculación desde el encargado

`POST /api/v1/students/guardians/{id}/students/`

```json
{"student_public_id": "uuid-del-estudiante", "relationship_label": "Responsable"}
```

Respuesta 201 con la relación compacta. Guardian conserva su ID entero existente;
el estudiante se selecciona por UUID. Rechaza campos adicionales, parentesco vacío
o mayor de 100 caracteres. No acepta principal, fechas ni creación de estudiantes.

La autorización ocurre en el servicio, antes de la transacción, con lectura y
edición sobre el estudiante. Un estudiante inexistente o fuera de alcance responde
404 y se audita sin distinguir ambos motivos. Falta de permiso/alcance global
responde 403 con auditoría compartida. Un encargado inexistente devuelve 404.

La transacción bloquea primero el estudiante y luego el encargado; revalida actividad
del perfil/persona y estado del estudiante, rechaza vínculos vigentes duplicados
y reutiliza `create_student_guardian_relation`. Esa operación conserva la regla del
primer principal y el evento `students.student_guardian_relation.created` existente.
Una relación finalizada permanece en el historial al crear la nueva. Si falla la
auditoría se revierte toda la creación. No hay eliminación ni edición del historial.

Los nuevos endpoints envían `Cache-Control: no-store`. OpenAPI documenta parámetros,
respuesta con capacidades, búsqueda, payload y respuesta de creación.

## Interacción y errores

Las relaciones solo se consultan al abrir la sección. Su error se muestra con
«Reintentar» y no como ausencia de estudiantes. El botón de vínculo solo aparece
con capacidad explícita y una consulta exitosa. Cancelar no escribe. Durante el
envío se bloquean campos, doble envío, paginación, cierre y enlaces a expedientes.
El rechazo conserva estudiante/parentesco; el éxito vuelve a primera página y
consulta la colección. La caché del selector está separada por encargado y se
invalida al vincular para no seguir ofreciendo estudiantes ya vinculados.

No se persisten datos o borradores en localStorage/sessionStorage/IndexedDB. El
acceso al expediente conserva sus permisos existentes. La brecha de lectura general
del padrón de encargados de #643 no se declara resuelta; estos endpoints protegen
los datos de estudiantes por permiso y alcance.

## Evidencia y reversión

- `backend/tests/api/test_guardian_record_ui_api.py`: alcance antes de contar/paginar,
  historial, referencias sin datos sensibles, permisos, búsqueda y elegibilidad,
  creación/principal, duplicados, selección obsoleta, denegación, reversión por
  auditoría fallida, sin N+1, 1.001 relaciones y esquema de paginación/capacidades.
- Regresiones de `test_guardians_api.py` y `test_guardian_derived_scope.py` conservadas.
- `frontend/src/test/GuardianStudents.test.jsx`: apertura bajo demanda, regreso,
  historial y paginación, error/reintento, selector, cancelación, creación por UUID,
  refresco, renovación de candidatos, error con datos conservados y bloqueo de envío.
- `frontend/src/test/guardianRecordServices.test.js`: rutas, query strings y payload.
- `frontend/src/test/GuardiansPage.test.jsx`: formularios institucionales conservados.

Backend completo local: 2.100 aprobadas, 23 omitidas, cobertura 95,39 %. Regresión
API final ampliada: 80 aprobadas. Frontend completo: 537 pruebas en 69 archivos,
cobertura de líneas 88,27 %; verificación UI/adaptador final: 8 aprobadas.
Herramientas: 69 pruebas y políticas GitHub: 7. ESLint, Prettier, Ruff y formato
aprobados. Build: 226.834/230.000 bytes gzip iniciales, ruta máxima
19.251/20.000 y página fría máxima 246.085/250.000. Django check y detección de migraciones de modelo
sin cambios. OpenAPI: cero errores y 25 advertencias existentes en otros endpoints.
Entorno local: Node 24, Python 3.11 y PostgreSQL 18; CI usa versiones fijadas.
Docker local no ejecutado.

Chrome real en escritorio 1440×1000 y móvil 390×844: 27 relaciones en dos páginas,
historial visible, selector acotado, cancelar sin POST, guardar con un POST y recarga
a 28 relaciones; enlace por UUID abre el expediente. Sin desbordamiento de página.
Datos/capturas/logs sintéticos permanecen fuera del repo en `tmp/local-runtime/632-g4-*`.
Vista local: `http://127.0.0.1:5195/app/padres-de-familia`; buscar `EncargadoG4`.

Reversión: revertir esta entrega; no hay migración o transformación de datos. Las
relaciones creadas permanecen disponibles mediante los contratos anteriores.
Integración, CI y aceptación del usuario pendientes al publicar.

Comandos: desde `backend/`, `python -m pytest --create-db --reuse-db -q`
(recrea solo la base automatica de pruebas), `python manage.py check`,
`python manage.py makemigrations --check --dry-run`, `python manage.py spectacular
--validate --file <archivo-temporal>`; regresion final con `--no-cov --reuse-db` de
`test_guardian_record_ui_api.py`, `test_guardians_api.py`, `test_guardian_derived_scope.py`
y `test_community_list_filters_api.py`, en sus carpetas api/permissions.
Desde `frontend/`: `npm run test:coverage -- --maxWorkers=1 --no-file-parallelism`,
`npx vitest run src/test/GuardianStudents.test.jsx src/test/guardianRecordServices.test.js
--maxWorkers=1 --no-file-parallelism`, `npm run lint`, `npm run build` y Prettier
sobre archivos modificados. Ruff, herramientas y politicas se verifican desde la raiz
con los comandos de CI. Los resultados completos y las regresiones finales son
corridas distintas; los casos de volumen/esquema se incluyeron en la regresion final.
