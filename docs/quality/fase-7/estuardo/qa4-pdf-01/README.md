# QA4-PDF-01: regresión de descarga y legibilidad de boleta

**Actualización del 14 de octubre:** la corrección está integrada en `develop` por el PR #595 y desplegada en QA mediante el commit `7f04a945d09bf77c514cf7bfe988888f2e2bfd10`. La [repetición sobre el código candidato, los JUnit, un PDF nuevo y su captura](candidato-2026-10-14/README.md) están disponibles. [Roí aprobó con observaciones el cierre técnico de QA4-PDF-01](https://github.com/siga-inebi/siga-inebi/pull/602#pullrequestreview-5521977443). Estuardo comunicó la autorización de Pablo para el cierre formal y que Pablo aprobó por su lado la descarga legible en QA. Se registra **aprobado según Pablo**; esa ejecución adicional no tiene PDF ni registro adjunto. Véase el [informe de INC-008](../informe-inc-008-2026-10-13.md).

**Fecha:** 13 de octubre de 2026 (America/Guatemala).
**Base de código:** `develop` en `68fa7753d0578abfa37a153df8a7f68e4b46a2bd`, más la corrección local del generador de PDF en esta rama. Esta ejecución **no identifica el SHA desplegado en QA**.
**Ejecutor:** verificación técnica asistida para Estuardo; revisión independiente de Roí pendiente.
**Entorno:** Docker Compose, Python 3.11, PostgreSQL 16; PyMuPDF local para inspección de PDF. Datos sintéticos de las factories.

## Hallazgo original y cambio

La [ronda 4](../ronda-4/README.md) descargó una boleta con HTTP 200 y contenido correcto, pero PyMuPDF informó `is_repaired=true` y `cannot recognize xref format`. La [boleta original](../ronda-4/evidencias.md) se conserva como evidencia histórica. `compile_historical_cycle_report` escribía posiciones `xref` y `startxref` constantes aunque el texto y el código de verificación cambian la longitud del PDF. Ahora calcula cada posición a partir de los bytes efectivamente emitidos. El contrato HTTP y los datos de la boleta no cambian.

## Procedimiento y resultado

1. Con matrícula, subárea y ciclo sintéticos, se registraron 59 y 60 en dos unidades, se cerraron ambas unidades y el ciclo.
2. Una cuenta de prueba con permiso `document_issue` solicitó `GET /api/v1/documents/historical-cycle-reports/?enrolment_id=...` por el cliente de API de Django. La respuesta fue HTTP 200, `application/pdf`, descarga `attachment`.
3. La prueba de regresión comprobó que `startxref` apunta a la tabla `xref` y que cada posición de objeto anunciada apunta al objeto correspondiente.
4. El [PDF descargado](boleta-sintetica.pdf) abrió en PyMuPDF con **`is_repaired=false`** y una página. La extracción de texto y la [captura renderizada](boleta-sintetica.png) muestran unidad 1 = 59, unidad 2 = 60, nota final = 60, «Aprobado» y «Promovido». La captura se inspeccionó visualmente.

| Artefacto | SHA-256 |
| --- | --- |
| `boleta-sintetica.pdf` | `dd9932010432fe6d10a49254ea547db2f9ce8d15d3c881eab0cb41e7af2d967c` |
| `boleta-sintetica.png` | `724a0c01ff80ff5b97bd34006d11e1d29dd9b728fe07f31eae03d73e1a61dd79` |

Los JUnit locales ignorados por Git identifican la repetición de la regresión: `regression.xml`, SHA-256 `9a35e85ff94b5707f394e401e8f3f382d459746c83a48e2c05bf4887bcc55dea` (378 casos, cero fallos u omitidos), y `frontend-junit.xml`, SHA-256 `9bf8ca88540e86720b1fc1a82ac95a84613c93f3e9c32f600f2fa7f707a7309e` (5 casos, cero fallos). Ambos están en `docs/quality/fase-7/evidence/RUN-EST-QA4-PDF-20261013/`; deben conservarse junto con la entrega técnica si se requiere auditar cada caso.

## Regresión

| Selección | Resultado |
| --- | --- |
| Evaluación, reportes y documentos: suites unitarias, API e integración sobre PostgreSQL 16 | **378 aprobadas**, cero fallidas; cuatro advertencias de deprecación Django. |
| `frontend/src/test/FinalGradeWindow.test.jsx` | **5 aprobadas**, cero fallidas. |
| Ruff `check` y `format --check` sobre los dos archivos Python modificados | Aprobados. |

La ejecución backend se hizo con `pytest -q --no-cov` sobre `test_evaluation_services.py`, `test_evaluation_api.py`, `test_evaluation.py`, `test_reporting_services.py`, `test_reporting_api.py`, `test_reporting.py`, `test_documents_services.py`, `test_documents_api.py` y `test_documents.py` en sus directorios `unit`, `api` e `integration`. No se afirma cobertura porcentual. El JUnit de los dos casos focales está en el directorio local ignorado `docs/quality/fase-7/evidence/RUN-EST-QA4-PDF-20261013/`; el PDF y su captura sí se adjuntan aquí para revisión.

**Estado de esta ejecución histórica:** corrección local y regresión aprobadas el 13 de octubre. Véase la actualización anterior para el estado del commit candidato. Esta ejecución verificó el endpoint de descarga, no un botón de producto.
