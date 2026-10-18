# Filtros de matrículas vigentes — M5

Entrega del issue #632, hallazgo M5 de `docs/ux-ui.md`, sobre RF-MAT-007.
Rama creada desde `develop`; revisión e integración pendientes. No cierra la épica.

## Experiencia y consultas

- Vigentes permite combinar estudiante, ciclo escolar, grado y sección. Los
  filtros se envían al servidor; no se filtra la página descargada en React.
- Ciclo y grado usan los catálogos académicos pequeños existentes, compartidos
  mediante caché. El grado puede consultarse sin ciclo; una combinación sin
  matrículas devuelve una lista vacía, sin ignorar el filtro.
- El selector nuevo de sección exige ciclo y consulta solo una página de
  `/academics/sections/`, acotada por `academic_cycle_id` y, si corresponde,
  `grade_id`. Anterior/Siguiente permiten recorrer las demás páginas. La selección
  mantiene su etiqueta al explorar otra página. La búsqueda del selector se
  limita a las opciones de su página y se avisa que hay más páginas.
- Cambiar ciclo limpia grado y sección; cambiar grado limpia sección. Cada cambio
  de filtro reinicia la página de matrículas a 1 en el mismo evento. Limpiar en
  Vigentes restablece estudiante y filtros académicos.
- El historial sigue consultándose completo por estudiante, con sus estados y
  registros inactivos: allí no se muestran ni envían los filtros académicos.
  Al volver a Vigentes se conservan las selecciones académicas. Limpiar desde
  Historial quita el estudiante, sin alterar esos filtros guardados en memoria.
- Los errores de catálogos y listados se muestran; la selección se conserva.
  Secciones permite reintento explícito y descarta respuestas tardías de un
  ciclo/grado anterior. Se distingue catálogo vacío de error.
- La barra permite envolver controles para pantallas estrechas. No añade cambios
  de matrícula, cupos, estados, resultados académicos ni movimientos.

## Contratos y límites

`GET /api/v1/enrolments/active/` admite los UUID opcionales `academic_cycle_id`,
`grade_id` y `section_id`, además de `student_id`. Se combinan por intersección
antes de contar y paginar. UUID mal formado: 400; UUID académico válido sin
coincidencias o filtros contradictorios: 200 con `count=0`. Sin filtros conserva
el comportamiento previo. Ruta y respuesta JSON no cambian.

La implementación de esos tres parámetros es idéntica a la preparada en el
PR #638: se incluye aquí para poder probar M5 desde `develop` sin depender de
fusionar aquel PR. No hay dos contratos ni filtros alternativos. La consulta ORM
permanece en el servicio del dominio; vistas y componentes no deciden vigencias.
No cambian autorización, alcance ni campos publicados del listado existente.

La búsqueda remota de estudiantes y la eliminación de catálogos para traducir
UUID se entregan en el PR #636 (M1). La rama independiente de M5 conserva el
listado y formulario existentes; esta entrega no afirma haber eliminado esas
descargas del código base. Los catálogos de ciclo/grado del selector sí se usan
para decisiones de filtro, no para traducir filas.

La migración a `useServerList`, tamaño de página configurable, estado en URL y
política común de caché depende del issue #630. Ese hook todavía no existe en
`develop`: se reutiliza `usePaginatedList` sin crear una segunda infraestructura
compartida. Recargar la página no conserva los filtros de esta entrega.

ADR aplicables: ADR-0004 (REST), ADR-0005 (autorización), ADR-0006 (historia) y
ADR-0008 (capas). No se añaden migraciones, permisos, dependencias ni variables.

## Evidencia

- `backend/tests/api/test_enrolment_filters_api.py`: filtros individuales y
  combinados antes de paginar, más de 25 registros, exclusión de registros
  retirados/inactivos, contradicciones, UUID inválidos/desconocidos y sesión.
- `frontend/src/test/EnrolmentAcademicFilters.test.jsx`: dependencias de filtros,
  páginas a pedido, selección persistente, reintento y respuesta tardía.
- `frontend/src/test/newModulePages.test.jsx`: petición filtrada, reinicio de
  página, limpiar, independencia del historial y errores sin perder selección.
- `frontend/src/test/moduleServices.test.js`: contrato de query string.

La aceptación visual institucional y la integración de los PR se registran por
separado de las pruebas automatizadas.
