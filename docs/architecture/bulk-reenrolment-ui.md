# Reinscripción por lotes: contrato y evidencia del issue #632

## Alcance

RF-MOV-007 conserva sus reglas y su endpoint de escritura. Este bloque conecta la
interfaz al lote existente, resuelve la consulta global de matrículas de M2 y
entrega la parte de reinscripción masiva de M4. Añade los filtros de servidor que
necesita M5; la pantalla general de filtros se integra en el bloque de listas
compartidas del #630. No completa M2/M4/M5 ni el issue #632 íntegramente.

Se revisaron AGENTS.md, RF-MOV-007, RF-MAT-007, el mapa de dominios, los contratos
de API y ADR-0004/0005/0006/0008. No se cambian reglas de promoción, autorización,
cupo, idempotencia ni conservación de historial. No requiere migraciones ni
variables de entorno nuevas.

## Uso desde Matrículas

1. Abrir **Reinscribir por lotes** y seleccionar el ciclo de origen.
2. Buscar por nombre o código; seleccionar filas o la página visible. Se conserva
   la selección al buscar y paginar; cambiar de ciclo de origen la limpia.
3. Elegir ciclo y sección de destino y fecha de vigencia. Las secciones se
   consultan por el ciclo seleccionado; no se descarga el catálogo global.
4. Solicitar **Vista previa**. Se envía un solo POST con los identificadores de
   las matrículas seleccionadas y la sección de destino de cada fila.
5. Revisar el resultado por estudiante y usar **Confirmar reinscripción**. La
   confirmación utiliza el mismo lote revisado con `preview=false`.

Cambiar selección, fecha, ciclo o sección de destino invalida la revisión.
Mientras se procesa el lote se bloquean los campos y las acciones de envío.
La vista previa no reserva plazas: el servidor revalida al confirmar y puede
devolver un resultado parcial. Se muestran tanto las filas correctas como los
errores; ninguna fila se selecciona ni se promueve automáticamente.

Después de confirmar se exige una nueva revisión para otro envío. Si se pierde
la conexión se conserva la selección y se puede revisar y reintentar: el
endpoint distingue `existing` de `created` y no duplica lo ya registrado. La
tabla principal se recarga cuando hay filas `created`.

## Consulta de candidatos

`GET /api/v1/enrolments/re-enrolments/candidates/`

| Parámetro | Contrato |
| --- | --- |
| `academic_cycle_id` | UUID público obligatorio del ciclo de origen |
| `grade_id`, `section_id` | UUID públicos opcionales, combinables con AND |
| `search` | Nombre, apellido o código; términos separados combinados con AND; sin distinción de mayúsculas; máximo 150 caracteres |
| `page` | Paginación estándar, 25 filas por página |

Responde `{count,next,previous,results}`. Cada resultado contiene únicamente
`public_id` (de la matrícula de origen), `student_code`, `first_name`,
`last_name`, `grade_name`, `section_name` y `status`. No hace falta descargar
el padrón de personas o estudiantes para traducir UUID.

El filtro por ciclo, búsqueda, estado y alcance ocurre antes de paginar. El
orden estable es código de estudiante y PK de matrícula. Se ofrecen matrículas
no desactivadas `active` o `completed`, de estudiantes no desactivados. Una
candidata no constituye autorización ni garantía de éxito del lote.

La consulta requiere sesión y `enrollment_create`; reutiliza
`authorized_student_queryset` de identidad, el mismo alcance de estudiante que
consulta la escritura masiva mediante `has_scoped_permission`. No añade
permisos implícitos ni excepciones administrativas. Sin permiso o alcance
vigente devuelve 403; con alcance vigente ajeno a los candidatos devuelve una
página vacía. UUID inválidos, ausencia de ciclo o búsqueda excesiva devuelven
400. Un UUID válido sin coincidencias devuelve una página vacía.

La selección de matrículas `completed` queda sometida a la política central de
alcance: los grants por dimensiones académicas resuelven estudiantes mediante
matrículas activas; un grant directo al estudiante o al módulo de estudiantes
puede cubrir expedientes sin una matrícula activa. Este cambio no amplía esa
política. La escritura sigue validando el ciclo destino y todas sus reglas.

## Filtros de matrículas vigentes

`GET /api/v1/enrolments/active/` admite ahora `academic_cycle_id`, `grade_id` y
`section_id`, combinables con el `student_id` existente. Son UUID públicos y se
aplican en servidor antes de paginar. Se conserva el contrato de lectura con
sesión y de estados: únicamente `is_active=true,status=active`.

La ventana existente **Matricular por lotes** pasa el ciclo a esta consulta.
Conserva las altas iniciales individuales: `/re-enrolments/bulk/` exige una
matrícula anterior y no es intercambiable con `/matriculations/`. La eliminación
de las peticiones individuales de altas iniciales requiere un contrato masivo
propio; no se presenta esta parte de M2 como resuelta. M6 permitirá ordenar
posteriormente las entradas de alta de la cabecera.

## Pruebas reproducibles

Todos los datos de las pruebas son sintéticos. Backend en PostgreSQL:

```powershell
python -m pytest --reuse-db --no-cov -q tests/api/test_reenrolment_candidates_api.py
```

La selección prueba denegación sin sesión/permiso/alcance, validación de UUID y
búsqueda, aislamiento por alcance y ciclo, más de 25 resultados sin cortes,
estados excluidos, nombres/códigos, filtros combinados y la secuencia
candidato → vista previa sin escrituras → confirmación → repetición idempotente.

```powershell
npm exec vitest -- run src/test/bulkReenrolment.test.jsx src/test/moduleServices.test.js src/test/newModulePages.test.jsx --maxWorkers=1 --no-file-parallelism
```

Frontend prueba selección entre páginas y búsquedas, un POST por lote, revisión
obligatoria, cambios que invalidan confirmación, resultado parcial por nombre,
recarga tras creación, errores de conexión y reintento de consulta. Los tests
de servicios verifican rutas y parámetros HTTP; los existentes conservan las
altas iniciales. Estas comprobaciones automatizadas no sustituyen aceptación
visual institucional ni certifican la totalidad del epic.

## Integración y reversión

Evidencia local del 17 de octubre de 2026: suite backend completa, 1.785 pruebas
aprobadas, 23 omitidas y 95,17 % de cobertura; suite frontend completa, 321
pruebas aprobadas en 37 archivos y 85,31 % de cobertura de líneas. Entorno nativo:
PostgreSQL 18.3, Python 3.11.3, Django 5.2.17 y Vitest 3.2.7; las versiones
bloqueadas del proyecto se verifican en CI. Ruff, ESLint, formato, build con
presupuesto, Bandit de matrícula y `makemigrations --check --dry-run` aprobados;
49 pruebas de las herramientas de requerimientos aprobadas. OpenAPI validado
sin errores, conservando las 27 advertencias de la base.

La comprobación HTTP por el proxy local verificó sesión, candidatos en más de
una página, ausencia de duplicados entre páginas y estados `ready`, `created`
y `existing` al revisar, confirmar y repetir. Se usó exclusivamente la base
sintética aislada `siga_inebi_reenrolment_preview`; no se alteraron las otras
instancias. No se presenta esta prueba HTTP como revisión visual automatizada.

Rama creada desde `develop` actualizado (`5f8630d`). No incluye ni requiere
fusionar los PR #633–#637: el DTO de candidatos es específico de este flujo y no
modifica el DTO general de matrícula de M1. El #630 conserva la responsabilidad
del hook de listas, estado en URL, selectores compartidos e invalidación general
de cachés. Esta ventana reutiliza los componentes y hooks actuales.

Para revertir, retirar el acceso a la ventana y revertir este cambio de código.
Las matrículas confirmadas conservan su historial; no deben eliminarse para
revertir la interfaz. Los endpoints de escritura preexistentes permanecen
compatibles.
