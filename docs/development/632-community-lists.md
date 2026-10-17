# Issue #632: contratos de listados de comunidad educativa

## Objetivo y alcance

Entrega backend previa a la migración de pantallas. Atiende 1.1.6–1.1.7, PE1 y la parte
de contrato de E10, T2, G2 y PE3 de [la guía UX/UI](../ux-ui.md). Prepara E3 sin declararlo
resuelto: las descargas completas y el corte de 1.000 registros del frontend siguen pendientes.

Rama `fix/632-community-search`, creada desde `develop` actualizado a `5f8630d`.
Es independiente de los PR #633 (persistencia de persona) y #634 (registros del expediente).
No contiene sus cambios ni sustituye su integración en `develop`.

## Decisiones aplicadas

- Los cuatro listados excluyen la baja lógica por defecto y admiten inclusión explícita.
- El estado del expediente estudiantil se filtra de forma independiente de la baja lógica.
- La búsqueda reutiliza `SearchFilter` de DRF, ya utilizado por Estudiantes; no crea otra
  infraestructura transversal de búsqueda.
- Los parámetros específicos se validan mediante serializadores de consulta y se publican en
  OpenAPI. Los filtros ORM viven en `queries.py` conforme a ADR-0008.
- Los helpers de consulta conservan `include_inactive=True` como valor predeterminado para
  mantener la semántica previa de las consultas individuales y otros consumidores internos.
  Las vistas de listado pasan explícitamente el valor validado, cuyo predeterminado es `False`.
- No cambia autorización, esquema, historial, permisos ni reglas de conversión de personas.
  No aplica una nueva decisión de negocio D4/D5/D7/D10 en esta entrega.

El [contrato API](../architecture/api-conventions.md#listados-de-comunidad-educativa-632)
documenta campos de búsqueda, valores, errores y la adaptación de consumidores existentes.
Los CUI de pruebas son valores sintéticos. Los ejemplos siguientes evitan datos personales.

## Ejemplos de consulta

Con una sesión autorizada:

```http
GET /api/v1/people/?search=Demo&include_inactive=true
GET /api/v1/teachers/?search=EMP-&position=Administrativo
GET /api/v1/students/?search=STU-&status=pre_enrolled&page=2
GET /api/v1/students/guardians/?search=Demo&include_inactive=true
```

Conservar todos los filtros al seguir `next` y `previous`. Omitir el filtro específico si
se quieren todos los estados o puestos; no enviar una cadena vacía. Una segunda página
inexistente conserva la respuesta 404 estándar de DRF.

## Pruebas y reproducción

`backend/tests/api/test_community_list_filters_api.py` cubre:

- Activos por defecto, booleanos explícitos y errores de parámetros.
- Búsqueda por nombres con varios términos, CUI y códigos; cero coincidencias.
- Filtrado previo a paginación con 26 coincidencias y 26 distractores por dominio,
  navegación y desempate de nombres iguales, sin filas repetidas ni omitidas.
- Los seis estados del expediente y el puesto docente combinados con otros filtros.
- Autenticación, permiso/alcance estudiantil y exclusión de estudiantes ajenos al alcance.
- Consulta individual de registros desactivados usando los identificadores existentes.

Desde `backend/`, con PostgreSQL configurado según [local-setup](local-setup.md):

```bash
python -m pytest tests/api/test_community_list_filters_api.py tests/api/test_people_api.py tests/api/test_teachers_api.py tests/api/test_students_api.py tests/api/test_guardians_api.py --reuse-db --no-cov -q
python -m pytest --create-db --reuse-db -q
python -m ruff check apps tests
python -m ruff format --check apps tests
python manage.py makemigrations --check --dry-run
```

La recreación se aplica únicamente a la base automática de pruebas, nunca a la base de uso local.

Validación local del 17 de octubre de 2026:

| Comprobación | Resultado |
| --- | --- |
| Regresiones nuevas | 41 pruebas aprobadas; los casos iniciales reprodujeron búsqueda ignorada, actividad mezclada y filtros de dominio ausentes |
| Endpoints afectados, nuevas y existentes | 98 pruebas aprobadas |
| Backend completo con base de pruebas recreada | 1.817 aprobadas, 23 omitidas; cobertura 95,16 % |
| Ruff y formato backend | Aprobados |
| Bandit en people, teachers y students | Aprobado |
| Detección de migraciones | Sin cambios |
| OpenAPI con `spectacular --validate` | Cero errores; 27 advertencias (23 únicas), iguales a la rama base comparada con #633 |
| `git diff --check` | Aprobado |

Entorno existente: PostgreSQL 18.3 y Python 3.11.3 con Django 5.2.17. Las versiones locales
difieren de las fijadas por el proyecto; CI verifica las dependencias fijadas con Python 3.12
y PostgreSQL 16. No se modificaron dependencias para esta entrega. No hay cambios de frontend;
no se presenta la suite frontend ni Docker como ejecutados localmente en esta rama.
La referencia del PR y sus checks completan la evidencia de integración.

## Pendientes y orden de continuación

1. Integrar los PR #633 y #634 mediante la revisión habitual del equipo.
2. Adoptar `useServerList`, tamaño de página, URL e invalidación de caché entregados por #630.
3. Migrar Estudiantes, Docentes y Encargados para enviar búsqueda/filtros al servidor y retirar
   `useLocalList`/`collectAllPages`; conectar los filtros correspondientes en Personas.
4. Verificar exportaciones y selectores: los consumidores históricos deben pedir
   `include_inactive=true` cuando corresponda; no marcar E3 ni T2/G2 completos antes de esto.
5. Continuar los bloques restantes del issue, incluidos plantillas y expediente con pestañas.

No se cambia el entorno local que ya estaba ejecutándose: esta rama debe integrarse o levantarse
por separado para verificar el nuevo backend. No se agregan variables de entorno ni migraciones.

## Reversión

Revertir el commit de esta entrega restaura los contratos previos. No hay cambios de datos,
esquema ni estados que requieran reparación o restauración.
