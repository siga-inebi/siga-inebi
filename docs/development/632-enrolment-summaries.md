# Issue #632: M1, nombres incluidos en Matrículas

## Alcance y motivación

La tabla pedía los catálogos completos de estudiantes, ciclos, secciones y grados para convertir
UUID a etiquetas. El límite compartido de 40 páginas podía dejar nombres sin resolver, y un
fallo de catálogo perjudicaba una tabla cuya petición de matrículas sí había terminado.

Esta entrega implementa M1 de [la guía UX/UI](../ux-ui.md): los nombres viajan con la página de
matrículas. Incluye una búsqueda remota para el filtro de estudiante y carga diferida del
formulario de alta. Se creó `fix/632-enrolment-names` desde `develop` actualizado a `5f8630d`.
No duplica los PR #633–#635, que siguen pendientes de integración.

Se adelantó M1 porque #630 todavía no tiene una implementación publicada de `useServerList`.
La migración completa de los listados de comunidad educativa continúa pendiente de esa base.
No se implementa un hook de listados alternativo ni se modifican componentes compartidos.

## Diseño

- `EnrolmentSerializer` agrega resúmenes mínimos de estudiante, ciclo, grado y sección;
  `MatriculationSerializer` los hereda. Se mantienen los UUID y los payloads anteriores.
- Las consultas de lectura existentes en `services.py` precargan las relaciones que usa el
  serializador, incluidos persona y oferta de sección. No se añade ORM a las vistas ni reglas
  de negocio a componentes o serializadores.
- `EnrolmentsPage` presenta los resúmenes, incluyendo la jornada para distinguir secciones
  homónimas. Sin resumen presenta una etiqueta de indisponibilidad, sin recuperar un padrón.
- `EnrolmentStudentFilter` reutiliza `SearchableSelect` y `useSearchableCatalog` existentes.
  Busca explícitamente por nombre/código; limita resultados a la primera página y orienta a
  afinar el término. La clave de caché distingue esta búsqueda con inactivos del buscador de
  candidatos a matrícula. La etiqueta seleccionada se conserva fuera de las coincidencias.
- Cambiar estudiante reinicia la paginación. Solo se consulta la pestaña visible; Historial
  requiere una selección antes de consultar, como establece el contrato existente.
- `EnrolmentCreateWindow` conserva campos, validación y payloads del alta/reinscripción, y se
  monta bajo demanda. Los catálogos necesarios para ese formulario se piden al abrirlo.

El [contrato API](../architecture/api-conventions.md#resúmenes-de-matrícula-632-m1) enumera
campos, consumidores, privacidad y semántica histórica. No hay migraciones, variables nuevas,
modificaciones de datos ni cambios de autorización o reglas de matrícula.

## Pruebas verificables

Backend: `backend/tests/api/test_enrolment_summaries_api.py` comprueba resúmenes mínimos,
conservación de identificadores, historial con referencias desactivadas, autenticación y
una única consulta al serializar páginas de 1 y 25 filas, tanto vigentes como históricas.
Las pruebas existentes de alta, movimientos, cupo y permisos siguen siendo aplicables.

Frontend: `frontend/src/test/EnrolmentListSummaries.test.jsx` comprueba que abrir Matrículas
realiza únicamente la petición del listado, los nombres se muestran desde la respuesta,
la navegación pide solo la página visible, la selección remota consulta historial y los
catálogos del formulario no se descargan hasta abrirlo. `newModulePages.test.jsx` conserva
la regresión del payload de matrícula derivado de la sección y de los flujos existentes.

Reproducción desde `backend/`, con PostgreSQL configurado según `local-setup.md`:

```bash
python -m pytest tests/api/test_enrolment_summaries_api.py tests/api/test_enrolments_api.py --reuse-db --no-cov -q
python -m pytest --create-db --reuse-db -q
python -m ruff check apps tests
python -m ruff format --check apps tests
python manage.py makemigrations --check --dry-run
```

Desde `frontend/`:

```bash
npm exec vitest run src/test/EnrolmentListSummaries.test.jsx src/test/newModulePages.test.jsx -- --maxWorkers=1 --no-file-parallelism
npm run test:coverage -- --maxWorkers=1 --no-file-parallelism
npm run lint
npm run format:check
npm run build
```

Resultados locales del 17 de octubre de 2026:

| Comprobación | Resultado |
| --- | --- |
| Backend afectado | 58 pruebas aprobadas, incluidas 8 nuevas |
| Backend completo con base automática recreada | 1.784 aprobadas, 23 omitidas; cobertura 95,15 % |
| UI afectada | 44 pruebas aprobadas, incluidas 4 nuevas |
| Frontend completo | 313 aprobadas en 37 archivos; cobertura de líneas 85,17 % |
| Ruff, formato backend y Bandit de enrolments | Aprobados |
| ESLint y Prettier | Aprobados |
| Build y presupuestos frontend | Aprobados; carga inicial 221.587/230.000 bytes gzip |
| Detección de migraciones y `git diff --check` | Sin cambios / aprobado |
| OpenAPI validado | Cero errores; 27 advertencias (23 únicas), misma cantidad que la base comparada con #633 |
| HTTP en preview aislada | Frontend/login/vigentes/historial responden 200; resúmenes mínimos verificados |

Entorno existente: PostgreSQL 18.3 y Python 3.11.3 / Django 5.2.17; frontend con Vitest 3.2.7.
Las dependencias locales difieren de las fijadas; CI verifica las versiones fijadas y el entorno
reproducible. No se actualizan dependencias. Docker y revisión visual en navegador automatizado
no se ejecutaron localmente para esta entrega.

Preview de esta rama: `http://127.0.0.1:5175/app/matriculas`, backend `127.0.0.1:8003`.
No sustituye las instancias locales anteriores ni fusiona los PR anteriores en `develop`.

## Qué queda pendiente

- Los formularios de alta/reinscripción todavía usan catálogos completos al abrirse; migrarlos
  al `search-select` de `EntityFormWindow` depende de #630. No se declara eliminado el límite
  de 1.000 registros de todos los selectores ni del resto de pantallas.
- M2 (operación masiva y filtros por ciclo), M3–M7 y el expediente con pestañas continúan
  pendientes. Los botones existentes de movimientos y documentos conservan sus flujos.
- No se migran los listados E3/T2/G2 a `useServerList` ni se redefine paginación/exportación
  compartida en esta entrega. Las funciones de catálogos compartidas no se modifican.
- #635 debe integrarse para disponer del contrato documentado de búsqueda de comunidad e
  inclusión explícita de inactivos; esta entrega mantiene compatibilidad con la búsqueda por
  nombre/código de estudiantes que ya existe en `develop`.

## Revisión manual y reversión

Abrir Matrículas con Red del navegador visible: debe consultarse `/enrolments/active/`, sin
descargar estudiantes, ciclos, secciones ni niveles. Escribir dos o más caracteres en el filtro,
seleccionar una coincidencia y revisar Historial. Abrir Nueva matrícula y comprobar entonces
las consultas de sus catálogos. Comprobar nombres, código, ciclo, grado, sección y jornada.

Revertir el commit de esta entrega restaura presentación y consultas anteriores; no hay datos
ni esquema que reparar. Esta rama no altera por sí sola los servidores locales ya ejecutados.
