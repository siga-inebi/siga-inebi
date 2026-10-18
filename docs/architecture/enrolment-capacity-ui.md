# Cupo visible al matricular — M7

Entrega del issue #632, M7 y consumo contextual de S5 de `docs/ux-ui.md`.
Expone RF-EST-008 y conserva RF-MAT-004. La revisión, integración a `develop` y
aceptación institucional se registran por separado.

## Comportamiento

- Nueva matrícula, reinscripción individual y matriculación inicial por lotes
  muestran **Cupo de la sección** al elegir ciclo y sección. Antes se muestra una
  indicación y no se consulta ocupación.
- Se presentan `capacity`, `occupied_seats` y `available_seats` del servidor.
  No se resta cupo en React ni se estima con la lista de estudiantes.
- `capacity=0` y `available_seats=null` significan **Sin límite declarado**;
  `available_seats=0` significa **Sección sin vacantes**. Una respuesta vacía o
  un error no se convierten en cero vacantes.
- Se consulta una sola sección del ciclo elegido; cambiar selección no conserva
  datos de la anterior. No se muestran respuestas tardías de otro contexto.
- **Actualizar cupo** consulta de nuevo. El error ofrece **Reintentar cupo**,
  sin cerrar el formulario ni repetir automáticamente la solicitud fallida.
  Un error de actualización tampoco deja visibles datos viejos.
- La lectura se renueva al abrir el contexto y al terminar un envío que deja la
  ventana abierta (rechazo individual o resultado de lote). Durante el envío no
  se muestra la lectura anterior como disponibilidad actual ni se permite
  actualizar. El cierre después de un alta individual exitosa se conserva.
- El aviso no reserva vacantes ni autoriza una inscripción. El servicio del
  servidor sigue validando al guardar; no se bloquea el envío desde React a
  partir de una lectura que puede haber cambiado.
- Los lotes iniciales conservan resultados parciales y validación por alumno;
  no se modifica su contrato ni se introduce una regla de cupo de lote en la UI.

## Contrato y arquitectura

Se consume el endpoint existente
`GET /api/v1/enrolments/sections/occupancy/?academic_cycle_id={uuid}&section_id={uuid}`.
No se descarga el padrón ni todas las ocupaciones. Se conservan ruta, campos,
autorización y validación existentes. No hay cambios de backend productivo,
migraciones, permisos, dependencias ni variables de entorno nuevas.

React Query usa una clave explícita de ciclo/sección:
`queryKeys.enrolments.occupancy`. Se exige lectura fresca al montar/reabrir y
reactivar tras un envío; los datos en caché se ocultan durante la actualización.
No hay sondeo periódico ni recarga por cambiar de pestaña del navegador. La
escritura puede rechazar una disponibilidad que era válida al consultar.

`EntityFormWindow` incorpora una extensión aditiva de presentación: `children`
admite contenido o `(values, {submitting}) => contenido`, debajo de los campos.
No altera `fields`, normalización, errores ni envío. El componente compartido
no conoce matrículas ni aplica reglas de cupo.

ADR aplicables: ADR-0002 (monolito modular), ADR-0004 (REST), ADR-0005
(autorización) y ADR-0008 (capas). Las reglas permanecen en el servicio/modelo
de ocupación y en el guard de escritura existente.

## Pruebas

- `frontend/src/test/SectionOccupancyNotice.test.jsx`: selección, valores del
  servidor, lleno/sin límite, ausencia de información, otro contexto, errores,
  reintento, respuesta tardía, reapertura y actualización después de operación.
- `frontend/src/test/newModulePages.test.jsx`: nueva matrícula, reinscripción,
  rechazo conservando formulario y actualización después de lote. También
  ejercita la extensión contextual del formulario compartido.
- `frontend/src/test/moduleServices.test.js`: parámetros GET.
- `backend/tests/api/test_enrolment_capacity_ui_contract.py`: disponible/lleno,
  liberación por estado retirado, sección sin límite y rechazo al guardar si
  otra inscripción consumió la última vacante después de consultar.

No se agrega una pantalla general de ocupación ni se cambia M2, M6 o el contrato
de los flujos masivos.
