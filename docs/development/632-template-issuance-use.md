# Issue #632: PL1, PL2 y PL5 de plantillas

## Alcance

Esta entrega implementa el uso explícito de emisión decidido en D7, su migración desde códigos
legados, el reemplazo confirmado de plantilla activa y datos de muestra completos en vista previa.
Incluye la explicación de TD1: el tipo documental solo clasifica.

Rama `fix/632-template-purpose`, creada desde `develop` actualizado a `5f8630d`, independiente de
los PR #633–#636. El aporte D7 del [ADR-0011](../decisions/ADR-0011-template-issuance-use.md) queda
listo para la consolidación de decisiones a cargo de #630. El catálogo incorpora RF-PLA-008 y
actualiza el significado de RF-PLA-007 conservando su ID, conforme a `change-control.md`.
Entrega: [PR #637](https://github.com/siga-inebi/siga-inebi/pull/637), con base `develop`.
Sus checks de integración complementan la evidencia local de este documento.

## Cambios observables

- La tabla y los formularios muestran «Se usa para»: Ninguna, Constancia de inscripción o
  Certificado de estudios. El historial muestra el uso de la versión.
- El selector identifica usos ocupados y la plantilla activa. Reemplazar exige marcar la
  confirmación de esa plantilla; se conserva la anterior y sus versiones.
- Ante una confirmación obsoleta se relee la disponibilidad. La nueva ocupante no hereda el
  consentimiento y el borrador conserva nombre, descripción y contenido.
- La pantalla avisa si la emisión utiliza texto predeterminado, incluso cuando existe plantilla
  activa pero no contiene una versión publicada con contenido.
- Vista previa aporta las ocho etiquetas, incluidos código, ciclo, sección y fechas sintéticas.
  Se sustituyen también marcadores escritos con espacios, por ejemplo `{{ student.code }}`.

## Diseño y contratos

Las reglas están en `apps/documents/services.py`; modelos y restricción parcial refuerzan la
unicidad. Los servicios bloquean institución y plantilla en orden consistente. El catálogo de
disponibilidad vive en `queries.py` y usa una subconsulta para obtener contenido de la última
versión; nunca descarga todo el historial ni todas las páginas de plantillas.

Las vistas y serializadores solo validan/adaptan HTTP. El formulario reutiliza `FloatingWindow`,
`FormSelect` y `FormTextField` con `useState`. Captura el UUID confirmado y no introduce reglas
de selección de emisión en React: el servidor vuelve a comprobar toda la operación.

Se mantienen permisos existentes del catálogo y emisión, encabezado obligatorio y marcadores
cerrados. No se agregan datos reales, secretos, dependencias ni variables de entorno.

El [contrato API](../architecture/api-conventions.md#uso-de-emisión-de-plantillas-632-d7) define
valores, omisión, confirmación, errores, disponibilidad y compatibilidad. Un cliente anterior que
creaba una plantilla de tipo `certificate` debe enviar `issuance_use=study_certificate` si quiere
asociarla a certificados nuevos. Omitir el campo en PATCH conserva su valor.

## Migración y despliegue

`documents.0016_template_issuance_use`:

1. Retira la unicidad de activas por tipo.
2. Agrega el campo a plantilla y versión.
3. Asigna Constancia a las activas de tipo `constancia`, Certificado a las de `certificate` y
   Ninguna a las demás. Añade a versiones legadas el uso equivalente a su tipo histórico.
4. Crea la unicidad parcial de activas por institución y uso distinto de Ninguna.

No se reescriben campos históricos previos ni se cambia el enlace de emisiones a versiones.
El metadato deducido de versiones legadas indica el destino del antiguo código; no prueba que
una versión concreta haya sido emitida. Los nombres, contenido, secuencias y fechas conservan
sus valores originales.

Ejecutar la migración y desplegar backend/frontend de esta entrega en la misma ventana; evitar
operar el catálogo con versiones mezcladas durante la transición. Los servidores locales de las
otras ramas no deben usar esta preview como reemplazo de sus contratos.

```bash
python manage.py migrate
python manage.py makemigrations --check --dry-run
```

Reversión: antes de volver a `documents.0015_documentissuance`, desactivar explícitamente las
plantillas que produzcan varias activas del mismo tipo. El guard de reversión rechaza esos casos
con una instrucción y no modifica datos para resolverlos automáticamente. Después puede revertirse
el código. No borrar plantillas, versiones ni emisiones para forzar una reversión.

## Verificación

Pruebas nuevas de backend:

- `tests/unit/test_template_issuance_use.py`: clasificación independiente, omisión, unicidad,
  ocupante obsoleto, rollback, historial, institución y consulta acotada de disponibilidad.
- `tests/api/test_template_issuance_use_api.py`: contrato HTTP, permisos, disponibilidad y las
  ocho etiquetas con espacios, sin publicar versiones desde vista previa.
- `tests/integration/test_template_use_concurrency.py`: dos publicaciones y dos reemplazos
  concurrentes; solo una operación gana el uso.
- `tests/migrations/test_documents_0016_template_use.py`: datos legados conservados y guard de
  reversión que exige resolver conflictos de clasificación explícitamente.
- La regresión de emisión individual ahora usa un tipo arbitrario (`report`) y destino explícito,
  demostrando que se conserva la versión utilizada y que el código de tipo deja de decidir emisión.

Frontend: `TemplateIssuanceUse.test.jsx` comprueba uso visible, fallback, consentimiento por UUID,
confirmación obsoleta con borrador conservado, edición y recuperación de errores de disponibilidad.
`templateUseService.test.js` comprueba el endpoint acotado. La vista previa envía las ocho muestras
sin crear ni actualizar plantillas, y `newModulePages.test.jsx` conserva las regresiones existentes.

Desde `backend/`, con PostgreSQL configurado según `local-setup.md`:

```bash
python -m pytest --create-db --reuse-db -q
python -m ruff check apps tests
python -m ruff format --check apps tests
python -m bandit -q -r apps/documents -x migrations
python manage.py spectacular --validate --file /ruta/temporal/openapi.yml
```

Desde `frontend/`:

```bash
npm run test:coverage -- --maxWorkers=1 --no-file-parallelism
npm run lint
npm run format:check
npm run build
```

Resultados locales del 17 de octubre de 2026:

| Comprobación | Resultado |
| --- | --- |
| Backend completo con base automática recreada | 1.804 aprobadas, 23 omitidas; cobertura 95,17 %, incluidas 28 pruebas nuevas |
| Frontend completo | 316 aprobadas en 38 archivos; cobertura de líneas 85,20 %, incluidas 7 pruebas nuevas |
| Herramientas de requerimientos | 49 pruebas aprobadas |
| Ruff y formato backend; Bandit de documents | Aprobados |
| ESLint y Prettier; build y presupuestos frontend | Aprobados; carga inicial 221.564/230.000 bytes gzip |
| Detección de migraciones | Sin cambios adicionales a 0016 |
| OpenAPI | Cero errores; 27 advertencias (23 únicas), igual a la base comparada con #633 |
| HTTP de preview | Login, catálogo y vista previa correctos; ocho etiquetas sustituidas, reemplazo sin confirmar 400, confirmado creado e historial conservado |

La primera suite completa de frontend detectó un mock de navegación que respondía con el sobre
de salud de API al nuevo endpoint de disponibilidad. Se ajustó al contrato de arreglo y la suite
completa pasó. No se cambió el contrato para acomodarlo a ese mock.

Entorno local existente: PostgreSQL 18.3, Python 3.11.3 / Django 5.2.17 y Vitest 3.2.7. Sus versiones
difieren de las fijadas; CI valida el entorno fijado. Docker y revisión visual en navegador
automatizado no se ejecutaron localmente para esta entrega.

Preview: `http://127.0.0.1:5176/app/plantillas`, backend `127.0.0.1:8004`, sobre una base nueva
`siga_inebi_templates_preview` migrada y poblada únicamente con `seed_demo_data` y plantillas
sintéticas. No se copió ni migró la base de las otras instancias locales.

## Pendientes explícitos

D4 y PL3/PL4/PL6/PL7/PL8/PL9/PL10/PL11 se completan en el PR #666. TD2 y DO1–DO3 siguen pendientes. Esta entrega no crea
editor enriquecido ni motor PDF nuevo, no ofrece vista previa antes de guardar, no restaura
versiones y no agrega emisión por lotes. RF-PLA-006 conserva su estado parcial.

La consolidación completa de ADR-0011 y la base compartida de listados pertenecen a #630.
No se marca el issue #632 completo ni se integran automáticamente los PR anteriores.
