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

Validación local del 17 de octubre de 2026: suite completa de backend sobre
PostgreSQL, **1784 aprobadas / 23 omitidas**, cobertura **95.15%**. Frontend:
**317 aprobadas en 37 archivos**, cobertura de líneas **85.28%**. Las 49 pruebas
de herramientas de requerimientos también pasan; Ruff, ESLint, compilación y
presupuesto de assets, comprobación Django y ausencia de migraciones pendientes
verificados. No se afirma aceptación visual por esas pruebas.

## Integración con las entregas anteriores

Los PR siguen independientes hacia `develop`. Se verificaron combinaciones
locales en checkouts separados, sin fusionar ramas públicas:

- Con #636: **69 pruebas de frontend y 8 de API aprobadas**, más ESLint,
  compilación y presupuesto. Hay cambios concurrentes en `EnrolmentsPage.jsx`:
  al integrar se conserva `EnrolmentStudentFilter` con valor `{value,label}`,
  nombres anidados y carga exclusiva de la pestaña activa; se agregan los
  filtros académicos, su estado, los parámetros y el reinicio de página de M5.
  Limpiar usa `changeStudentFilter(null)` en esa combinación. No debe restaurarse
  el catálogo completo de estudiantes ni quitarse la barra académica al resolver.
- Con #638: **17 pruebas de API aprobadas** (M5 y candidatos de reinscripción).
  Los campos de `ActiveEnrolmentQuerySerializer` son idénticos; Git puede marcar
  conflicto al coincidir su inserción con las clases nuevas de candidatos. Se
  conservan los tres campos una sola vez y las clases de candidatos de #638.
  No cambia ningún contrato de reinscripción.
- Con #639, #640 y #641: combinaciones Git sin conflictos de contenido. Esto no
  sustituye las pruebas posteriores a la integración completa.

La vista local de revisión conjunta con #636 usa una base PostgreSQL aislada y
datos sintéticos. Se comprobaron por HTTP login/CSRF, combinación de filtros,
nombres anidados, catálogo de secciones acotado, UUID inválido (400), ausencia de
coincidencias y acceso al historial. La revisión visual institucional permanece
pendiente.
