# Reporte UX/UI — SIGA-INEBI

Fecha del análisis: 2026-10-17 · Rama analizada: `develop` (commit `c6605a6`).

Este reporte junta lo que hay que corregir en la experiencia de uso del sistema. Sale de leer el backend (`backend/apps/*/api`) y el frontend (`frontend/src/*`) módulo por módulo, y de cruzar los endpoints publicados con los que la interfaz realmente usa. Es un análisis del código: no incluye pruebas con usuarios ni mediciones en un entorno desplegado.

## Resumen ejecutivo

Las tablas por módulo suman **119 hallazgos (25 P0, 66 P1 y 28 P2)**, y la sección general agrega 22 problemas que afectan a todo el sistema. Cinco problemas explican la mayor parte de lo que se percibe como "el sistema está mal":

1. **El ciclo escolar no se puede operar de punta a punta.** No hay pantallas para crear secciones ni el plan de estudios del ciclo, que son requisito para activarlo. Tampoco se puede cerrar una unidad de evaluación, que es requisito para cerrarlo. Un ciclo nuevo queda en borrador para siempre, y uno activo no se puede cerrar desde la interfaz (2.1, 2.2, 2.11).
2. **No se puede dar acceso al sistema a nadie.** No existe el alta de cuentas, ni la página de activación, ni la gestión de roles y alcances. Además, dos contratos del backend piden identificadores internos que ningún cliente puede conocer (2.17).
3. **Los cambios guardados "no se ven".** Hay una caché de 5 minutos en sedes, jornadas, niveles, cursos y secciones, y la caché del frontend nunca se actualiza después de guardar. Peor aún: los formularios de edición de estudiantes, docentes y encargados descartan sin aviso la dirección, el sexo, la nacionalidad, el departamento y el municipio (1.2).
4. **La paginación no tiene una convención.** Conviven cuatro formas de listar: unas pantallas descargan todo el padrón (con corte silencioso en 1 000 registros), otras ven solo la primera página, y el selector de filas por página no funciona en ninguna tabla (1.1).
5. **El trabajo repetitivo se hace de uno en uno.** Las notas se capturan con un formulario por nota y las matrículas por lote se envían de a una, aunque el backend ya ofrece operaciones masivas (2.10, 2.11).

Las reglas de negocio que el código no cerraba quedan decididas en la sección 3 (D1–D10). La sección 4 ordena el trabajo en siete fases, de las correcciones rápidas al pulido.

## Cómo leer este reporte

- **Sección 1 — General:** problemas que afectan a todos o casi todos los módulos (paginación, caché, selectores, permisos). Conviene resolverlos primero, porque varios síntomas de los módulos salen de aquí.
- **Sección 2 — Por módulo:** hallazgos propios de cada pantalla.
- **Sección 3 — Decisiones de negocio:** las reglas que el código no cerraba, ya decididas (D1–D10).
- **Sección 4 — Orden sugerido de trabajo.**

Cada hallazgo lleva una prioridad:

| Prioridad | Significado |
|---|---|
| **P0** | Bloquea una operación, pierde datos sin avisar o muestra información incorrecta. |
| **P1** | La operación se puede hacer, pero cuesta demasiados clics, es confusa o carga de más. |
| **P2** | Mejora de claridad, consistencia o comodidad. |

También se marca el tipo: **Sin UI** (el backend ya lo permite y no hay forma de hacerlo desde la interfaz), **Bug**, **Rendimiento**, **Clics** o **Claridad**.

---

## 1. General (aplica a todos los módulos)

### 1.1 Paginación: no hay una convención, hay cuatro

**Situación actual.** Conviven cuatro formas distintas de listar datos:

| Patrón | Qué hace | Dónde se usa |
|---|---|---|
| `useLocalList` + `collectAllPages` | Descarga **todas** las páginas del backend, una tras otra, y pagina en el navegador. | Ninguna. **Resuelto en #631:** Estudiantes, Docentes y Padres de familia pasaron a `useServerList` y `useLocalList` se eliminó. |
| `usePaginatedList` | Pide solo la página que se ve (paginación real en el servidor). | Personas, Ciclos, Sedes, Niveles, Cursos, Aulas, Plantillas, Tipos de documento, Asignaciones, Matrículas, Asistencia, Evaluación, Alertas, Cuentas |
| Catálogos (`useCatalogOptions` + `collectAllPages`) | Descarga el catálogo completo para llenar un desplegable o traducir un UUID a un nombre. | Casi todos los formularios y Matrículas, Evaluación, Asignaciones |
| Llamada directa a la primera página | Usa `page.results` e ignora las demás páginas. | Relaciones con encargados, notas de salud, observaciones y contactos de emergencia del estudiante |

**Problemas que provoca:**

1. **P0 · Bug — El selector "Filas por página" no funciona en ninguna tabla.** [DataTable.jsx](../frontend/src/shared/ui/table/DataTable.jsx) siempre muestra las opciones `[10, 25, 50, 100]`, pero solo cambia algo si la pantalla le pasa `onRowsPerPageChange`, y **ninguna pantalla lo pasa**. Al elegir 50 no ocurre nada. Además, el backend ignora `?page_size=`: usa `PageNumberPagination` sin `page_size_query_param` ([base.py:219-220](../backend/config/settings/base.py#L219-L220)). El `listTypes({ page_size: 100 })` de [TemplatesPage.jsx](../frontend/src/documents/TemplatesPage.jsx) tampoco tiene efecto.
2. **P1 · Rendimiento — Estudiantes, Docentes y Padres descargan todo el padrón.** **Resuelto en #631:** las tres pantallas piden solo la página visible con `useServerList`; `collectAllPages` queda solo para su exportación CSV. [studentsService.js:11](../frontend/src/students/studentsService.js#L11), [teachersService.js:10](../frontend/src/teachers/teachersService.js#L10) y [guardiansService.js:11](../frontend/src/guardians/guardiansService.js#L11) recorren todas las páginas. La tabla muestra "página 1", pero todas las páginas ya se pidieron en peticiones seguidas. Es lo que se ve en la pestaña Red.
3. **P0 · Bug — Corte silencioso en 1 000 registros.** [pages.js:2](../frontend/src/shared/api/pages.js#L2) limita el recorrido a 40 páginas × 25 = 1 000 filas. Con más registros, el resto deja de existir para la búsqueda, la exportación CSV y los desplegables, sin ningún aviso.
4. **P0 · Bug — Listas truncadas a 25.** `listGuardianRelations`, `listHealthNotes`, `listObservations` y `listEmergencyContacts` en [studentsService.js](../frontend/src/students/studentsService.js) devuelven solo `page.results` de la primera página. En el caso de los encargados es peor: se piden **todas las relaciones del sistema** (sin filtrar por estudiante) y se filtran en el navegador. En cuanto el sistema tiene más de 25 relaciones, los encargados de muchos estudiantes "desaparecen" de su ficha.
5. **P1 · Rendimiento — Las pantallas cargan catálogos ajenos para traducir UUIDs.** Ver Matrículas (2.9) y Evaluación (2.11). El backend responde solo identificadores (`student_id`, `section_id`…) y el frontend descarga los padrones completos para mostrar nombres.
6. **P1 · Bug — El interruptor "Mostrar desactivados" no hace nada en algunos listados.** `/people/`, `/teachers/`, `/students/` y `/students/guardians/` no leen `include_inactive`: devuelven activos e inactivos mezclados siempre. En Personas el interruptor se ve, pero no cambia el resultado.
7. **P1 · Claridad — La búsqueda es inconsistente.** Estudiantes, Docentes y Padres buscan solo por nombre y en el navegador. Personas y el resto no tienen búsqueda. El backend solo ofrece `?search=` en `/students/` (código, nombre y apellido).

**Convención propuesta (una sola para todo el sistema):**

*Backend*

- Una clase de paginación propia en `apps/common`, por ejemplo `StandardPagination(PageNumberPagination)`, con `page_size = 25`, `page_size_query_param = "page_size"` y `max_page_size = 100`. Se registra como `DEFAULT_PAGINATION_CLASS`.
- Todo listado acepta los mismos parámetros: `page`, `page_size`, `search`, `ordering`, `include_inactive` y los filtros propios del dominio (`academic_cycle_id`, `section_id`, `status`, etc.).
- `include_inactive` se respeta en **todos** los listados con baja lógica.
- Los listados que la interfaz muestra en tabla incluyen los nombres que se van a pintar, por ejemplo `student: {public_id, full_name, student_code}` en lugar de solo `student_id`. Así ninguna pantalla necesita descargar otro catálogo para traducir.
- Los recursos hijos se filtran en el servidor: `/students/guardian-relations/?student=<id>`, o mejor `/students/<id>/guardian-relations/`.

*Frontend*

- Un único hook de listado sobre react-query (por ejemplo `useServerList`) que maneje `page`, `pageSize`, `search` (con *debounce*), filtros y `refresh`. Debe entregar siempre `onRowsPerPageChange` a `DataTable`.
- Página, tamaño, búsqueda y filtros viven en la URL (`?page=2&page_size=50&search=ana`). Así, volver atrás, recargar o compartir el enlace conserva la vista.
- Se eliminan `useLocalList` y el uso de `collectAllPages` en pantallas. `collectAllPages` queda, como mucho, para una exportación que la persona pide explícitamente, con barra de progreso y sin tope silencioso.
- `DataTable` no muestra el selector de filas si la pantalla no lo soporta. Así nunca vuelve a aparecer un control que no hace nada.
- La exportación CSV usa los filtros actuales y la hace el backend (endpoint `/export/`), o recorre las páginas a pedido. Hoy exporta solo lo que se descargó, que tiene el tope de 1 000.

### 1.2 Los cambios guardados tardan hasta 5 minutos en verse

Hay **cuatro causas distintas** que se suman:

1. **P0 · Bug — Caché HTTP de 5 minutos en catálogos editables.** [academics/api/views.py:87](../backend/apps/academics/api/views.py#L87) define `CATALOGUE_CACHE_SECONDS = 300`, que se aplica a **sedes, jornadas, niveles, cursos y secciones**. `CacheableListMixin` responde `Cache-Control: private, max-age=300`, y durante esos 5 minutos el navegador devuelve el listado viejo **sin preguntar al servidor**. Ciclos ya se corrigió con `cache_seconds = 0` (revalidación por ETag). Es la causa directa de que **los cursos tarden 5 minutos**.
   *Corrección:* `cache_seconds = 0` en todos los catálogos editables (se conserva el ETag y la respuesta 304), o directamente quitar el mixin de esas vistas.
2. **P0 · Bug — Los formularios de edición descartan campos sin avisar.** En Estudiantes, Docentes y Padres de familia, el formulario de edición muestra *sexo, nacionalidad, dirección, departamento y municipio*, pero el `handleUpdate` solo envía `first_name`, `last_name`, `email` y `phone_number` a `/people/<id>/`. Quien cambia la dirección y guarda ve que "no se guardó". Esto puede pasar por un retraso, pero es pérdida de datos. Archivos: [AlumnosPage.jsx](../frontend/src/students/AlumnosPage.jsx), [DocentesPage.jsx](../frontend/src/teachers/DocentesPage.jsx) y [GuardiansPage.jsx](../frontend/src/guardians/GuardiansPage.jsx) (función `handleUpdate`).
3. **P1 · Bug — La caché de react-query nunca se invalida.** No hay un solo `invalidateQueries` en el frontend. Los catálogos de los desplegables (docentes, estudiantes, cursos, secciones, ciclos) se guardan 60 s ([queryClient.js:17](../frontend/src/shared/api/queryClient.js#L17)): crear un docente y abrir enseguida "Nueva asignación" no lo muestra. Los contadores del menú lateral se guardan **5 minutos** ([useModuleCounts.js:5](../frontend/src/app/useModuleCounts.js#L5)).
   *Corrección:* después de cada escritura, invalidar las claves afectadas (`queryClient.invalidateQueries({ queryKey: ["catalog"] })`, `["students"]`, etc.). La convención es: *toda mutación invalida lo que muestra*.
4. **P2 · Riesgo — Las claves de caché dependen de `load.name`.** `useCatalogOptions` arma la clave con el nombre de la función ([useCatalogOptions.js:26](../frontend/src/shared/catalogs/useCatalogOptions.js#L26)). En el *build* de producción los nombres se minifican, así que dos catálogos de chunks distintos podrían compartir clave y mostrarse cruzados. Conviene usar claves explícitas de `queryKeys.js` (por ejemplo `queryKeys.catalog("teachers")`).

### 1.3 Selectores que no escalan

- **P1 · Clics — Los desplegables no permiten buscar.** `EntityFormWindow` usa `FormSelect` (un `<select>` simple) para estudiante, docente, matrícula, encargado, etc. Con cientos de opciones, encontrar a alguien obliga a desplazarse por toda la lista. Ya existen `SearchableSelect` y `useSearchableCatalog` (búsqueda en el servidor). Hay que convertirlos en el tipo de campo por defecto para entidades grandes: `type: "search-select"` dentro de `EntityFormWindow`.
- **P1 · Rendimiento —** Cada uno de esos desplegables descarga el padrón completo (ver 1.1). Con búsqueda en el servidor solo se pide lo que la persona escribe.

### 1.4 El menú muestra todo a todos

- **P1 · Claridad —** [permissions.js](../frontend/src/auth/permissions.js) devuelve `true` en todas sus funciones, y `/auth/me/` no devuelve roles ni permisos. Cualquier usuario ve todos los módulos y se entera de que no tiene acceso con un error 403 después de hacer clic.
  *Corrección:* que `/auth/me/` incluya los permisos atómicos efectivos (o un resumen por módulo), y que el menú y los botones se oculten o deshabiliten con una explicación. El backend sigue siendo la autoridad; esto es solo presentación.

### 1.5 Ventanas apiladas en lugar de vistas de detalle

- **P1 · Clics —** El patrón "tabla → ventana de detalle → otra ventana → formulario" se repite en Estudiantes (detalle → Salud → Nueva nota), Plantillas, Matrículas y Evaluación. Llegar a un dato requiere 3 o 4 ventanas superpuestas, y al cerrar una se pierde el contexto.
  *Propuesta:* una ruta de detalle por entidad (`/app/alumnos/:id`) con pestañas (Datos, Encargados, Salud, Observaciones, Contactos, Matrículas, Documentos, Asistencia), y formularios en línea o en un panel lateral.

### 1.6 Consistencia visual y de textos

- **P2 · Claridad —** Las fechas se muestran crudas (`2026-03-01`) en notas de salud y observaciones; en otras pantallas se usa `formatDate`. Hay que usar siempre `formatDate` / `formatDateTime`.
- **P2 · Claridad —** Hay textos con y sin tilde mezclados en la misma pantalla ("Codigo", "Teléfono", "Telefono", "Ano del ciclo"). Conviene definir una regla (con tildes) y aplicarla a toda la interfaz.
- **P2 · Claridad —** Los códigos se generan solos en Estudiantes, Docentes, Sedes y Niveles, pero en Plantillas, Cursos y Tipos de documento se escriben a mano. Conviene unificar: sugerir siempre el código, como ya hace `next-code/`.
- **P2 · Claridad —** Los mensajes de error del backend mezclan inglés y español ("Student not found.", "Teacher not found." en `queries.py`). Hay que traducirlos todos.

### 1.7 Panel principal

- **P1 · Rendimiento —** [useDashboardSummary.js](../frontend/src/dashboard/useDashboardSummary.js) descarga **todos** los estudiantes, docentes y encargados solo para contar `records.length`, mientras el menú lateral ya obtiene el `count` en una petición de una página. Además, el número queda cortado en 1 000. Hay que reutilizar `useModuleCounts` o un endpoint `/dashboard/summary/`. **Resuelto en #630 (PR #651):** el panel reutiliza `useModuleCountsState`, la misma fuente y la misma cache que los badges del menú: una petición de una fila por módulo, usando `count`, sin descargar padrones ni tope de 1 000.

---

## 2. Por módulo

### 2.1 Ciclo escolar

El ciclo es la raíz de todo (secciones, matrícula, asignaciones, evaluación) y hoy su ciclo de vida **no se puede completar desde la interfaz**.

| # | Prioridad · Tipo | Hallazgo |
|---|---|---|
| C1 | **P0 · Sin UI** | **Un ciclo nuevo no se puede activar.** Activar exige ([services.py, `_academic_cycle_opening_gaps`](../backend/apps/academics/services.py)) al menos una oferta de grado, secciones activas, plan de estudios por grado y docente asignado para cada sección × curso. La interfaz **no tiene pantalla para crear secciones** (`POST /academics/sections/`) **ni plan de estudios del ciclo** (`/academics/curriculum-plans/`). Un ciclo creado con "Nuevo ciclo" nace vacío y se queda en borrador para siempre. Por eso "no se le pueden asignar clases, ni maestros, ni cursos": el selector de sección de Asignaciones queda vacío. |
| C2 | **P0 · Bug** | **Clonar solo funciona con ciclos cerrados**, pero el botón aparece en todos. El backend responde "Solo se puede clonar un ciclo escolar cerrado." ([services.py, `clone_academic_cycle`](../backend/apps/academics/services.py)) **después** de que la persona llenó el formulario. **Decidido (D2): se permite clonar un ciclo activo.** Cambio de backend: `clone_academic_cycle` acepta ciclos `ACTIVE` y `CLOSED`, y sigue rechazando los borradores, con un mensaje claro. En la interfaz, el botón se deshabilita en borradores con un *tooltip* que diga por qué. Al clonar un ciclo activo se copian sus asignaciones **vigentes** (`ends_on` nulo), igual que hoy. |
| C3 | **P0 · Sin UI** | **Un ciclo en borrador no se puede editar.** No existe `PATCH` del ciclo en el backend ni acción "Editar" en la interfaz. Si se clonó con un nombre, fechas o descripción equivocados, no hay forma de corregirlo. Hace falta un `PATCH /academics/cycles/<id>/` (solo en borrador) y el botón correspondiente. |
| C4 | **P0 · Sin UI** | **Un ciclo activo no se puede cerrar si tiene unidades de evaluación**, porque la interfaz no tiene la acción "Cerrar unidad" (ver Evaluación, V1), y cerrar el ciclo exige todas las unidades cerradas. |
| C5 | **P0 · Bug / Claridad** | **El texto de "Activar" es falso.** La confirmación dice "El ciclo activo anterior queda cerrado", y el subtítulo dice "Activar un ciclo cierra el anterior". El backend hace lo contrario: rechaza con "Hay que cerrar el ciclo activo antes de activar otro." **Decidido (D1): se exige cerrar el anterior; el backend se queda como está.** Solo cambia la interfaz: corregir el subtítulo y la confirmación y, mientras exista otro ciclo activo, deshabilitar "Activar" con el *tooltip* "Cierre primero el ciclo «X»" y un enlace a ese ciclo. |
| C10 | **P0 · Sin UI** | **Volver a borrador un ciclo activado por error.** **Decidido (D3): debe existir.** No hay endpoint ni botón. Hace falta un `POST /academics/cycles/<id>/revert-to-draft/` con motivo obligatorio, auditado, y la acción "Volver a borrador" (con confirmación) en la fila del ciclo activo. Condiciones de uso en D6. |
| C6 | **P1 · Sin UI** | **Reabrir ciclo** (`POST /cycles/<id>/reopen/`, con motivo obligatorio) no tiene botón. |
| C7 | **P1 · Claridad** | Cuando activar falla, el backend devuelve una lista larga de faltantes en un solo párrafo ("falta asignar docente para X en la sección Y…; …"). Conviene una **lista de verificación previa a la activación**: una vista que muestre qué falta (ofertas, secciones, plan, docentes), con enlaces para resolver cada punto, antes de pulsar "Activar". |
| C8 | **P1 · Sin UI** | **Días no computables** (`declare_non_computable_day`, RF-JOR-010) existe como servicio, pero no tiene endpoint ni pantalla. |
| C9 | **P2 · Clics** | El detalle histórico es de solo lectura y se abre en ventana. En un ciclo en borrador o activo, ese detalle debería ser el **tablero de preparación del ciclo**: secciones, plan, asignaciones y horarios en un solo lugar. |

**Propuesta de flujo (con las decisiones D1–D3):**

```
                 Clonar (desde activo o cerrado)
                ┌───────────────────────────────┐
                ▼                               │
Nuevo ──▶ BORRADOR ──Activar──▶ ACTIVO ──Cerrar──▶ CERRADO
            ▲   (exige que no haya        │            │
            │    otro ciclo activo)       │            │
            └──── Volver a borrador ──────┘            │
                  (motivo + condiciones)               │
                                   ACTIVO ◀── Reabrir ─┘
                                          (motivo + permiso)
```

- **Borrador:** tablero de preparación con pestañas Secciones / Plan de estudios / Asignaciones / Horarios, más la lista de verificación de activación (C7). Se puede editar (C3).
- **Activo:** evaluación, matrícula y asistencia. Acciones: Clonar (para preparar el siguiente ciclo), Cerrar y Volver a borrador.
- **Cerrado:** solo lectura. Acciones: Clonar y Reabrir.

### 2.2 Secciones, plan de estudios y horarios (no existen en la interfaz)

| # | Prioridad · Tipo | Hallazgo |
|---|---|---|
| S1 | **P0 · Sin UI** | CRUD de **secciones**: `GET/POST /academics/sections/`, `GET/PATCH/DELETE /academics/sections/<id>/`. Solo se crean indirectamente al clonar. |
| S2 | **P0 · Sin UI** | **Plan de estudios por ciclo**: `/academics/curriculum-plans/` (CRUD). No confundir con "Cursos del nivel" de la pantalla Niveles, que es el vínculo nivel ↔ curso. Hoy la interfaz no deja claro que son dos cosas distintas. |
| S3 | **P1 · Sin UI** | **Horarios**: bloques horarios por jornada (`/shifts/<id>/schedule-blocks/`), sesiones de clase por sección (`/sections/<id>/class-sessions/`), clonar horario entre secciones, carga semanal (`/sections/<id>/weekly-load/`) y publicación del horario del ciclo (`/cycles/<id>/schedule-publication/`). |
| S4 | **P1 · Sin UI** | **Mi horario semanal** (`/identity/me/schedule/`) para docentes. |
| S5 | **P1 · Sin UI** | **Ocupación de secciones** (`/enrolments/sections/occupancy/`): cupo usado y disponible. Sería útil al matricular. |

### 2.3 Sedes, jornadas y aulas

| # | Prioridad · Tipo | Hallazgo |
|---|---|---|
| A1 | **P0 · Bug** | Caché de 5 minutos en sedes y jornadas (ver 1.2.1): una sede o jornada recién creada no aparece en los selectores ni en la propia tabla al recargar. |
| A2 | **P1 · Rendimiento** | [RoomsPage.jsx](../frontend/src/academics/RoomsPage.jsx) descarga todas las sedes (`collectAllPages`) para pintar el nombre de la sede en cada aula. El listado de aulas debería traer `campus: {public_id, name}`. |
| A3 | **P2 · Clics** | La relación sede → jornadas se muestra como una tabla maestro-detalle que aparece al seleccionar una fila. No hay ninguna pista visual de que hay que hacer clic en la sede para ver sus jornadas. Conviene una flecha o un chip "Ver jornadas (2)". |

### 2.4 Niveles, grados y cursos

| # | Prioridad · Tipo | Hallazgo |
|---|---|---|
| N1 | **P0 · Bug** | Caché de 5 minutos en niveles y cursos (ver 1.2.1). Es la causa de que "los cursos no se ven hasta los 5 minutos". |
| N2 | **P1 · Claridad** | "Plan de estudios" en Niveles (cursos que se imparten en el nivel, con horas semanales) **no es** el plan de estudios del ciclo que exige la activación. Hay que renombrarlo ("Cursos del nivel") y explicar la relación con el plan del ciclo, o generar el plan del ciclo a partir de él. |
| N3 | **P2 · Clics** | Igual que en Sedes: el maestro-detalle (nivel → grados → cursos) no muestra que hay que seleccionar una fila. |

### 2.5 Asignaciones docentes

| # | Prioridad · Tipo | Hallazgo |
|---|---|---|
| AD1 | **P0 · Bloqueado por S1** | Sin secciones en el ciclo nuevo, el selector de sección queda vacío y no se puede asignar nada. |
| AD2 | **P1 · Rendimiento** | [BulkAssignmentWindow.jsx](../frontend/src/academics/BulkAssignmentWindow.jsx) y [CloneAssignmentsWindow.jsx](../frontend/src/academics/CloneAssignmentsWindow.jsx) recorren todas las páginas de asignaciones de dos ciclos para compararlas en el navegador. |
| AD3 | **P1 · Clics** | No hay una vista de **matriz sección × curso** del ciclo que muestre de un vistazo qué falta asignar (justo lo que bloquea la activación). Con esa vista, asignar sería un clic por celda. |
| AD4 | **P2 · Claridad** | No se puede ver "qué da este docente" desde su ficha en Docentes. |

### 2.6 Estudiantes

| # | Prioridad · Tipo | Hallazgo |
|---|---|---|
| E1 | **P0 · Bug** | La edición descarta sexo, nacionalidad, dirección, departamento y municipio (ver 1.2.2). |
| E2 | **P0 · Bug** | Los encargados del estudiante salen de la primera página de **todas** las relaciones del sistema (ver 1.1.4). Con más de 25 relaciones, faltan encargados. |
| E3 | **P1 · Rendimiento** | Se descarga todo el padrón para paginar en el navegador (ver 1.1.2), con tope de 1 000 (ver 1.1.3). **Resuelto en #631:** paginación y búsqueda (nombre, código o CUI) en el servidor. **Seguimiento #632:** `useServerList`, tamaño y URL; CSV completo explícito con avance/cancelación en [E3/E10](architecture/student-server-list-ui.md). Pendiente de integración y aceptación. |
| E4 | **P1 · Clics** | El detalle abre ventanas encadenadas: Detalle → Salud → Nueva nota. Para consultar salud, observaciones y contactos de un mismo estudiante hacen falta 6 o más clics y tres ventanas superpuestas. Ver la propuesta de expediente con pestañas (1.5).  **Seguimiento #632:** [expediente con pestanas](architecture/student-record-tabs-ui.md), ruta propia, ocho secciones, lecturas diferidas/paginadas y formularios en linea; integracion y aceptacion pendientes. |
| E5 | **P1 · Sin UI** | **Encargados:** marcar como principal (`/guardian-relations/<id>/make-primary/`), finalizar la relación (`/guardian-relations/<id>/end/`) y editarla. Solo se puede vincular.  Seguimiento: [acciones de vinculos E5](architecture/guardian-relation-actions-ui.md), implementadas y probadas; dependen del expediente #647, con integracion y aceptacion pendientes. |
| E6 | **P1 · Sin UI** | **Notas de salud, observaciones y contactos de emergencia:** editar y desactivar (`PATCH/DELETE` en `/health-notes/<id>/`, `/observations/<id>/` y `/emergency-contacts/<id>/`). Solo se puede crear.  Seguimiento: [acciones del expediente E6](architecture/student-record-actions-ui.md), edicion, desactivacion con confirmacion e historial paginado; integracion y aceptacion pendientes. |
| E7 | **P1 · Sin UI** | **Desactivar estudiante** (`DELETE /students/<id>/`).  Seguimiento: [desactivacion desde expediente E7](architecture/student-deactivation-ui.md), confirmacion, auditoria atomica y conservacion de historial; integracion y aceptacion pendientes. |
| E8 | **P1 · Clics** | "Vincular encargado" carga todos los encargados en un desplegable sin búsqueda. Tampoco permite crear el encargado en el mismo paso: hay que salir a "Padres de familia", crearlo y volver.  Seguimiento #632: [E8/E9/D5](architecture/student-guardian-link-and-status-ui.md), implementado con pruebas; integracion y aceptacion pendientes. |
| E9 | **P2 · Claridad** | **Decidido (D5): el estado del expediente se sigue editando a mano.** Para que eso no deje datos contradictorios: (a) sacar el estado del formulario general y cambiarlo con una acción propia, "Cambiar estado", con confirmación; (b) avisar cuando el estado elegido choca con la matrícula (por ejemplo, "Retirado" con una matrícula activa, o "Activo" sin ninguna matrícula vigente), sin bloquear; (c) mostrar en la ficha quién cambió el estado y cuándo, a partir de la auditoría.  Seguimiento #632: [E8/E9/D5](architecture/student-guardian-link-and-status-ui.md), implementado con pruebas; integracion y aceptacion pendientes. |
| E10 | **P2 · Claridad** | La búsqueda solo mira el nombre; el backend ya busca por código. Tampoco hay filtro por estado. **Seguimiento #632:** búsqueda de servidor por nombre/código, filtro por estado y actividad independiente en [E3/E10](architecture/student-server-list-ui.md). Pendiente de integración y aceptación. |
| E11 | **P2 · Claridad** | La ficha no muestra matrícula vigente, sección, historial de matrícula, documentos ni asistencia.  **Seguimiento #632:** [expediente con pestanas](architecture/student-record-tabs-ui.md), ruta propia, ocho secciones, lecturas diferidas/paginadas y formularios en linea; integracion y aceptacion pendientes. |

### 2.7 Docentes

| # | Prioridad · Tipo | Hallazgo |
|---|---|---|
| T1 | **P0 · Bug** | La edición descarta sexo, nacionalidad, dirección, departamento y municipio (ver 1.2.2). |
| T2 | **P1 · Rendimiento** | Se descarga todo el padrón (ver 1.1.2). El backend no tiene `?search=` ni filtro por puesto: el filtro "Puesto" funciona solo sobre lo descargado. **Resuelto en #631:** el backend ya acepta `search` y `position`; la pantalla pagina, busca y filtra por puesto en el servidor. **Seguimiento #632:** contratos de servidor en #635; adopción de `useServerList`, filtros, URL y CSV completo en [T2/T4](architecture/teacher-server-list-ui.md). Pendiente de integración y aceptación. |
| T3 | **P1 · Sin UI** | **Desactivar docente** (`DELETE /teachers/<id>/`). **Seguimiento #632:** confirmación, permiso aprobado `teacher.deactivate` con alcance `teachers`, baja y auditoría atómicas, idempotencia e historial conservado en [T3](architecture/teacher-deactivation-ui.md). Pendiente de integración y aceptación. |
| T4 | **P2 · Claridad** | Los puestos estaban fijos en `teachersMock.js` y duplicaban el backend. **Seguimiento #632:** catálogo autenticado `GET /teachers/positions/` desde `Teacher.Position`, compartido por filtro y formularios; archivo duplicado retirado. Contrato, errores y pruebas en [T2/T4](architecture/teacher-server-list-ui.md). Pendiente de integración y aceptación. |

### 2.8 Padres de familia (encargados)

| # | Prioridad · Tipo | Hallazgo |
|---|---|---|
| G1 | **P0 · Bug** | La edición descarta sexo, nacionalidad, dirección, departamento y municipio (ver 1.2.2). |
| G2 | **P1 · Rendimiento** | Se descarga todo el padrón (ver 1.1.2). El backend no tiene `?search=`. **Resuelto en #631:** paginación y búsqueda (nombre o CUI) en el servidor. **Seguimiento #632:** Listado migrado a paginación y búsqueda del servidor, actividad optativa, URL y CSV completo sin tope de 1.000. Seguimiento: [listado de encargados G2](architecture/guardian-server-list-ui.md); pruebas locales aprobadas, integración y aceptación pendientes. El backend admite `search` desde #635. |
| G3 | **P1 · Sin UI** | **Desactivar encargado** (`DELETE /students/guardians/<id>/`). **Seguimiento:** Desactivación implementada con confirmación, `guardian.deactivate` y alcance `students`, auditoría atómica e historial conservado. [Entrega G3](architecture/guardian-deactivation-ui.md); integración y aceptación pendientes. |
| G4 | **P1 · Claridad** | La ficha del encargado no muestra a qué estudiantes está vinculado, ni permite vincularlo desde aquí. **Seguimiento:** Ficha con estudiantes vinculados, historial paginado, acceso al expediente y vinculación por búsqueda bajo permiso/alcance del alumno. [Entrega G4](architecture/guardian-students-record-ui.md); integración y aceptación pendientes. |

### 2.9 Personas

| # | Prioridad · Tipo | Hallazgo |
|---|---|---|
| PE1 | **P1 · Bug** | "Mostrar desactivados" no hace nada: `/people/` siempre devuelve todas las personas (ver 1.1.6). |
| PE2 | **P1 · Claridad** | El alta pide solo nombre, apellido, correo, teléfono e identificador. **Seguimiento #632/D10:** Personas ofrece «Convertir» a estudiante, docente o encargado; los formularios también buscan la persona registrada antes del alta. Se completa la misma persona por `person_public_id`, sin crear otra. [Contrato y pruebas](architecture/person-conversion-ui.md). |
| PE3 | **P2 · Claridad** | **Seguimiento #632:** búsqueda por nombre o CUI en el servidor, perfiles estudiante/docente/encargado/cuenta en la fila, paginación y estado en URL. [Contrato y pruebas](architecture/person-conversion-ui.md). |
| PE4 | **P2 · Claridad** | El propósito de la pantalla no es claro para un usuario operativo ("registro base de identidad institucional"). Conviene moverla a Administración o mostrarla solo a quien la necesita. |

### 2.10 Matrículas

#### Seguimiento de M4: consulta de promoción

Entrega de #632: la acción **Consultar promoción** en cada fila de Vigentes e
Historial muestra promoción, repitencia o graduación, grado elegible, subáreas
pendientes y fuente congelada/vigente. No crea una reinscripción. Reutiliza el
endpoint existente con permiso y alcance de matrícula; no añade catálogos.
La reinscripción masiva se entrega separadamente en PR #638. Ambas partes de M4
requieren integración a `develop` y aceptación; no completan M2 ni el resto de
Matrículas. Evidencia y límites: [consulta de promoción](architecture/enrolment-promotion-ui.md).

| # | Prioridad · Tipo | Hallazgo |
|---|---|---|
| M1 | **P1 · Rendimiento** | **Por qué carga estudiantes:** [EnrolmentsPage.jsx](../frontend/src/enrolments/EnrolmentsPage.jsx) monta `useStudentCatalog`, `useSectionCatalog`, `useGradeCatalog` y `useCycleCatalog`. Cada uno descarga el catálogo completo **solo para traducir** `student_id`, `section_id`, etc. a nombres, porque [EnrolmentSerializer](../backend/apps/enrolments/api/serializers.py) responde únicamente UUIDs. *Corrección:* que el serializador incluya `student: {full_name, student_code}`, `section: {name, grade_name, shift_name}` y `academic_cycle: {name}`, y quitar esos catálogos de la página. |
| M2 | **P1 · Rendimiento** | [BulkEnrolmentWindow.jsx](../frontend/src/enrolments/BulkEnrolmentWindow.jsx) descarga todas las matrículas activas de todos los ciclos y filtra por ciclo en el navegador. Después matricula **una petición por estudiante**. El backend ofrece `/re-enrolments/bulk/` y filtros por ciclo. **Seguimiento #632:** reinscripción masiva en PR #638; [altas iniciales](architecture/bulk-initial-matriculation-ui.md) con candidatos paginados, preview acumulado y un POST por lote, resultados parciales y reintento sin duplicados. Integración y aceptación pendientes. |
| M3 | **P1 · Sin UI** | **Movimientos del estudiante:** cambio de sección (`/<id>/section-change/`), retiro (`/<id>/withdrawal/`), traslado de egreso (`/<id>/transfer-out/`), traslado de ingreso (`/transfers/in/`) y anulación de movimiento (`/movements/<id>/annulment/`). Hoy solo se puede *ver* el historial de movimientos. Seguimiento parcial: [cambio, retiro y anulación](architecture/enrolment-movements-ui.md); traslados pendientes. |
| M4 | **P1 · Sin UI** | **Promoción** (`/<id>/promotion/`) y **reinscripción masiva** (`/re-enrolments/bulk/`). |
| M5 | **P1 · Clics** | "Vigentes" solo filtra por estudiante (con un desplegable sin búsqueda de todo el padrón). Faltan filtros por ciclo, grado y sección, que es como trabaja secretaría. **Seguimiento #632:** filtros académicos de servidor, reinicio de página y secciones paginadas en [M5](architecture/enrolment-filters-ui.md); búsqueda remota de estudiante en PR #636. Integración/aceptación pendientes; base común de URL y `useServerList` en #630. |
| M6 | **P2 · Claridad** | Hay tres botones de alta en la cabecera ("Matricular", "Reinscribir", "Matricular por lotes") más "Movimientos". La diferencia entre matricular y reinscribir no se explica en la pantalla. Conviene un solo botón "Matricular" que detecte si el estudiante ya tuvo matrícula y elija el camino. **Seguimiento #632:** [alta unificada](architecture/unified-matriculation-ui.md): acceso Matricular, formulario individual con selección en servidor y entradas masivas agrupadas. Rutas anteriores conservadas; integración y aceptación pendientes. |
| M7 | **P2 · Claridad** | Al matricular no se ve el cupo disponible de la sección (ver S5). **Seguimiento #632:** [cupo contextual](architecture/enrolment-capacity-ui.md) en nueva matrícula, reinscripción individual y lote inicial; distingue sin límite, lleno y error, y actualiza al terminar envíos. Conserva la validación de servidor. Integración y aceptación pendientes. |

Seguimiento del bloque de matrículas #632: la interfaz de reinscripción masiva,
los candidatos paginados y el alcance parcial de M2/M4/M5 están documentados en
[Reinscripción por lotes](architecture/bulk-reenrolment-ui.md). La operación
masiva de altas iniciales y promoción siguen pendientes; no se consideran
intercambiables los contratos de matriculación inicial y reinscripción.

### 2.11 Evaluación

| # | Prioridad · Tipo | Hallazgo |
|---|---|---|
| V1 | **P0 · Sin UI** | **Cerrar unidad de evaluación** (`/evaluation-units/<id>/close/`). Sin esto no se puede cerrar el ciclo (ver C4). |
| V2 | **P0 · Clics** | **La captura de notas es de una en una.** [GradesWindow.jsx](../frontend/src/evaluation/GradesWindow.jsx) abre un formulario por nota: estudiante (desplegable con todas las matrículas del sistema), subárea, docente y valor. Una sección de 30 estudiantes con 10 subáreas y 4 unidades son 1 200 formularios. Hace falta una **planilla de calificaciones** (sección + subárea → tabla de estudiantes con una celda por nota, guardado por lotes), apoyada en `/grades/bulk/`, que el backend ya tiene sin usar. |
| V3 | **P1 · Sin UI** | **Avance de captura** por unidad (`/capture-progress/`): cuánto falta por calificar. |
| V4 | **P1 · Sin UI** | **Recuperación:** elegibilidad (`/recovery-eligibility/`) y registro de notas de recuperación (`/recovery-grades/`). |
| V5 | **P1 · Sin UI** | **Resultados congelados** al cerrar el ciclo: consulta (`/frozen-result/`), corrección (`/frozen-result/correct/`) y condición de promoción (`/frozen-promotion/`). También la boleta del estudiante (`/enrolments/<id>/grades/`) y la trazabilidad del resultado (`/audit/.../result-trace/`). |
| V6 | **P1 · Sin UI** | **Clonar configuración de evaluación** de un ciclo a otro (`/evaluation-config/clone/`). |
| V7 | **P1 · Rendimiento** | `useEnrolmentCatalog` descarga en paralelo **todas las matrículas activas, todos los estudiantes y todas las secciones** para armar las etiquetas del desplegable ([academicCatalogs.js:269-290](../frontend/src/shared/catalogs/academicCatalogs.js#L269-L290)). |
| V8 | **P2 · Claridad** | En el formulario de nota hay que elegir al docente a mano; debería salir de la asignación docente vigente de esa sección y subárea. |

### 2.12 Asistencia

| # | Prioridad · Tipo | Hallazgo |
|---|---|---|
| AS1 | **P1 · Sin UI** | **Turno de captura:** abrir (`/capture-batches/`), consultar el vigente (`/capture-batches/current/`) y confirmar (`/capture-batches/<id>/confirm/`). Recién se agregó la ventana operativa del escaneo (commit `cba7db8`), pero la interfaz no muestra el turno ni su vencimiento. |
| AS2 | **P1 · Sin UI** | **Credenciales del estudiante:** emitir, imprimir (`/credentials/print-content/`), revocar y resolver. Sin esto no hay forma de generar el carné QR que se escanea. |
| AS3 | **P1 · Sin UI** | **Justificaciones:** enviar, resolver, adjunto, motivos y notificaciones (`/justifications/…`). |
| AS4 | **P1 · Sin UI** | **Permisos de salida** (`/permits/` y `/permits/<id>/resolve/`). |
| AS5 | **P1 · Sin UI** | **Notificaciones de ausencia** (`/absence-notifications/`), **motivos de registro manual** (`/manual-registration-reasons/`) y **razón de cobertura de cierre** (`/section-closures/coverage-ratio/`). |
| AS6 | **P2 · Clics** | La página principal mezcla movimientos, alertas, parámetros, cámara, escaneo, presencia, cierre y dos "sondas" de consulta (estado del día y porcentaje) como ventanas sueltas. Conviene separarla en pestañas: *Hoy* (escaneo y presencia) / *Movimientos* / *Cierres* / *Justificaciones y permisos* / *Configuración*. |

### 2.13 Plantillas documentales (formatos imprimibles)

Es el módulo más difícil de entender hoy. Quien arma una plantilla no ve el documento que está armando.

| # | Prioridad · Tipo | Hallazgo |
|---|---|---|
| PL1 | **P0 · Claridad** | **Regla invisible del código de tipo.** La constancia de inscripción solo usa la plantilla si existe un tipo de documento con código exacto **`constancia`**, y el certificado de estudios solo si el tipo es **`certificate`** ([services.py, `INDIVIDUAL_TEMPLATE_KIND`](../backend/apps/documents/services.py)). El catálogo inicial trae `certificate`, `report` y `other`, **pero no `constancia`**. Si el tipo no existe o se llama distinto, el sistema emite un texto por defecto y no avisa. La interfaz debe decir para qué emisión sirve cada tipo, o asociar la plantilla a la emisión de forma explícita. **Resuelto por D7:** cada plantilla declara explícitamente para qué emisión se usa. |
| PL2 | **P0 · Claridad** | **Solo puede haber una plantilla activa por tipo** (restricción `unique_active_document_template_per_kind_per_institution`). El formulario ofrece todos los tipos y el error llega al guardar. Hay que marcar en el selector los tipos que ya tienen plantilla activa y ofrecer "reemplazar la actual". Con D7, la regla pasa a ser *una plantilla activa por uso de emisión*, y el selector debe mostrar qué uso ya tiene plantilla. |
| PL3 | **Implementado · #666** | El editor integra el catálogo general/sensible, inserción en el bloque activo y validación en vivo de etiquetas desconocidas. |
| PL4 | **Implementado · #666** | El formulario genera una vista previa PDF real con debounce, incluso antes de guardar una plantilla nueva. |
| PL5 | **P1 · Bug** | **La vista previa rellena solo 3 de 8 etiquetas.** [TemplatePreviewWindow.jsx](../frontend/src/documents/TemplatePreviewWindow.jsx) envía nombre del estudiante, nombre de la institución y nombre corto. Código, ciclo, sección, fecha de inscripción y fecha de emisión salen **vacíos**, y parece que la plantilla está mal. |
| PL6 | **P1 · Claridad** | **D4.1 implementada:** la vista previa muestra el PDF real generado en el servidor con encabezado, página y datos de muestra. La selección de un estudiante real continúa fuera del alcance actual. |
| PL7 | **Implementado · #666** | El formulario explica que el encabezado y logo se derivan de la configuración institucional. |
| PL8 | **Implementado · #666** | El historial permite seleccionar dos versiones, compararlas y restaurar una como una versión nueva auditable. |
| PL9 | **Implementado · #666** | “Emisión documental” reúne emisión individual, lotes idempotentes, histórico, entrega, integridad y verificación pública por código. |
| PL10 | **Implementado · #666** | D4.2 expone bloques, énfasis, alineación, papel, orientación, márgenes, pie y hasta dos firmas. |
| PL11 | **Implementado · #666** | Al crear, el código se sugiere desde el nombre y permanece editable hasta guardar. |

#### 2.13.1 Plantillas con formato (decisión D4)

Lo que hace falta en cada capa:

| Capa | Hoy | Propuesta |
|---|---|---|
| **Contenido guardado** | Texto plano en `DocumentTemplate.content` y en cada `DocumentTemplateVersion`. | Contenido estructurado: JSON de un editor de texto enriquecido (por ejemplo, el formato de documento de TipTap o ProseMirror) o HTML saneado con lista blanca. El JSON es más seguro: no hay HTML que sanear y las etiquetas `{{…}}` pueden ser nodos propios que no se rompen al editar. Se agrega `content_format` (`plain` / `rich`) para que las versiones ya emitidas en texto plano se sigan leyendo igual (AGENTS.md, regla 12). |
| **Configuración de página** | No existe. | Campos por plantilla: tamaño (Carta / Oficio / A4), orientación, márgenes, mostrar encabezado institucional (siempre activo, por RF-PLA-004, pero con posición y tamaño de logo), pie de página y bloque de firmas (nombre y cargo de quien firma, uno o dos). |
| **Generación del PDF** | `_text_lines_stream` y `_assemble_pdf` escriben líneas de texto de 90 caracteres con una sola fuente. | Un motor que respete el formato: convertir el contenido a HTML y renderizarlo con WeasyPrint, o dibujarlo con ReportLab. Debe ser el **mismo motor** para la vista previa y para la emisión, para que lo que se ve sea lo que se imprime. La elección de librería es técnica y conviene documentarla como ADR. |
| **Editor (frontend)** | `<textarea>`. | Editor enriquecido con barra mínima: negrita, cursiva, subrayado, títulos, alineación, listas, tabla simple, salto de página. Panel de etiquetas a un clic (las etiquetas se insertan como "chips" no editables). Vista previa del PDF real al lado, con datos de muestra completos o con un estudiante elegido. |

**Alcance mínimo viable:** negrita, cursiva, alineación, títulos, tamaño de papel, márgenes, firma y vista previa real. Tablas y saltos de página pueden venir después.

**Propuesta de pantalla:** listado de plantillas con el tipo y "se usa para: Constancia de inscripción". Al abrir una, editor a pantalla completa con tres zonas: etiquetas (izquierda, clic para insertar) · contenido (centro) · vista previa del PDF con un estudiante de muestra o real (derecha). Botones "Guardar como versión nueva" e "Historial / restaurar".

### 2.14 Tipos de documento

| # | Prioridad · Tipo | Hallazgo |
|---|---|---|
| TD1 | **P1 · Claridad** | No se explica que ciertos códigos (`constancia`, `certificate`) tienen significado para la emisión (ver PL1). Hay que mostrarlo como un chip "Usado por: Constancia de inscripción" y avisar antes de desactivar uno de ellos. Con D7, los tipos de documento dejan de tener significado para la emisión, y este hallazgo se reduce a explicar que el tipo es solo una clasificación. |
| TD2 | **P2 · Claridad** | No muestra cuántas plantillas usan cada tipo. |

### 2.15 Documentos del expediente (archivos)

| # | Prioridad · Tipo | Hallazgo |
|---|---|---|
| DO1 | **P1 · Sin UI** | **Reemplazar archivo / nueva versión** (`/records/<id>/versions/`), **verificar integridad** (`/records/<id>/verify/`) y **subir documento escaneado** (`/records/scan/`): existen en `documentsService`, pero ninguna pantalla los usa. |
| DO2 | **P1 · Sin UI** | **Consumo de almacenamiento** (`/storage-consumption/`) para administración. |
| DO3 | **P2 · Clics** | Los documentos del estudiante solo se alcanzan desde Matrículas → fila → "Requisitos documentales". Deberían estar también en el expediente del estudiante (ver 1.5). |

### 2.16 Alertas y umbrales

| # | Prioridad · Tipo | Hallazgo |
|---|---|---|
| R1 | **P2 · Claridad** | Las alertas de asistencia (Asistencia) y las de reporte (Alertas) son dos listados distintos con nombres parecidos. Conviene unificarlas o explicar la diferencia. |
| R2 | **P2 · Clics** | Desde una alerta no se puede ir al estudiante afectado. |

### 2.17 Usuarios, roles y acceso

Es el módulo con más huecos. Hoy, desde la interfaz, **no se puede dar acceso al sistema a nadie**: no hay alta de cuenta, ni página para activarla, ni gestión de roles. La única pantalla, "Cuentas", lista cuentas y permite restablecer acceso, cerrar sesiones y desactivar.

Modelo del backend, para entender las propuestas: una **cuenta** (`UserAccount`) siempre está ligada a una **persona**. Tiene estado (`pending` → `active`, o `blocked` / `disabled`) y uno o más **roles** asignados con vigencia (`RoleAssignment`). Cada asignación lleva uno o más **alcances** (`ScopeGrant`): institución, ciclo, grado, sección, curso, asignación docente, estudiante o módulo. Un rol agrupa **permisos atómicos** (38, en [atomic_permissions.py](../backend/apps/identity/atomic_permissions.py)) y define su tiempo de inactividad de sesión.

#### 2.17.1 Inicio de sesión y sesión

| # | Prioridad · Tipo | Hallazgo |
|---|---|---|
| L1 | **P0 · Sin UI** | **No hay página de activación de cuenta.** `POST /identity/accounts/activate/` (público: usuario + código de activación + contraseña nueva) no tiene pantalla. Aunque se creara una cuenta, quedaría en `pending` para siempre. Hace falta una ruta pública `/activar` enlazada desde el login. |
| L2 | **P0 · Sin UI** | **No hay página para usar un restablecimiento de contraseña.** Administración puede emitirlo, pero `POST /identity/password-resets/consume/` (público: token + contraseña nueva) no tiene pantalla. Hace falta una ruta pública `/restablecer?token=…`. |
| L3 | **P1 · Claridad** | **El login no ofrece "¿Olvidó su contraseña?".** Como el restablecimiento lo emite administración (no hay autoservicio por correo), el enlace debe explicar eso: "Pida a administración un enlace de restablecimiento". Así la persona no queda adivinando. |
| L4 | **P1 · Bug / Claridad** | **La sesión vence sin avisar.** El backend cierra la sesión tras N minutos de inactividad (el mayor de los roles del usuario; [middleware.py](../backend/apps/identity/middleware.py)). Cuando pasa, el frontend solo hace `setUser(null)` ([AuthProvider.jsx](../frontend/src/auth/AuthProvider.jsx)): la persona cae en el login sin mensaje y pierde el formulario que estaba llenando. Propuesta: aviso 2 minutos antes ("Su sesión se cerrará por inactividad · Seguir conectado"), mensaje en el login ("Su sesión se cerró por inactividad") y volver a la misma página al entrar. Esto último ya funciona con `state.from`. |
| L5 | **P1 · Claridad** | **Bloqueo por intentos fallidos.** Tras `LOGIN_MAX_FAILED_ATTEMPTS` (5) intentos, la cuenta queda bloqueada `LOGIN_LOCKOUT_MINUTES`. Hay que verificar que el login diga claramente que la cuenta está bloqueada temporalmente y hasta cuándo, y no solo "credenciales inválidas". |
| L6 | **P2 · Claridad** | El campo dice "Contrasena" (sin tilde) y no tiene botón para mostrar u ocultar la contraseña. |

#### 2.17.2 Mi cuenta (cualquier usuario)

| # | Prioridad · Tipo | Hallazgo |
|---|---|---|
| MC1 | **P1 · Sin UI** | **No hay página "Mi cuenta".** El menú de usuario ([UserMenu.jsx](../frontend/src/shared/layout/UserMenu.jsx)) solo ofrece cambiar contraseña, cerrar sesiones y salir. Propuesta de página `/app/mi-cuenta` con: datos de la persona, **mis roles y alcances** ("Docente · Sección 1.º Básico A · Matemática"), mi horario semanal (`/identity/me/schedule/`, ver S4) y mis sesiones. |
| MC2 | **P1 · Claridad** | **Las reglas de contraseña no son las reales.** La ventana de cambio dice "Debe contener al menos 8 caracteres", pero el backend aplica todos los validadores de Django (contraseña común, solo números, parecida al usuario). Hay que listar todas las reglas y mostrar el error de cada una junto al campo. El mensaje genérico "Ocurrió un error… Verifique los datos" no ayuda. Aplica también a la activación (L1) y al restablecimiento (L2). |
| MC3 | **P2 · Claridad** | El panel muestra el estado de la cuenta en crudo (`active`). Debe traducirse ("Activa"). |

#### 2.17.3 Administración de cuentas

| # | Prioridad · Tipo | Hallazgo |
|---|---|---|
| U1 | **P0 · Sin UI + contrato** | **Crear cuenta.** `POST /identity/accounts/` existe, pero (a) no hay pantalla y (b) **pide el `id` interno (entero) de la persona** (`PrimaryKeyRelatedField`), mientras `/people/` solo expone `public_id`. Ningún cliente puede obtener ese id: hay que cambiar el contrato a `person_public_id` (y documentarlo, AGENTS.md regla 3). Flujo propuesto: botón **"Dar acceso al sistema"** en la ficha del docente (y en Personas) → usuario sugerido (por ejemplo `nombre.apellido`) → al crearla se muestra **una sola vez** el código de activación y su vencimiento, con botones Copiar e Imprimir instrucciones. Con D10, el mismo flujo de "Dar acceso" debe buscar primero la persona por CUI o nombre. |
| U2 | **P1 · Sin UI** | **Reemitir código de activación** (`/accounts/<id>/activation-challenges/`) para cuentas pendientes cuyo código venció. |
| U3 | **P1 · Claridad** | **El restablecimiento de contraseña muestra un token crudo.** "Restablecer acceso" abre un diálogo con el `token` ([AccountsPage.jsx](../frontend/src/auth/AccountsPage.jsx)), que nadie sabe qué hacer con él. Debe mostrar el **enlace completo** a `/restablecer?token=…` (L2), cuándo vence, y botones Copiar e Imprimir. |
| U4 | **P1 · Claridad** | **El listado de cuentas no tiene filtros.** El backend ya acepta `?status=` y `?search=` (usuario, nombre, apellido), pero la pantalla no muestra buscador ni filtro por estado, aunque el comentario del componente dice que sí. Además faltan columnas: correo, **roles**, último acceso (`last_login`) y si está bloqueada temporalmente (`locked_until`). |
| U5 | **P1 · Sin UI + backend** | **No hay ficha de la cuenta.** Hace falta una vista de detalle con: persona vinculada (enlace a su expediente), estado, roles con alcances y vigencias, sesiones activas e historial de accesos (desde auditoría). El backend no tiene `GET /identity/accounts/<id>/` ni un listado de asignaciones por cuenta: hay que agregarlos. |
| U6 | **P1 · Sin UI + backend** | **Reactivar una cuenta desactivada / desbloquear.** No existe ni en backend ni en interfaz. Una cuenta desactivada por error no tiene vuelta atrás, y el bloqueo temporal solo se levanta esperando. Regla decidida en D8. |
| U7 | **P2 · Sin UI + backend** | **Editar la cuenta** (correo, nombre de usuario): no hay endpoint. |
| U8 | **P2 · Claridad** | Los nombres de estado vienen en inglés desde el backend ("Pending", "Active", "Blocked", "Disabled"). El frontend los traduce, pero cualquier otro cliente o mensaje los mostraría en inglés. |
| U9 | **P2 · Clics** | Cada fila tiene tres botones de texto ("Restablecer acceso", "Cerrar sesiones", "Desactivar"). Con muchas filas la tabla se satura: conviene un menú "⋯" de acciones, o moverlas a la ficha (U5). |

#### 2.17.4 Roles y permisos

| # | Prioridad · Tipo | Hallazgo |
|---|---|---|
| RO1 | **P0 · Sin UI** | **No hay pantalla de roles.** El backend permite listar, crear y editar roles (`/identity/roles/`, `/identity/roles/<id>/`) con nombre, descripción, permisos y tiempo de inactividad de sesión. Propuesta: listado de roles con cantidad de cuentas que lo tienen; editor con los permisos **agrupados por módulo** (Cuentas, Estudiantes, Matrícula, Asistencia, Evaluación, Documentos, Alertas, Auditoría, Plataforma) y casillas por grupo. |
| RO2 | **P1 · Claridad** | **Los permisos están en inglés** ("Can view student basic data", "Can write grades"…). Hay que traducir las 38 etiquetas a español y agregar una línea de descripción ("Permite ver nombre, código y foto del estudiante; no incluye salud ni observaciones"). |
| RO3 | **P1 · Claridad** | El `slug` del rol se escribe a mano; debe derivarse del nombre. Los roles de sistema (`is_system`) deben verse marcados y protegidos, con el motivo. |
| RO4 | **P1 · Claridad** | El tiempo de inactividad por rol existe, pero no se explica que **gana el mayor** de los roles del usuario. Hay que decirlo junto al campo. |
| RO5 | **P2 · Sin UI** | No hay forma de **comparar roles** ni de ver "quién tiene este permiso". Es útil para auditorías de acceso. |
| RO6 | **P2 · Sin UI** | No se pueden desactivar ni eliminar roles (no hay endpoint). Un rol que ya no se usa queda para siempre en el catálogo. |

#### 2.17.5 Asignación de roles y alcances

| # | Prioridad · Tipo | Hallazgo |
|---|---|---|
| RA1 | **P0 · Sin UI + contrato** | **Asignar un rol con alcance.** `POST /identity/accounts/<id>/role-assignments/` existe, pero (a) no hay pantalla y (b) los alcances (`ScopeGrantWriteSerializer`) **piden ids internos** de institución, ciclo, grado, sección, curso, asignación docente y estudiante, mientras todas las APIs académicas solo exponen `public_id`. Hay que cambiar el contrato a `public_id` y documentarlo. |
| RA2 | **P0 · Sin UI** | **Revocar una asignación** (`DELETE /identity/role-assignments/<id>/`). |
| RA3 | **P1 · Clics** | Propuesta de asistente en 3 pasos desde la ficha de la cuenta: **1. Rol** (con su descripción) → **2. Alcance** (selector del tipo de alcance y luego selectores con búsqueda de ciclo, grado, sección, curso o estudiante, según el tipo) → **3. Vigencia** (desde y hasta, por defecto el rango del ciclo). Al final, un resumen en lenguaje natural: "Ana López podrá *registrar notas* en *Matemática · 1.º Básico A · Ciclo 2027* hasta el *31/10/2027*". |
| RA4 | **P1 · Clics** | **Alcance del docente automático.** Hoy, si los permisos de un docente dependen de sus asignaciones, habría que crear un alcance por sección y curso a mano. Conviene que asignar el rol "Docente" ofrezca "Usar sus asignaciones docentes vigentes" como alcance (el modelo ya tiene `teaching_assignment`), o que se cree al registrar la asignación. |
| RA5 | **P2 · Claridad** | Mostrar las asignaciones por vencer (próximos 15 días) y las vencidas, para que nadie pierda acceso sin aviso al cambiar de ciclo. |

#### 2.17.6 Organización del menú

- **P2 · Claridad —** Hoy "Seguridad" tiene solo "Cuentas", y "Personas" y "Tipos de documento" están mezclados con la operación diaria. Propuesta de grupo **Administración**: Cuentas · Roles · Personas · Tipos de documento · Auditoría · Plataforma. Solo lo ve quien tiene esos permisos (ver 1.4).
- **P2 · Decisión —** El backend contempla cuentas de encargado (`account_kind = "guardian"`), pero no hay portal para padres de familia. Decidido en D9: queda fuera del alcance actual y la interfaz no ofrece ese tipo de cuenta.

### 2.18 Auditoría y plataforma (no existen en la interfaz)

| # | Prioridad · Tipo | Hallazgo |
|---|---|---|
| AU1 | **P1 · Sin UI** | **Bitácora de auditoría** (`/audit/events/`) y su exportación (`/audit/events/export/`). |
| AU2 | **P1 · Sin UI** | **Declaraciones de retención de datos** (`/audit/retention-declarations/`). |
| AU3 | **P2 · Sin UI** | **Salud de la plataforma:** tareas programadas (`/platform/task-runs/`, `/platform/task-health/`) y respaldos (`/platform/backup-health/`). El panel solo muestra `/health/`. |

---

## 3. Decisiones de negocio

Todas las reglas que el código no cerraba quedan decididas aquí. D1–D5 las definió el responsable del proyecto. D6–D10 se tomaron con el criterio de mínima sorpresa para la persona usuaria, menor riesgo para la integridad académica y consistencia con el alcance vigente ([functional-scope.md](requirements/functional-scope.md)).

Como cambian reglas del dominio, cada una debe registrarse como ADR en [docs/decisions](decisions/) ([ADR-0011](decisions/ADR-0011-decisiones-ux-ui.md) las consolida; cada responsable agrega su aporte en un archivo `ADR-0011-*.md`). Las que tocan un requerimiento deben actualizar también el [catálogo de requerimientos](requirements/requirements-catalogue.md) y la [matriz de trazabilidad](requirements/traceability-matrix.md) (AGENTS.md, reglas 3 y 10).

| # | Decisión | Qué cambia | Hallazgos |
|---|---|---|---|
| **D1** | Para activar un ciclo **hay que cerrar antes el ciclo activo**. | Nada en backend (ya es así). En la interfaz: corregir textos y deshabilitar "Activar", con explicación, mientras haya otro ciclo activo. | C5 |
| **D2** | **Se puede clonar un ciclo activo** para preparar el siguiente. | Backend: `clone_academic_cycle` acepta ciclos `ACTIVE` y `CLOSED`. Actualizar RF-CIC-007 y sus pruebas. | C2 |
| **D3** | **Existe "volver a borrador"** para un ciclo activado por error. | Nuevo servicio y endpoint auditados, con motivo obligatorio, y botón en la interfaz. Condiciones en D6. | C10 |
| **D4** | **Las plantillas llevan formato.** | Contenido estructurado, configuración de página, motor de PDF con formato y editor enriquecido con vista previa real. | PL3–PL6, PL10, 2.13.1 |
| **D5** | **El estado del expediente del estudiante se edita a mano.** | Se mantiene el campo, pero con una acción propia, confirmación, avisos de inconsistencia con la matrícula y trazabilidad visible. | E9 |
| **D6** | **Volver a borrador solo antes de que el ciclo tenga actividad.** Se permite únicamente si el ciclo **no** tiene matrículas, notas, movimientos de asistencia, unidades de evaluación cerradas ni documentos emitidos. Exige motivo y el permiso nuevo `academic_cycle.revert`. Se conservan la estructura (ofertas, secciones, plan) y las asignaciones docentes. | Si el ciclo ya tiene actividad, la vía es cerrarlo y, si hace falta, reabrirlo (RF-CIC-005). El botón aparece deshabilitado y lista qué lo impide ("Tiene 312 matrículas"). | C10 |
| **D7** | **Cada plantilla declara para qué emisión se usa.** Campo explícito "Se usa para": *Constancia de inscripción*, *Certificado de estudios* o *Ninguna*, con **una sola plantilla activa por uso**. El tipo de documento queda solo como clasificación. | Migración: las plantillas activas con tipo `constancia` o `certificate` pasan al uso correspondiente. La emisión deja de buscar por código de tipo. Si un uso no tiene plantilla, la pantalla de Plantillas lo avisa ("La constancia de inscripción usa el texto por defecto"). | PL1, PL2, TD1 |
| **D8** | **Se pueden reactivar cuentas desactivadas y desbloquear cuentas bloqueadas.** Reactivar devuelve la cuenta a `pending` con un **código de activación nuevo**: la persona define otra contraseña y los roles revocados **no** vuelven solos. Desbloquear levanta el bloqueo temporal y reinicia los intentos fallidos. Ambas acciones requieren el permiso `account.activate` y un motivo, y quedan auditadas. | Dos endpoints nuevos (`/accounts/<id>/reactivate/` y `/accounts/<id>/unlock/`) y sus acciones en la ficha de la cuenta. | U6 |
| **D9** | **El portal para padres de familia queda fuera del alcance actual.** No figura en el catálogo de requerimientos, y la granularidad de acceso de encargados sigue abierta como [PD-004](decisions/pending-decisions.md). | Se conserva `account_kind = "guardian"` en el backend, pero la interfaz no ofrece crear cuentas de encargado hasta que exista ese requerimiento. | 2.17.6 |
| **D10** | **Personas es un registro mínimo que se completa al convertirla.** Personas sigue pidiendo solo nombre y contacto, y ofrece "Convertir en estudiante / docente / encargado", que pide los datos faltantes (CUI, fecha de nacimiento, dirección…) y **reutiliza la misma persona** en lugar de crear otra. Antes de crear un estudiante, docente o encargado se busca por CUI y nombre para evitar duplicados. | Backend: alta de estudiante, docente y encargado a partir de `person_public_id`, además del alta con persona anidada. | PE2, U1 |

---

## 4. Orden sugerido de trabajo

**Fase 0 — Registrar las decisiones**

1. Escribir el ADR con D1–D10 (`ADR-0011`).
2. Actualizar RF-CIC-005 y RF-CIC-007, y dar de alta los requerimientos nuevos (volver a borrador, uso de emisión de plantillas, reactivar y desbloquear cuentas, conversión de persona) en el catálogo y la matriz de trazabilidad.
3. Agregar los permisos nuevos (`academic_cycle.revert`) al catálogo de permisos atómicos.

**Fase 1 — Correcciones rápidas de alto impacto**

1. `cache_seconds = 0` en sedes, jornadas, niveles, cursos y secciones (1.2.1).
2. Enviar todos los campos de persona al editar estudiantes, docentes y encargados (1.2.2).
3. Invalidar la caché de react-query después de cada escritura (1.2.3).
4. Ciclos: corregir el texto de "Activar" y deshabilitarlo si hay otro activo (C5, D1); permitir clonar ciclos activos en backend y deshabilitar "Clonar" en borradores (C2, D2).
5. Filtrar las relaciones de encargados por estudiante en el servidor (1.1.4).
6. Plantillas: campo "Se usa para" con su migración (PL1, D7) y vista previa con todas las etiquetas rellenadas (PL5).
7. Usuarios: traducir permisos y estados (RO2, U8, MC3); mostrar el enlace completo de restablecimiento (U3); agregar buscador y filtro de estado en Cuentas (U4).

**Fase 2 — Convención de paginación (sección 1.1)**

1. `StandardPagination` + `page_size` + `search` + `include_inactive` en el backend.
2. Nombres incluidos en serializadores (matrículas, aulas, notas, asignaciones).
3. `useServerList` único en el frontend + selector de filas funcionando + estado en la URL.
4. Migrar Estudiantes, Docentes, Padres y Matrículas; eliminar `useLocalList`. *(Estudiantes, Docentes y Padres migrados y `useLocalList` eliminado en #631; queda Matrículas.)*
5. Selectores con búsqueda en el servidor dentro de `EntityFormWindow`.

**Fase 3 — Dar acceso al sistema (usuarios)**

1. Contratos con `public_id` en alta de cuenta y en alcances (U1, RA1); alta de estudiante, docente y encargado desde una persona existente (D10).
2. Páginas públicas de activación y restablecimiento (L1, L2, L3).
3. Alta de cuenta desde la ficha del docente o de la persona, con código de activación (U1, U2).
4. Pantalla de roles con permisos agrupados (RO1, RO3, RO4).
5. Ficha de cuenta y asistente de asignación de rol con alcance (U5, RA2, RA3, RA4); reactivar y desbloquear (U6, D8).
6. Aviso de sesión por vencer y mensaje de sesión expirada (L4); "Mi cuenta" (MC1, MC2).
7. Permisos efectivos en `/auth/me/` y menú filtrado por permisos (1.4).

**Fase 4 — Desbloquear el ciclo de vida del ciclo escolar**

1. Pantallas de Secciones y Plan de estudios del ciclo (S1, S2).
2. Editar ciclo en borrador (C3), reabrir (C6), volver a borrador (C10, D6) y lista de verificación de activación (C7).
3. Cerrar unidad de evaluación (V1).
4. Matriz sección × curso de asignaciones (AD3).

**Fase 5 — Flujos operativos sin interfaz**

1. Planilla de calificaciones con guardado por lotes (V2) y recuperación (V4).
2. Movimientos de matrícula (M3, M4).
3. Credenciales, turnos de captura, justificaciones y permisos de asistencia (AS1–AS4).
4. Plantillas con formato: contenido estructurado, motor de PDF, editor y vista previa real (2.13.1, PL3, PL4, PL6, PL10).
5. Pantalla "Emitir documentos" (PL9).

**Fase 6 — Pulido**

Expediente con pestañas (1.5), cambio de estado del expediente (E9), menú de Administración (2.17.6), auditoría y plataforma (2.18), textos y fechas (1.6) y el resto de los P2.

## Seguimiento de implementación de M3 — issue #632

La entrega de [cambio, retiro y anulación (#639)](https://github.com/siga-inebi/siga-inebi/pull/639)
y la de [traslados de ingreso y egreso](architecture/student-transfers-ui.md)
cubren en código las cinco operaciones de M3 con captura, revisión e historial.
La documentación de traslados contiene la tabla de cobertura y sus pruebas.
Integración en `develop` y aceptación institucional pendientes; M4 y el resto
del epic mantienen su alcance.
