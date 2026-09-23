# Catalogos Configurables

## Proposito

Dejar por escrito que catalogos institucionales son datos administrables y cuales
son constantes de codigo a proposito, para que `RNF-MAN-001` se pueda verificar
en vez de suponerse.

`RNF-MAN-001` — *Ningun catalogo institucional fijado en codigo: tipos de
documento, plantillas, parametros de jornada, ponderaciones y etiquetas son
configurables* (prioridad MoSCoW: Debe).

## Regla

Un catalogo institucional es una lista que el establecimiento puede querer
cambiar durante la vida del sistema: agregar una entrada, renombrarla o retirarla.
Ese cambio debe ser una tarea administrativa, nunca una migracion ni un
despliegue.

Lo contrario tambien vale, y es la mitad que suele olvidarse: una regla que el
requerimiento fija de forma explicita **no** es configurable, y exponerla como
parametro seria un defecto, no una mejora. Toda constante de esa clase se lista
abajo con la fuente que la fija.

Una lista que enumera los estados internos de un flujo tampoco es un catalogo:
`open`/`closed`, `active`/`archived`, `draft`/`active` son ramas de codigo, y
agregar una implica escribir el comportamiento que le corresponde.

## Catalogos administrables

| Catalogo | Donde vive | Se administra en |
| --- | --- | --- |
| Tipos de documento | `documents.DocumentKind` | `GET/POST /api/v1/documents/types/`, pantalla "Tipos de documento" |
| Plantillas documentales | `documents.DocumentTemplate` (+ versiones inmutables) | `/api/v1/documents/templates/`, pantalla "Plantillas" |
| Etiquetas de contenido de plantilla | `documents.DocumentTemplate.content` | Contenido libre de la plantilla |
| Parametros de jornada | `attendance.JornadaParameters` | API de asistencia, vigentes por `effective_from` |
| Umbrales de ausencias frecuentes | `reporting.AbsenceThresholdParameters` | API de reportes, vigentes por `effective_from` |
| Estructura academica (sedes, jornadas, niveles, grados, secciones, cursos, aulas) | `academics.*` | API de academics |
| Unidades de evaluacion y su cantidad por defecto | `evaluation.{EvaluationUnit,EvaluationGlobalConfig,CycleEvaluationConfig}` | API de evaluacion |
| Permisos atomicos y roles | `identity.{Role,RoleAssignment,ScopeGrant}` | API de identidad |

Los parametros operativos (tiempos de sesion, intentos de ingreso, tamano maximo
de adjunto, crecimiento estimado de almacenamiento, `CONN_MAX_AGE`) se leen de
variables de entorno en `backend/config/settings/base.py`: se ajustan por
infraestructura sin recompilar nada.

## Constantes fijadas a proposito

| Constante | Valor | Por que no es configurable |
| --- | --- | --- |
| `SUBJECT_APPROVAL_THRESHOLD` | 60 | RF-RES-003: lo fija el Reglamento de Evaluacion de los Aprendizajes; ninguna institucion puede bajarlo |
| `RECOVERY_MIN_ATTENDANCE_PERCENTAGE` y limites de subareas reprobadas | 80 % y 3/4 | RF-RES-004: misma fuente reglamentaria |
| `GRADE_MIN_VALUE` / `GRADE_MAX_VALUE` | 0 y 100 | Escala nacional de notas; sostiene ademas una restriccion de base de datos |
| `FIELD_TAGS` (`apps/documents/field_catalog.py`) | 8 etiquetas | RF-PLA-002: cada etiqueta es un resolutor contra un campo de modelo. Una etiqueta que nadie programo no se puede rellenar, asi que darla de alta desde una pantalla produciria documentos con huecos |
| `ATOMIC_PERMISSIONS` (`apps/identity/atomic_permissions.py`) | catalogo cerrado | Cada permiso lo comprueba una vista o un servicio concreto; uno inventado desde la interfaz no protegeria nada |
| Niveles nacionales (`ensure_national_levels`) | preprimaria..diversificado | Los fija el MINEDUC; las jornadas, grados y secciones que cuelgan de ellos si son administrables |

## Tipos de documento (cambio de `RNF-MAN-001`)

Hasta esta entrega los tipos de documento eran un `TextChoices` en
`DocumentTemplate`. Agregar una constancia nueva exigia migracion y despliegue,
que es justo lo que el requerimiento prohibe.

Ahora son filas de `documents.DocumentKind`, una por institucion:

- `code` es el identificador estable que expone la API (el campo `kind` de una
  plantilla sigue serializando ese codigo, asi que el contrato publico no
  cambio) y es inmutable tras el alta;
- `label` es el texto visible y se edita libremente;
- la baja es logica (`is_active`) y el borrado fisico esta prohibido, porque las
  plantillas y las versiones inmutables siguen apuntando al codigo (ADR-0006);
- desactivar un tipo con plantillas activas se rechaza: dejaria una plantilla
  apuntando a un tipo que ya no se ofrece, y la emision resuelve plantillas por
  tipo;
- `DocumentTemplateVersion.kind` guarda una copia congelada del codigo, no una
  referencia: renombrar el tipo hoy no puede reescribir lo que decia una version
  emitida (RF-PLA-005).

La migracion `documents.0013_documentkind` siembra el catalogo inicial por
institucion y conserva cualquier codigo que ya estuviera en uso en vez de
colapsarlo en `other`.

## Verificacion

| Escenario | Prueba |
| --- | --- |
| Alta de un tipo nuevo y su uso en una plantilla, sin migracion | `backend/tests/unit/test_documents_services.py::test_document_type_catalogue_admits_a_new_type_without_touching_code` |
| El catalogo es por institucion | `...::test_document_type_catalogue_is_scoped_to_its_institution` |
| El nombre visible se edita; el codigo no | `...::test_document_type_label_is_editable_and_the_code_is_not` |
| Baja logica, con plantillas activas rechazada y sin borrado fisico | `...::test_document_type_is_deactivated_not_deleted_and_keeps_active_templates_usable` |
| Un tipo retirado deja de ofrecerse | `...::test_deactivated_document_type_is_no_longer_offered_for_new_templates` |
| La version emitida conserva el codigo de su momento | `...::test_template_version_snapshot_keeps_the_code_it_was_issued_with` |
| Ciclo completo por API (alta, edicion, baja) | `backend/tests/api/test_documents_api.py::test_document_type_is_created_updated_and_deactivated_over_the_api` |
| Rechazo de un tipo inexistente | `...::test_creating_a_template_with_an_unknown_type_is_rejected` |
| Migracion de datos de un despliegue existente | `backend/tests/migrations/test_documents_0013_document_kind.py` |
| La pantalla llena el selector con el catalogo del backend | `frontend/src/test/newModulePages.test.jsx` (`DocumentTypesPage`, `TemplatesPage`) |

Se corren con `make test-backend` y `make test-frontend`.
