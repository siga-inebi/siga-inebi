# Regresión de evaluación, reportes y QA4-PDF-01 en el candidato

**Ejecución:** 14 de octubre de 2026, America/Guatemala. **Responsable:** Estuardo, con ejecución técnica asistida. **Revisión independiente:** Roí pendiente.

## Identidad del candidato

| Campo | Valor |
| --- | --- |
| Commit de `develop` probado | `7f04a945d09bf77c514cf7bfe988888f2e2bfd10` |
| CI/CD QA | [Run 38572348097](https://github.com/siga-inebi/siga-inebi/actions/runs/38572348097), aprobado |
| Revisión Cloud Run desplegada | `siga-inebi-qa-00019-64t`, 100 % del tráfico al finalizar el despliegue |
| Backend publicado | `sha256:991358e23d5128339069601265cd834630cf4251fc2c4ce6333629a340646bec` |
| Frontend publicado | `sha256:247ff12ee95a99cd75bf5d4d8e15b87a1c2b14c1873e330d090262f59f1d6c91` |
| Salud de base QA | `GET /api/v1/health/database/`: HTTP 200, `status=ok` el 14 de octubre |

El workflow compila ambas imágenes con `$GITHUB_SHA`, las publica por digest, ejecuta migraciones, actualiza Cloud Run y enruta todo el tráfico a la revisión nueva. El run vincula así el commit con la revisión desplegada. El control de salud no sustituye una prueba funcional autenticada.

## Regresión sobre ese código

Se ejecutó el árbol limpio del commit anterior en Docker Desktop con PostgreSQL 16. Se montó el código actual sobre una imagen de pruebas local con las mismas dependencias; el intento de reconstruirla se detuvo por un error de conexión a Docker Hub al solicitar `python:3.11-slim`. Las dependencias backend no cambiaron desde la imagen local. El CI/CD del mismo commit aprobó además `backend-tests`, `frontend-tests`, lint, build y la integración Docker.

| Control | Resultado | Evidencia |
| --- | --- | --- |
| Suites unitarias, API e integración de evaluación, reportes y documentos | **378 aprobadas**, 0 fallidas, 0 omitidas; 4 advertencias de deprecación Django | [JUnit backend](backend-regression.xml) |
| `FinalGradeWindow.test.jsx`: 59.5 → 60, 59.4 → 59, cero, sin nota y teclado | **5 aprobadas**, 0 fallidas | [JUnit frontend](frontend-regression.xml) |
| Descarga por `GET /api/v1/documents/historical-cycle-reports/` mediante cliente API de Django | HTTP 200, `application/pdf`, `attachment`; ciclo cerrado y permiso `document_issue` sintéticos | Pruebas API en JUnit backend |
| Integridad y lectura estricta de la boleta | `startxref` y offsets `xref` correctos; PyMuPDF 1.28.2: una página, `is_repaired=false` | [PDF nuevo](boleta-sintetica-candidata.pdf) y [captura renderizada](boleta-sintetica-candidata.png) |
| Coherencia de notas y condición | Unidad 1: 59; unidad 2: 60; nota final: 60; aprobado; promovido | PDF, captura y prueba API |

El comando backend ejecutó `pytest -q --no-cov` sobre los nueve módulos `test_evaluation_*`, `test_reporting_*` y `test_documents_*` de `tests/unit`, `tests/api` y `tests/integration`. Se guardó el JUnit con `--junitxml`. Vitest ejecutó `src/test/FinalGradeWindow.test.jsx` y exportó su JUnit. No se atribuye una cobertura porcentual a esta selección.

| Archivo | Bytes | SHA-256 |
| --- | ---: | --- |
| `backend-regression.xml` | 54 411 | `caf73c02fed883e57fdfec714b894fedbed3b5f3950d62bd47791f2c836a2554` |
| `frontend-regression.xml` | 1 254 | `8d987cbe991cc1dd6156f3f91ac4180a0d70ada794d13aa436d049c93c8e24cc` |
| `boleta-sintetica-candidata.pdf` | 1 075 | `fbe941c523cf4314ae6905aa5ee6a4827cd72d6147014636746e41c99ab78412` |
| `boleta-sintetica-candidata.png` | 35 755 | `c262dc9a8e147f1fbcd5d6f57c8d570b749444719e582f3fbaf580ee08212be4` |

Se usaron solo factories y datos sintéticos; no se incluyeron credenciales ni respuestas autenticadas de QA. La captura se inspeccionó visualmente.

## Límite para el cierre formal

La descarga funcional anterior se ejecutó **contra el código candidato en PostgreSQL local**, por cliente API, no con una cuenta dentro del servicio Cloud Run. El 14 de octubre Estuardo confirmó acceso a QA con la cuenta sintética `qa-admin` (`GET /api/v1/auth/me/`: HTTP 200, `authenticated=true`). Ese endpoint no expone permisos. Estuardo informó que no existe un ciclo cerrado en QA; la matrícula mostrada en el historial consultado corresponde a un ciclo activo. Por tanto, no se pudo ejecutar la descarga de una boleta de ciclo cerrado en ese entorno ni adjuntar un PDF obtenido de QA. Queda pendiente preparar una matrícula sintética de ciclo cerrado en un entorno disponible, repetir allí la descarga y verificar el archivo. También queda pendiente el dictamen independiente de Roí sobre QA4-PDF-01 e INC-008. Hasta entonces el hallazgo está corregido técnicamente y desplegado, pero la validación funcional autenticada en QA no se da por aprobada.
