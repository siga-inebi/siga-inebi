# Reporte técnico de API, documentos y auditoría — aporte de Roí

**Fase:** 7
**Base verificada:** `develop` en `5ed5fd24d02f494053c53dbbbafe50a8412534e5`
**Fecha de ejecución:** 2026-10-13
**Rama de documentación:** `docs/roi-documents-phase7-evidence`
**Responsable:** Roí
**Datos:** factories y archivos sintéticos; no se utilizaron datos institucionales reales.

## 1. Alcance y criterio de cierre

Este documento es el anexo de evidencia de Roí para contratos API, documentos,
descargas, emisión, auditoría y recuperación. El contrato general permanece en
[Manual 07 — API e integraciones](../../manuals/07-api-integrations-documentation.md).
Aquí se vinculan los endpoints con sus pruebas ejecutables y se separa lo que ya
está verificado en `develop` de lo que depende de una revisión externa o del
PR #595.

No se marca QA4-PDF-01 como cerrado únicamente por la fusión del código. La
corrección de offsets `xref`/`startxref` y su prueba estricta pertenecen al
[PR #595](https://github.com/siga-inebi/siga-inebi/pull/595), fusionado en
`b4b0d40c49ab29e75dc41fb34a2fbd69eb466757`. La revisión de Roí quedó
registrada directamente en ese PR con cambios solicitados porque la evidencia
no fijaba el SHA desplegado en QA y `backend-lint` estaba fallando al momento
de la fusión.

## 2. Matriz de contratos verificables

| Contrato | Respuesta esperada | Controles de seguridad/auditoría | Evidencia automatizada |
| --- | --- | --- | --- |
| `POST /api/v1/documents/records/` | `201` con identificador público y metadatos de la versión | permiso `document_upload`, tipo/tamaño permitidos, auditoría de alta | `test_document_record_upload_success_and_audited`; rechazos de MIME, tamaño y permiso en `backend/tests/api/test_documents_api.py:471-530` |
| `POST /api/v1/documents/records/scan/` | `201` con registro de documento digitalizado | permiso `document_upload`, checksum y auditoría | `test_scanned_document_upload_success_and_audited`; rechazo de alcance en `:559` |
| `GET /api/v1/documents/records/{public_id}/download/?token=...` | `200`, binario del archivo y `Content-Disposition: attachment` | token breve, ligado al actor, de un solo uso; rechazo de ausente, inválido, vencido o de otro actor | `backend/tests/api/test_documents_api.py:174-355`; servicios y auditoría en `backend/tests/unit/test_documents_services.py:1040-1140` |
| `POST /api/v1/documents/records/{public_id}/verify/` | `200` con resultado de integridad | permiso y alcance del estudiante; detección de payload alterado; auditoría | `backend/tests/api/test_documents_api.py:357-437` |
| `GET /api/v1/documents/official-issuance/eligibility/?enrolment_id=...` | `200` con decisión y códigos de bloqueo | permiso `document_issue`; matrícula/documentos obligatorios; auditoría de permitido, bloqueado o denegado | `backend/tests/unit/test_documents_services.py:230-330`; API en `backend/tests/api/test_documents_api.py` alrededor de `:1010-1075` |
| `GET /api/v1/documents/historical-cycle-reports/?enrolment_id=...` | `200`, `application/pdf`, adjunto con notas, condición y promoción | ciclo cerrado, permiso de emisión, lectura de resultados congelados; auditoría de compilación | `backend/tests/api/test_documents_api.py:1081-1168`; integración en `backend/tests/integration/test_documents.py:108-150` |
| `GET /api/v1/documents/verify/{code}/` | `200` con autenticidad mínima del documento portado | endpoint público con rate limit; no expone datos sensibles | `test_document_verification_*` en `backend/tests/api/test_documents_api.py`; contrato en Manual 07 §4.2 |
| `GET /api/v1/audit/events/` y `GET /api/v1/audit/events/export/` | listado filtrable o CSV | permiso `audit_read`; exportación también auditada; endpoints de escritura rechazados | `backend/tests/api/test_audit_api.py:94-153,341-353`; `backend/tests/integration/test_audit.py:42-120` |

La ruta de lectura de documentos del expediente también conserva el alcance y
la auditoría de lectura: `backend/tests/api/test_audit_api.py:355-402`.
Las respuestas de error usan el sobre común documentado en Manual 07 §3.3;
no se introduce un contrato público nuevo en este cierre.

## 3. Ejecución reproducible en `develop`

Comando ejecutado desde `backend/`:

```text
\.venv\Scripts\python.exe -m pytest tests/api/test_documents_api.py tests/unit/test_documents_services.py tests/integration/test_documents.py tests/api/test_audit_api.py tests/unit/test_audit_services.py tests/integration/test_backup_and_recovery.py --no-cov -q -rs
```

Resultado observado:

```text
244 passed, 23 skipped, 5 warnings in 25.82s
Exit code: 0
```

Los 23 `skip` corresponden al entorno local: falta `sh` para el simulacro
protegido y no están disponibles `pg_dump`, `pg_restore` ni los clientes de
PostgreSQL. No se convierten en aprobaciones implícitas. Las cuatro pruebas de
integridad documental posterior a restauración sí están implementadas en
`backend/tests/integration/test_backup_and_recovery.py:521-628` y quedan
cubiertas cuando se ejecutan en el entorno PostgreSQL/Unix requerido.

## 4. QA4-PDF-01 y evidencia del documento final

El PR #595, ya fusionado, agrega la regresión específica que inspecciona que
`startxref` apunte al `xref` real y que cada objeto PDF esté en el offset anunciado,
además de comprobar las notas sintéticas 59 y 60, nota final 60, aprobación y
promoción. Esa prueba no se replica aquí porque el cambio de generación aún no
forma parte de la base `develop` de esta rama.

Para aceptar la evidencia final todavía deben quedar registrados en el expediente:

1. SHA exacto de la revisión desplegada en QA.
2. Resultado del test QA4-PDF-01 sobre ese SHA, con PDF y captura o reporte de
   lector estricto.
3. Corrección de los errores `E501` e `I001` reportados por `backend-lint`.
4. Revisión independiente posterior a la resolución de los puntos anteriores.

Hasta cumplir esos cuatro puntos, la matriz debe conservar la distinción entre
"prueba automatizada preparada" y "evidencia final aceptada".

## 5. Recuperación y límites de esta evidencia

La verificación de almacenamiento documental posterior a restauración ya fue
aportada en PR #572 como `CP-INT-REC-001`. Este reporte la referencia, pero no
la presenta como un simulacro completo de recuperación: la restauración de
PostgreSQL, el almacenamiento de archivos y el cambio de tráfico son controles
distintos. El informe vigente es
[informe-recuperacion.md](informe-recuperacion.md).

La aceptación institucional, la sesión UAT con usuarios y el video manual no
pueden certificarse mediante pruebas automatizadas de esta rama. Requieren
participantes y evidencia externa identificable; no se fabrican resultados.

## 6. Pendientes para la entrega

- Estuardo: completar la evidencia de QA del código ya fusionado en #595 y
  resolver o referenciar de forma trazable el `backend-lint` que falló.
- Revisor independiente: confirmar la revisión del PDF generado y su evidencia.
- Daniel/Ops: ejecutar el simulacro de recuperación en el entorno con clientes
  PostgreSQL y almacenamiento de archivos disponible.
- Responsables de UAT: registrar participantes, fecha, casos ejecutados,
  resultado y decisión institucional.

Con este anexo quedan documentados los contratos y las pruebas que Roí puede
verificar en código. No se declara cierre total mientras permanezcan los
pendientes externos anteriores.
