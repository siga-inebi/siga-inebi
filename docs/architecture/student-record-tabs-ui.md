# Expediente del estudiante con pestañas — E4/E11

Entrega del issue #632 y de la propuesta 1.5 de `docs/ux-ui.md`. Sustituye el
detalle modal del listado por `/app/alumnos/{public_id}?tab={seccion}`. No declara
completo el epic ni las operaciones de comunidad educativa pendientes.

## Experiencia y alcance

Ocho pestañas: **Datos, Encargados, Salud, Observaciones, Contactos, Matrículas,
Documentos y Asistencia**. La URL admite entrada directa, recarga y navegación del
historial. Una pestaña desconocida muestra Datos. El acceso desde el listado usa
el UUID público, sin descargar el padrón para resolver el expediente.

La ficha inicial consulta solo los datos básicos autorizados. Las colecciones se
consultan al visitar su pestaña, por alumno y con paginación del servidor. Una
colección visitada permanece montada y oculta al salir de su pestaña: conserva
página y borrador en memoria, sin repetir lecturas sensibles al volver. Navegar
a otro alumno desmonta el expediente; respuestas tardías no cambian la nueva ficha.

Los formularios existentes de edición, vinculación, salud, observaciones y contactos
se presentan en línea. No se apilan ventanas. Cancelar vuelve a la colección; un
rechazo conserva datos y muestra el error. Durante el envío se bloquean campos,
cambio de pestaña y retorno desde el botón de la ficha. Guardar un registro relacionado
recarga la primera página de su colección, con los filtros del alumno conservados.

- **Datos:** nombre, código, estado, sexo, nacionalidad, correo, teléfono, dirección,
  departamento, municipio, fotografía y fechas de registro/actualización disponibles.
  La foto conserva el visor independiente. Se reutiliza el formulario de edición.
- **Encargados:** relaciones vigentes e históricas, parentesco, principal, teléfono y
  fechas. La vinculación elige un encargado desde páginas del catálogo; no descarga
  todos los encargados. La entrega posterior [E5](guardian-relation-actions-ui.md)
  agrega edición de parentesco, cambio de principal y finalización con reemplazo;
  crear/buscar encargado E8 sigue pendiente.
- **Salud/Observaciones/Contactos:** lectura y creación existentes, con carga, errores,
  reintento y páginas; no se convierten denegaciones en «Sin registros». La entrega
  posterior [E6](student-record-actions-ui.md) agrega edición, desactivación con
  confirmación y consulta paginada de desactivados.
- **Matrículas:** historia completa con nombres de ciclo/grado/sección/jornada,
  estados y vigencias. `is_current` lo decide la lectura existente del servidor, no
  una comparación de fechas en React. No ejecuta movimientos ni reinscripciones.
- **Documentos:** todas las versiones del alumno, con nombre, versión, fecha y estado
  activo/histórico; acceso al archivo mediante el token de descarga existente.
  No cambia versiones, escaneo, integridad, emisión ni almacenamiento (DO1/DO2).
- **Asistencia:** movimientos del alumno, con fecha, captura, entrada/salida, origen
  y marca de supresión, sin ocultar historia ni implementar otra regla de asistencia.

## Privacidad y decisiones conservadas

El contrato `PersonSerializer` mantiene **CUI y fecha de nacimiento como write-only**,
según la decisión existente de RNF-LEG-001. La nueva ruta no los expone ni inventa
valores. «Datos» muestra los campos disponibles bajo ese contrato. No se amplían
permisos ni se agrega información sensible al listado o a la respuesta básica.

Salud/observaciones/contactos conservan autorización sensible y auditoría de sus
endpoints. Documentos conserva `ensure_document_access` y el protocolo de descarga
de uso único. El acceso básico no concede acceso a esas pestañas. Mientras #630
no publique permisos efectivos, la denegación se muestra en la sección correspondiente.

Las respuestas mantienen `Cache-Control: no-store`. Los datos y borradores viven en
memoria del expediente; no se escriben en localStorage, sessionStorage o IndexedDB.
La URL contiene únicamente UUID y clave de pestaña, sin nombres ni contenido sensible.

El estado del expediente sigue siendo un campo de la edición existente; la acción
independiente con confirmación, avisos y auditoría visible corresponde a **D5/E9**.
No se declara implementada en este PR. La desactivación E7 también queda separada.

## Contratos aditivos

- `GET /api/v1/students/records/{public_id}/`: mismo `StudentSerializer` y política
  `student_view_basic`/alcance que el detalle previo; resolución por UUID. Solo lectura.
  El detalle y las escrituras anteriores por ID interno conservan su contrato.
- `GET /api/v1/students/records/{public_id}/guardians/?page=1`: filtra relaciones por
  alumno autorizado **antes** de contar/paginar, con orden estable y `guardian_detail`.
  No sustituye ni rompe el endpoint global usado por otros clientes.
- `GET /api/v1/enrolments/students/{student_id}/record/?page=1`: requiere lectura
  básica con alcance; devuelve `public_id`, `cycle_name`, `grade_name`, `section_name`,
  `shift_name`, `status`, `effective_on`, `ends_on`, `is_current`. Sin catálogos globales.
- `GET /api/v1/documents/students/{student_id}/records/?page=1`: todas las versiones
  del alumno, con `document_read`, alcance y auditoría existentes. No incluye binarios.
- `GET /api/v1/attendance/events/?student_id={uuid}&page=1`: filtro UUID opcional,
  aplicado junto con alcance antes de paginar. Sin filtro conserva el listado anterior;
  UUID inválido responde 400. Orden estable por captura y PK.
- Los tres listados sensibles existentes se consumen mediante nuevos métodos frontend
  `listHealthNotesPage`/`listObservationsPage`/`listEmergencyContactsPage`, sin cambiar
  el retorno de los métodos antiguos en esta rama. Las escrituras mantienen sus contratos.

Las rutas nuevas básicas devuelven 403 sin permiso/alcance y 404 para UUID fuera del
queryset autorizado. Documentos usa su guard existente y puede denegar con 403. Las
colecciones conservan el sobre `{count,next,previous,results}` y páginas de 25.

## Arquitectura e integración

Aplican ADR-0004/0005/0006/0008. Lecturas por dominio en `queries.py`; adaptadores
HTTP sin ORM. Las reglas de negocio siguen en los servicios. React organiza datos,
formularios y estados de presentación, sin calcular vigencias o autorizaciones.

Se reutiliza exactamente el soporte de persistencia de campos de persona del
**PR #633** en `people.services.update_person`, necesario para que el editor del
expediente funcione de forma independiente desde `develop`. No se incorporan sus
cambios de docentes/encargados. Al combinar, conservar una sola implementación y
las pruebas de los tres perfiles. La edición conserva el servicio frontend existente
de escrituras separadas de persona/perfil/foto; no afirma atomicidad entre esas peticiones.

**#634:** conservar filtros/paginación backend y sus métodos compatibles para clientes
anteriores. `StudentRecordPage` reemplaza el detalle modal; no restaurar ventanas apiladas.
Sus pruebas de aislamiento y navegación se aplican al nuevo recorrido con pestañas.

**#635:** mantener búsqueda/actividad de los listados. La migración del listado principal
a `useServerList`, URL, tamaño de página y exportación depende de #630 y sigue pendiente;
este PR no crea otra infraestructura común. Se conservan alta, lista y exportación actuales.

Los PR de matrículas/plantillas conservan sus pantallas y operaciones. La ficha ofrece
lecturas específicas; no requiere fusionar esos PR para funcionar. No hay migraciones,
dependencias, permisos ni variables nuevas. Las ramas públicas no se fusionan automáticamente.

## Pruebas y reversión

`test_student_record_tabs_api.py` verifica UUID, campos protegidos, permisos y alcance,
segundas páginas de 26 registros por alumno, nombres/vigencia, persistencia de campos,
UUID inválidos y rechazo sensible. `StudentRecordPage.test.jsx` comprueba carga diferida,
borradores/páginas conservados, creación/edición en línea, errores/reintento, documentos,
asistencia y respuestas tardías. `AlumnosPage.test.jsx` conserva alta/listado/CSV y prueba
la nueva navegación; las pruebas de operaciones del detalle se trasladan al expediente.

Revertir los commits restaura la interfaz anterior. No borrar personas, expedientes,
matrículas, archivos, vínculos ni auditoría. No hay migración que deshacer.


## Evidencia local de esta entrega

Base: `develop` actualizado en `5f8630d`; rama `feat/632-student-record-tabs`.

- PostgreSQL local: **1790 pruebas aprobadas, 23 omitidas, cobertura 95.19%**.
- Frontend completo: **315 pruebas / 37 archivos, cobertura 85.29%**. Tras el
  ajuste visual final y la prueba adicional de etiqueta de sexo: **22 pruebas
  aprobadas** de listado/expediente. El CI verifica nuevamente el conjunto completo.
- Ruff y su formato, ESLint, Prettier de archivos modificados, 49 pruebas de
  herramientas, build y presupuestos aprobados. Carga inicial: **222182/230000
  bytes gzip**; mayor entrada con ruta: **237030/250000 bytes gzip**.
- Django check y comprobacion de migraciones aprobados. OpenAPI: **0 errores**;
  conserva 27 avisos (23 unicos) del esquema existente.
- HTTP real con sesion y CSRF: ruta directa, aislamiento y `no-store`, 26 notas
  en dos paginas sin repeticion, vinculos, contactos, observaciones, matricula
  vigente con nombres, documento sintetico y checksum de descarga, rechazo del
  token usado, asistencia por UUID, edicion/lectura/restauracion de direccion y
  municipio, y UUID invalido 400.
- Chromium real: Datos/Salud a **1440 x 1000**, Datos a **390 x 844**, ocho
  pestanas y ancho del documento igual al viewport. Se corrigieron el espaciado
  interior, la etiqueta No especificado y los controles de pestanas en movil.
  Capturas locales ignoradas: `tmp/local-runtime/632-record-tabs-*.png`.
- Instancia de revision aislada con datos sinteticos: puerto frontend **5185**,
  backend **8013**, base `siga_inebi_student_record_preview`. No se adjuntan
  cookies, tokens, base de datos, medios ni logs privados al repositorio.

La revision visual local es evidencia tecnica; no sustituye la aceptacion funcional
pendiente por parte del usuario. Docker no se ejecuto en esta validacion local.


### Combinacion de PR anteriores verificada localmente

Preview separado y no publicado: `tmp/worktrees/632-record-tabs-integration`,
commit `3c37404`, combina esta entrega con #633, #634 y #635.
**106 pruebas backend y 45 pruebas frontend aprobadas** (personas, docentes,
encargados, listado, nuevo expediente y contratos de servicios anteriores).

Conflictos detectados y resolucion probada para integrar posteriormente:

- #633: conservar `AlumnosPage` y sus pruebas de navegacion de esta entrega;
  los cinco campos pasan al editor de `StudentRecordPage`. Combinar ambas
  secciones de `api-conventions.md`. El soporte de `update_person` es identico.
- #634: conservar la ficha nueva y su suite `StudentRecordPage.test.jsx`.
  `StudentRecordPagination.test.jsx` prueba los botones y ventanas del modal
  retirado: debe sustituirse al integrar por los recorridos de pesta?as,
  borrador/pagina, reintento y refresco ya verificados en la nueva suite.
  Conservar `studentRecordServices.test.js` y los contratos antiguos.
  En `queries.py`, combinar el filtro opcional `student_public_id` con
  `guardian_relations_for_record`; `-id` y `-pk` son el mismo desempate.
- #635: conservar clases nuevas del expediente y colocar el decorador
  `GuardianListQuerySerializer` justo antes de `GuardianListCreateView`.
  Mantener filtros de comunidad y sus pruebas.

El preview no cambia ninguna rama publica ni declara integrados estos PR en
`develop`. Sus conflictos requieren estas resoluciones cuando se fusionen.
