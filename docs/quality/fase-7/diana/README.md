# Primera ronda de Diana — personas, estudiantes y expediente

Fecha: 12 de octubre de 2026, America/Guatemala.
Código evaluado: `72ea438cd9a2427524346856d850578f6132e715` (`develop`, árbol limpio al iniciar).
Responsable: Diana. Ejecución técnica asistida por Claude Code; revisión de Santiago pendiente.
Diagnóstico local; no constituye candidato formal, aceptación institucional ni UAT.

## Archivos de trabajo

- [Ronda 2: integración y regresión](ronda-2/README.md) (13/10): regresión de INC-009 e INC-013 aprobada, cobertura de la sugerencia de código, integración por API de matrícula, justificaciones y documentos (44 de 46), nueva INC-DIA-001 y trazabilidad de INC-008.
- [Resultado de la primera corrida](resultado-primera-corrida.md): backend **150 pruebas aprobadas**, cero fallos y cero omitidas; frontend **29 aprobadas y 2 fallidas** por tiempo de espera (INC-013). Revisión humana pendiente.
- [Catálogo inicial](catalogo-inicial.csv): 17 requisitos (RF-EXP-001 a 009, RNF-AUD-003, RNF-PRI-001 a 005, RF-ALC-006 y RF-CRE-002), criterios originales y referencias candidatas por función.
- [Inventario de pruebas](inventario-pruebas.csv): 181 casos (150 backend y 31 frontend) con requisito candidato y línea.
- [Resultados por prueba](resultados-pruebas.csv): estado y duración de cada caso, transcritos de JUnit, incluida la corrida de diagnóstico.
- [Evidencia revisada](evidencia-revisada.md): comandos, versiones y hashes de los logs/JUnit locales. Los artefactos crudos no se publican en Git; su entrega a revisores está pendiente.
- [Casos de integración en pareja](casos-integracion.md): fichas de los cuatro flujos manuales con Josué, Santiago, Emilio y Roí, con reparto de pasos. No ejecutados.
- El catálogo general y sus resultados históricos se conservan. Este catálogo complementario no aprueba requisitos ni modifica el alcance institucional.

## Primeros seis casos

Todos usan datos sintéticos de las factories existentes y una base PostgreSQL de pruebas efímera. Ejecutor técnico: Claude Code, para Diana; revisor propuesto: Santiago. El estado inicial se reconstruye por los fixtures de pytest y sus transacciones; no se modifica la base de desarrollo. Las referencias son relativas a `backend/`.

| Caso | Requisito / fuente | Precondición y pasos | Resultado esperado | Prueba reutilizada |
| --- | --- | --- | --- | --- |
| CP-API-EXP-DIA-001 | RF-EXP-001, RF-EXP-002 | Con permiso y alcance, crear un estudiante con sus datos personales; repetir el alta con un código ya usado; repetir sin permiso. | Alta con persona anidada y código único; el duplicado se rechaza sin escribir; sin permiso se deniega. | `tests/api/test_students_api.py::test_create_student`, `::test_create_student_duplicate_student_code_is_rejected`, `::test_create_student_without_permission_is_denied`; `tests/unit/test_students.py::test_student_code_unique` |
| CP-API-EXP-DIA-002 | RF-EXP-004 | Vincular un encargado con parentesco; intentar terminar el vínculo principal sin reemplazo; terminarlo con reemplazo; cambiar el principal. | Un solo encargado principal vigente; terminar el principal exige reemplazo; la historia de vínculos se conserva. | `tests/api/test_guardians_api.py::test_create_student_guardian_relation`, `::test_ending_primary_student_guardian_relation_requires_replacement`, `::test_end_student_guardian_relation_with_replacement`; `tests/unit/test_student_guardian_relation_services.py` |
| CP-SEG-EXP-DIA-003 | RF-EXP-009, RNF-AUD-003 | Crear y leer una nota de salud con permiso sensible y alcance; repetir con solo permiso básico; repetir con permiso sensible sin alcance. | Lectura permitida y auditada; acceso básico denegado; permiso sin alcance denegado; la baja conserva historia. | `tests/api/test_student_health_notes_api.py` (5 funciones); `tests/unit/test_student_health_note_services.py` |
| CP-SEG-ALC-DIA-004 | RF-ALC-006, RF-EXP-004 | Encargado con relación vigente y otra terminada; estudiante ajeno; terminar un vínculo vigente. | El encargado solo ve a sus estudiantes vigentes; terminar el vínculo revoca el alcance de inmediato. | `tests/permissions/test_guardian_derived_scope.py` (4 funciones); `tests/unit/test_students.py::test_guardian_access_cut_off_after_relation_end` |
| CP-INT-EXP-DIA-005 | RF-EXP-003, RF-EXP-008 | Recorrer el ciclo de vida de un estudiante; cambiar su estado; intentar borrado físico por instancia y por consulta. | El estado restringe la interacción; perfil y relaciones se conservan; el borrado físico se rechaza. | `tests/integration/test_student_lifecycle.py::test_student_lifecycle_preserves_profile_and_relations`; `tests/unit/test_students.py::test_student_record_instance_cannot_be_physically_deleted`, `::test_student_record_queryset_cannot_be_physically_deleted` |
| CP-SEG-PRI-DIA-006 | RNF-PRI-001, RNF-PRI-002, RNF-PRI-003 | Emitir credencial e inspeccionar el QR; escanear a un estudiante con nota de salud, observación y contacto; consultar presencia con y sin autorización. | El QR codifica solo el identificador opaco; la confirmación no filtra salud, notas ni contacto; toda respuesta de la API sale con `Cache-Control: no-store`. | `tests/unit/test_qr.py`; `tests/api/test_attendance_api.py::test_scan_endpoint_confirmation_never_leaks_health_academic_or_contact_data`; `tests/unit/test_no_store_api_middleware.py`; `tests/permissions/test_attendance_permissions.py` |

Las clases y archivos agrupan varios casos automatizados; el inventario enumera sus nodos precisos. Revisar las aserciones por criterio antes de afirmar cobertura completa.

## Incidencias registradas en esta ronda

Nota: la incidencia de los dos fallos de frontend se registró primero como INC-008. Ese
número ya correspondía a una incidencia de evaluación (PR #553), y INC-010 a INC-012 están
en uso en los PR abiertos de asistencia (#575 y #576), así que se renumeró a INC-013. El
hallazgo y su evidencia no cambian.

| ID | Hallazgo | Severidad | Estado |
| --- | --- | --- | --- |
| INC-013 | Dos pruebas de frontend (`GuardiansPage`: crear encargado; `personasPage`: crear persona) fallan por el límite de 5 s en este equipo. Con `--testTimeout=30000` pasan en 6,5 s y 5,2 s, y el CI de `develop` las aprueba en el mismo commit. Margen de tiempo insuficiente, no defecto funcional confirmado. | S4 | Abierta |
| INC-009 | `GET students/{id}/emergency-contacts/` pagina una consulta sin orden (`UnorderedObjectListWarning`): `EmergencyContact` no declara `ordering` y `emergency_contacts()` no ordena. Dos páginas pueden repetir u omitir filas. | S3 | Abierta |

## Brechas y decisiones para Pablo / Santiago

1. **Discrepancia del plan.** La tabla 10.1 de `tests_plan.md` asigna a expediente los requisitos `RF-EST-001–013`, pero en `requirements.json` el prefijo `RF-EST` es *Estructura Académica* (dominios `institutional-structure` y `school-cycle`, de Josué). Los requisitos de expediente son `RF-EXP-001–009`. Se trabajó con `RF-EXP`; confirmar y corregir el plan.
2. **Estado desactualizado en el catálogo.** `RNF-PRI-001`, `RNF-PRI-002` y `RNF-PRI-003` figuran `Not implemented` / `Fuera del candidato actual`, pero sus PR (#499, #500 y #532) están fusionados en `develop` y sus pruebas pasan. Lo mismo ocurre con `RF-ALC-006`. Reconciliar; no se cambia el estado por una suite aprobada.
3. `RF-EXP-006` figura `In Progress`: la política de acceso a observaciones sigue abierta (PD-005). Las pruebas verifican permiso sensible y alcance, no la política institucional.
4. `RF-EXP-002` ("genera o valida" el código): esta ronda cubre la unicidad. La sugerencia del siguiente código libre tiene pruebas en `tests/api/test_form_suggestions_api.py::test_student_next_code_*`, que no se incluyeron; agregarlas en la siguiente corrida.
5. `RF-CRE-002`, `RNF-PRI-004` y `RNF-PRI-005` aparecen en el dominio o en la fila del plan de Diana, pero sus pruebas viven en las suites de credencial/asistencia (Emilio) y documentos (Roí). No se ejecutaron aquí; acordar quién las reporta.
6. INC-007 (la edición de persona enviaba `PATCH /people/undefined/`) toca este dominio y sigue `En verificación` a cargo de Daniel. Las pruebas de componentes pasan; falta comprobarlo en el QA cloud con navegador real.
7. Esta ronda usa `force_login` y jsdom: no demuestra login real, CSRF, navegador, cámara, usabilidad ni UAT. `--no-cov` es intencional para un subconjunto.
8. **Diccionario de datos.** El PDF del 29/09 declara como versión canónica `docs/architecture/data-dictionary.md`, generada con `backend/scripts/generate_data_dictionary.py`; ninguno de los dos archivos existe en `develop` ni en otra rama remota. Sin ellos no se puede regenerar ni contrastar contra las migraciones (tarea D3). Requiere decisión: versionar generador y diccionario, o declarar el PDF como única fuente.

## Siguiente sesión manual

Con Josué (CP-INT-MAT-001): persona → estudiante → estructura/ciclo → matrícula → consulta autorizada, comprobando vigencias y auditoría en el QA integrado. Con Santiago: pérdida de alcance del encargado al terminar el vínculo, con cuentas sintéticas permitidas y denegadas. Con Roí (CP-INT-DOC-001) y Emilio (CP-INT-JUS-001) según su agenda. Registrar pasos, esperado/observado, SHA, evidencias e incidencias.

Cada resultado se entrega a Pablo y las evidencias técnicas a Daniel; Santiago verifica la revisión cruzada.
