# D2 â€” RevalidaciÃ³n de evaluaciÃ³n e integraciÃ³n

**Responsable:** Estuardo
**Fecha:** 13 de octubre de 2026
**Rama y SHA probados:** `develop`, `5ed5fd24d02f494053c53dbbbafe50a8412534e5`
**Entorno:** Docker Compose 5.4.0, Python 3.11 y PostgreSQL 16; datos de pruebas sintÃ©ticos.
**Tipo de evidencia:** suites automatizadas locales; no es una validaciÃ³n del despliegue QA ni una aceptaciÃ³n institucional.

## Resultados

| Ãrea | SelecciÃ³n ejecutada | Resultado |
| --- | --- | --- |
| EvaluaciÃ³n y reportes | `tests/unit/test_evaluation_services.py`, `tests/api/test_evaluation_api.py`, `tests/integration/test_evaluation.py`, `tests/unit/test_reporting_services.py`, `tests/api/test_reporting_api.py`, `tests/integration/test_reporting.py` | 196 aprobadas; 0 fallidas; 4 advertencias `RemovedInDjango60Warning`. |
| IntegraciÃ³n acadÃ©mica y documental | Suites de servicios, API e integraciÃ³n de academics, enrolments, documents y audit, filtradas por `Frozen`, `Promotion`, `HistoricalCycleReport`, `historical_cycle_report`, `closed_cycle_history_report`, `boleta`, `close_cycle`, `closing_a_cycle` o `trace_includes` | 43 aprobadas; 448 deseleccionadas; 0 fallidas; 4 advertencias `RemovedInDjango60Warning`. |
| RegresiÃ³n frontend INC-008 | `npm.cmd test -- src/test/FinalGradeWindow.test.jsx` desde `frontend/` | 4 aprobadas con Vitest 4.1.11. |

**Total de esta revalidaciÃ³n:** 243 pruebas aprobadas, 0 fallidas y 8 advertencias backend. Las 448 pruebas deseleccionadas pertenecen a la selecciÃ³n de integraciÃ³n indicada; no se cuentan como aprobadas. No se midiÃ³ cobertura (`--no-cov`).

## Comandos reproducibles

Desde la raÃ­z del repositorio:

```powershell
docker compose -p siga_inebi_d2_current -f compose.yml -f compose.test.yml run --build --rm backend-test pytest -q --no-cov -ra tests/unit/test_evaluation_services.py tests/api/test_evaluation_api.py tests/integration/test_evaluation.py tests/unit/test_reporting_services.py tests/api/test_reporting_api.py tests/integration/test_reporting.py
```

```powershell
docker compose -p siga_inebi_d2_current -f compose.yml -f compose.test.yml run --rm backend-test pytest -q --no-cov -ra tests/unit/test_academics_services.py tests/unit/test_enrolments_services.py tests/unit/test_documents_services.py tests/unit/test_audit_services.py tests/api/test_academics_api.py tests/api/test_enrolments_api.py tests/api/test_documents_api.py tests/integration/test_academics.py tests/integration/test_enrolments.py tests/integration/test_documents.py -k "Frozen or Promotion or HistoricalCycleReport or historical_cycle_report or closed_cycle_history_report or boleta or close_cycle or closing_a_cycle or trace_includes"
```

Desde `frontend/`:

```powershell
npm.cmd test -- src/test/FinalGradeWindow.test.jsx
```

## Cierre D2

La ejecuciÃ³n automatizada quedÃ³ revalidada sobre el SHA local indicado. D2 sigue sujeto a los siguientes elementos:

- Pablo debe confirmar el criterio de pesos; no se presume una ponderaciÃ³n.
- JosuÃ© debe revisar la integraciÃ³n acadÃ©mica y RoÃ­ la evidencia documental/boleta.
- RoÃ­ debe resolver QA4-PDF-01 y comprobar descarga/legibilidad de la boleta.
- INC-008 tiene regresiÃ³n automatizada aprobada; esta corrida no incluye inspecciÃ³n visual manual.
- Repetir los casos afectados cuando se identifique y registre el SHA del candidato final desplegado.

Esta revalidaciÃ³n no sustituye esas decisiones o revisiones y no afirma que este SHA sea el candidato QA final.
