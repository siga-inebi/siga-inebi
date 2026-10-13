# D2 — Evaluación e integración

**Responsable:** Estuardo  
**Fecha:** 12 de octubre de 2026 (America/Guatemala)  
**SHA probado:** `e67faeb97729281f2e7e7b9a91125f8612b79ffa`  
**Resultado automatizado:** 243 pruebas aprobadas; 0 fallidas; 4 advertencias de deprecación por corrida backend.

## Ejecución

Se usaron datos sintéticos y una base PostgreSQL 16 temporal en la red aislada
`siga_inebi_test_app_net`. El contenedor Python 3.11 disponible localmente se
reutilizó porque Docker Hub no respondió al intento de descargar la imagen base.
El contenedor montó el directorio `backend/` del SHA indicado; no se usaron datos
de desarrollo ni institucionales.

| Alcance | Comando principal | Resultado |
| --- | --- | --- |
| Evaluación y reportes | `pytest -q --no-cov -ra tests/unit/test_evaluation_services.py tests/api/test_evaluation_api.py tests/integration/test_evaluation.py tests/unit/test_reporting_services.py tests/api/test_reporting_api.py tests/integration/test_reporting.py` | 196 aprobadas, 0 fallidas; 4 advertencias `RemovedInDjango60Warning`. |
| Integración académica/documental | `pytest -q --no-cov -ra tests/unit/test_academics_services.py tests/unit/test_enrolments_services.py tests/unit/test_documents_services.py tests/unit/test_audit_services.py tests/api/test_academics_api.py tests/api/test_enrolments_api.py tests/api/test_documents_api.py tests/integration/test_academics.py tests/integration/test_enrolments.py tests/integration/test_documents.py -k "Frozen or Promotion or HistoricalCycleReport or historical_cycle_report or closed_cycle_history_report or boleta or close_cycle or closing_a_cycle or trace_includes"` | 43 aprobadas, 448 deseleccionadas; 4 advertencias `RemovedInDjango60Warning`. |
| Regresión de nota final (INC-008) | `npm.cmd test -- src/test/FinalGradeWindow.test.jsx` desde `frontend/` | 4 aprobadas. La ventana muestra `final_grade` (por ejemplo, 60 para promedio 59.5). |

Las pruebas cubren fronteras y validación de notas, promedios y nota final,
permisos/alcances docentes, estados y correcciones, cierre y congelamiento,
promoción, boleta/historial, trazabilidad y reportes. No se midió cobertura
porcentual (`--no-cov`). La regresión de interfaz confirma el cambio integrado
en [PR #555](https://github.com/siga-inebi/siga-inebi/pull/555); no reemplaza una
revisión visual manual de la interfaz.

## Estado de D2

- **Verificado técnicamente en este SHA:** pruebas automatizadas de evaluación,
  reportes e integración de resultados académicos/documentales; regresión de
  INC-008 en frontend.
- **Regla de pesos:** no se inventó una ponderación. La documentación disponible
  describe promedios de unidades, pero no define pesos de ponderación. Pablo debe
  confirmar si la regla es promedio simple o proporcionar la regla aprobada; por
  tanto, el caso de pesos queda pendiente de decisión.
- **Revisión conjunta:** no se registra una sesión de revisión con Josué ni con
  Roí. Hace falta que Josué revise la integración académica y Roí la boleta,
  reportes y evidencia de D2.
- **QA4-PDF-01:** las pruebas backend no resuelven la observación previa de
  integridad/descarga de PDF ni demuestran que la boleta sea legible desde la
  interfaz. Roí debe revisar/corregir ese flujo y registrar su validación.
- **Candidato final:** esta corrida prueba el SHA indicado, no un SHA de entrega
  institucional acordado. Repetir el subconjunto en el candidato final después
  de fijarlo.

Por lo anterior, D2 tiene su ejecución técnica automatizada documentada, pero no
se declara cerrada la ponderación ni la revisión conjunta/documental pendiente.
