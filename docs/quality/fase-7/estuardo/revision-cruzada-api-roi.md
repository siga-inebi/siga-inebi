# Revisión cruzada del Manual 07: API e integraciones

Fecha: 12 de octubre de 2026. Revisor: Estuardo. Responsable del manual: Roí.
Alcance: contraste documental de ejemplos y afirmaciones con el código disponible
en la rama de trabajo. No representa una aceptación institucional ni una
validación exhaustiva de todos los endpoints.

## Correcciones aplicadas

| Hallazgo | Evidencia | Corrección |
| --- | --- | --- |
| UUID presentado como v4 tenía versión 7 | El grupo de versión del ejemplo comenzaba con `7`; `common.models` genera UUID con `uuid.uuid4`. | Se cambió el ejemplo a UUID versión 4. |
| Paginación anunciaba 20 por página y máximo configurable de 100 | `backend/config/settings/base.py` configura DRF `PAGE_SIZE: 25` y no establece clase o máximo personalizado. | Se documentó el valor predeterminado actual de 25 y la ausencia de máximo personalizado. |
| Ruta de boleta figuraba en singular | `backend/apps/documents/api/urls.py` registra `historical-cycle-reports/`. | Se corrigió la ruta a `/api/v1/documents/historical-cycle-reports/`. |
| Ejemplo de carga declaraba 245,890 bytes con el SHA-256 del contenido vacío | El digest incluido es `e3b0…b855`, hash estándar de cero bytes. | El ejemplo ahora omite el contenido y declara `size_bytes: 0`, aclarando la correspondencia del hash. |
| Ejemplos usaban dominio institucional y datos personales plausibles | El manual tenía un dominio institucional y nombre, correo y CUI con formato real. | Se sustituyó el host por `api.example.invalid`, el correo por un dominio reservado y se eliminó el CUI. |
| Generalización de 429 a todos los endpoints públicos | La configuración define `document_verification: 20/min` y `DocumentVerificationView` aplica ese throttle. | Se acotó la afirmación a la verificación pública de documentos y a 20 solicitudes por minuto por IP. |
| Cliente CSRF descrito como axios o fetch | `frontend/src/shared/api/apiClient.js` usa `fetch`. | Se documentó el cliente existente `fetch`. |

## Hallazgo pendiente del responsable del dominio

La corrida manual de Estuardo en
[`ronda-4/README.md`](ronda-4/README.md) obtuvo HTTP 200 y `application/pdf`
del endpoint correcto para una matrícula sintética. Sin embargo, PyMuPDF reportó
`is_repaired=true` y `cannot recognize xref format`; la descarga desde la interfaz
también quedó bloqueada porque no se encontró acción frontend para esta ruta.
Esto confirma que la respuesta HTTP por sí sola no demuestra un PDF utilizable.

La corrida registra los offsets `xref`/`startxref` constantes como posible causa,
no como diagnóstico confirmado. No se modificó el generador ni se declara resuelto
QA4-PDF-01. Roí debe revisar el hallazgo, confirmar la causa y documentar una
corrección y validación independientes antes de que el manual describa el PDF como
válido para el usuario final.

## Límites y pendientes

- Se contrastaron las discrepancias enumeradas; el catálogo completo de endpoints,
  permisos, respuestas y efectos de auditoría aún requiere revisión contractual
  endpoint por endpoint contra OpenAPI y las vistas/serializadores.
- El video de usuario ya fue elaborado según confirmación de Estuardo. Aún falta
  registrar su ubicación accesible, el alcance de módulos/roles, el SHA-256 final
  y la revisión independiente en el seguimiento de manuales.
- No se incorporaron datos reales, credenciales ni artefactos del entorno de QA.
