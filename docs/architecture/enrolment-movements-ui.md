# Movimientos de matrícula: primera entrega de M3 (#632)

## Alcance y reglas revisadas

Esta entrega conecta la interfaz a cambio de sección (RF-MOV-002), retiro formal
(RF-MOV-004) y anulación (RF-MOV-008), conservando fechas oficiales y de registro
separadas (RF-MOV-003). Revisa AGENTS.md, los requerimientos canónicos y
ADR-0004/0005/0006/0008. No modifica las reglas de permanencia, promoción, cupo,
autorización o auditoría de los servicios existentes.

M3 permanece parcial: traslado de ingreso y de egreso se entregan en otro PR.
La propuesta 1.5 se aplica al flujo de movimientos mediante formulario y revisión
en línea dentro de una sola ventana; no se declara completa la ruta de expediente
con pestañas ni la reorganización de requisitos documentales.

## Recorrido de usuario

- En **Matrículas → Vigentes**, abrir **Movimientos de matrícula** desde una fila.
  La ventana conserva el estudiante y el contexto académico de esa matrícula.
- **Historial** consulta páginas del estudiante y distingue fecha de vigencia,
  fecha de registro, motivo y estado de anulación.
- **Registrar movimiento** permite elegir cambio de sección o retiro. Solicita
  fecha de vigencia; el retiro exige además una causa no vacía.
- El cambio consulta secciones del ciclo y grado de origen en servidor. No agrega
  descargas globales de secciones o estudiantes.
- **Revisar movimiento** muestra destino, fecha y motivo antes de confirmar.
  Cambiar cualquier campo invalida la revisión. No abre otra ventana.
- La escritura ocurre únicamente al confirmar y bloquea cierre, edición, cambio
  de pestaña y doble envío mientras se procesa.
- Los errores conservan los campos y exigen revisar de nuevo. Se refrescan las
  listas y el historial para poder comprobar un resultado incierto; no hay
  reintentos automáticos de escrituras.
- Tras una escritura correcta, se vuelve al historial y se refresca la tabla.
  Para otra operación sobre la matrícula debe abrirse nuevamente desde la lista
  actualizada, evitando operar con el contexto anterior.

La entrada **Movimientos** de cabecera y las filas históricas permiten consultar
y solicitar anulaciones, pero requieren abrir una matrícula vigente para registrar
otro cambio o retiro. No se selecciona una matrícula activa de forma implícita.

## Anulación y conservación de historia

Cuando el dominio indica que el tipo admite anulación y el movimiento no está
anulado, su fila ofrece **Anular movimiento**. La captura y confirmación exigen
motivo y siguen dentro de la misma ventana. El historial mantiene el movimiento
original y muestra motivo y fecha de la corrección.

`GET /api/v1/enrolments/movements/` agrega el booleano de solo lectura
`supports_annulment`. Indica únicamente que el **tipo** tiene un caso reversible
implementado: retiro o cambio de sección. Traslados devuelven `false`. No es una
concesión de permisos ni una garantía de que el estado actual permita anular.
El servicio de escritura reutiliza esa misma propiedad del modelo; React no
contiene una lista propia de tipos reversibles. Los campos existentes permanecen
compatibles y no requiere migraciones.

Las anulaciones se cargan con `select_related` en la consulta del historial. La
serialización de 25 movimientos, con y sin corrección, se verifica con una sola
consulta; no agrega una consulta por fila para resolver la relación inversa.

## Escrituras y autorización

| Operación | Endpoint y payload |
| --- | --- |
| Cambio de sección | `POST /enrolments/{enrolment_id}/section-change/`: `new_section_id`, `effective_on` |
| Retiro | `POST /enrolments/{enrolment_id}/withdrawal/`: `reason`, `effective_on` |
| Anulación | `POST /enrolments/movements/{movement_id}/annulment/`: `reason` |

Las rutas llevan el prefijo `/api/v1`. Las dos primeras identifican una matrícula;
la tercera identifica el movimiento, nunca el UUID de la matrícula.

Se conserva `enrollment_update` con alcance sobre las secciones afectadas y la
validación central de ciclos y estados. La API sigue siendo la autoridad. Los
controles de captura no otorgan permisos: un rechazo se muestra sin descartar el
borrador. El GET del historial conserva su requisito de sesión existente; este
PR no redefine esa política de lectura.

El retiro utiliza el servicio que cierra permanencia y revoca acceso/credencial;
la anulación conserva su corrección auditable y las restauraciones existentes.
No copia notas, reasigna asistencias, borra historia ni crea nuevos tipos de
movimiento. No resuelve la decisión pendiente sobre ejecución futura de
movimientos: conserva las validaciones de cada endpoint.

## Verificación reproducible

Solo datos sintéticos; PostgreSQL como motor de prueba:

```powershell
python -m pytest --reuse-db --no-cov -q tests/api/test_movement_ui_contract.py tests/api/test_enrolments_api.py tests/unit/test_enrolments_services.py tests/integration/test_enrolments.py
npm exec vitest -- run src/test/enrolmentMovements.test.jsx src/test/newModulePages.test.jsx src/test/moduleServices.test.js --maxWorkers=1 --no-file-parallelism
```

Pruebas nuevas de contrato: cuatro tipos, alcance exacto del booleano aditivo y
carga del historial sin consultas por fila. La regresión existente cubre permiso,
alcance, ciclos, efectos de permanencia, historial, inmutabilidad y anulación.

Frontend verifica revisión obligatoria, filtros remotos del selector, UUID correcto
por operación, fecha/causa requeridas, invalidación al editar, preservación ante
rechazos, confirmación dentro de un solo diálogo, paginación de anulaciones,
recarga y bloqueo del cierre durante una escritura. Prueba además el acceso desde
una fila de Matrículas y los contratos HTTP de los tres métodos.

## Integración y reversión

Evidencia local del 17 de octubre de 2026: backend completo, 1.781 pruebas
aprobadas y 23 omitidas, con 95,15 % de cobertura; frontend completo, 319 pruebas
en 37 archivos, con 85,83 % de líneas. Tras ajustar la reutilización del contexto
visual de la tabla, la selección de 71 pruebas de pantallas, movimientos y
servicios volvió a aprobar. Ruff, ESLint, formato, build con presupuesto, Bandit,
comprobación de migraciones y 49 pruebas de herramientas de requerimientos
aprobados. OpenAPI conserva 27 advertencias de base y no presenta errores.

Entorno nativo: PostgreSQL 18.3, Python 3.11.3, Django 5.2.17 y Vitest 3.2.7;
las dependencias fijadas y Docker se verifican mediante los checks del PR.
La prueba HTTP por el proxy de `5178` ejecutó cambio/anulación y retiro/anulación,
verificó salida y retorno a la lista activa y comprobó que se conservaran ambos
movimientos con sus correcciones. Se usó solo la base sintética aislada
`siga_inebi_movements_preview`, sin alterar las otras previews. No se presenta
esta prueba como revisión visual automatizada.

Rama creada desde `develop` actualizado (`5f8630d`), con destino `develop`.
No incorpora los commits de PR anteriores ni infraestructura nueva de listas del
#630. M1 (#636), reinscripción masiva (#638), traslados, promoción y el expediente
completo conservan su alcance separado.

Sin migraciones ni variables de entorno nuevas. Para revertir, retirar la UI y
revertir el código; no eliminar matrículas, movimientos, correcciones o eventos
de auditoría ya registrados. El campo de lectura es aditivo y los endpoints de
escritura mantienen sus contratos.
