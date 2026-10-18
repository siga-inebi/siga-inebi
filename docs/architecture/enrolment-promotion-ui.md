# Consulta de promoción desde Matrículas

Entrega de M4 del issue #632, basada en `docs/ux-ui.md`, RF-MOV-006 y RF-RES-006.
Complementa la reinscripción masiva del PR #638. Ambos cambios requieren revisión
e integración a `develop`; esta entrega no cierra toda la épica.

## Comportamiento

- Cada fila de Vigentes e Historial por estudiante ofrece **Consultar promoción**.
- La ventana muestra estudiante, ciclo, grado y sección usando las celdas de la
  fila. No añade catálogos ni descarga el padrón; es compatible con los nombres
  anidados del PR #636.
- Una consulta carga solo `GET /api/v1/enrolments/{enrolment_id}/promotion/`.
  El cliente presenta `progression`, `eligible_grade_name`, `total_subjects` y
  `failed_subjects`; no calcula notas, decide promociones ni selecciona destinos.
- Se distinguen promoción, repitencia y graduación. Esta última no tiene grado
  siguiente. `result_source=frozen` se identifica como resultado congelado;
  `live` se advierte como cálculo que puede cambiar, incluso en ciclos históricos
  sin snapshot. No se deduce la fuente a partir del estado del ciclo.
- Si el servidor devuelve cero subáreas, se advierte que debe revisarse el plan y
  los resultados. Se conserva la decisión recibida, sin cambiar reglas de dominio.
- Los errores se muestran dentro de la misma ventana con reintento explícito.
  Durante la carga se informa el estado; cerrar es posible porque solo hay lectura.
  Respuestas tardías de otra matrícula o una ventana desmontada se ignoran.
- Consultar no crea matrícula, movimiento ni cambio de estado. La reinscripción
  sigue siendo otra operación con sus validaciones de cupo, ciclo y autorización.

## Contrato y autorización

Se conserva ruta y respuesta JSON. Se corrige el acceso previo basado únicamente
en sesión: la lectura académica exige `enrollment_create` o `enrollment_update`
con un alcance vigente que cubra la sección de la matrícula, mediante
`require_section_scope`, el resolvedor existente del dominio. No hay permisos
nuevos ni reglas de autorización duplicadas en React. Una cuenta autenticada sin
permiso o alcance recibe 403 antes de calcular o leer el resultado. Las
denegaciones generan `identity.authorization.denied`.

El alcance administrativo se puede evaluar en ciclos cerrados: consultar un
resultado congelado no es una escritura académica. No concede acceso general a
otras secciones ni deriva permiso de una asignación docente. Esta entrega no
cambia los contratos ni la autorización de otras consultas del módulo.

ADR aplicables: ADR-0004 (REST), ADR-0005 (RBAC y alcances), ADR-0006
(historia) y ADR-0008 (límites de aplicación). Las reglas existentes siguen en
`determine_grade_eligibility` y `determine_promotion`; no hay migraciones,
dependencias ni variables de entorno nuevas.

## Evidencia automatizada y revisión

- `frontend/src/test/PromotionWindow.test.jsx`: promoción, repitencia,
  graduación, fuente congelada/vigente, cero subáreas, denegación y reintento,
  respuesta tardía y cierre durante la consulta.
- `frontend/src/test/newModulePages.test.jsx`: acceso desde fila vigente e
  historial, contexto con nombres y matrícula elegida.
- `frontend/src/test/moduleServices.test.js`: ruta GET, sin POST.
- `backend/tests/api/test_enrolments_api.py`: permiso y alcance ausentes,
  otra sección, asignación vencida, denegación auditada antes del cálculo,
  ambos permisos válidos, lectura congelada en ciclo cerrado sin mutaciones,
  graduación y conservación de pruebas de promoción/repitencia.
- Los servicios existentes conservan sus pruebas de reglas y snapshots en
  `backend/tests/unit/test_enrolments_services.py`.

La revisión visual institucional y la integración de los PR son pasos pendientes
de aceptación; las pruebas automatizadas no sustituyen esa revisión.
