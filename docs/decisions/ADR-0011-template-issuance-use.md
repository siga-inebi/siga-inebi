# ADR-0011: aporte D7, uso explícito de plantillas para emisión

## Estado y alcance

Aceptada para D7 por `docs/ux-ui.md`, sección 3, e implementada en la entrega PL1/PL2/PL5
del issue #632. Este archivo aporta D7 al ADR-0011; la consolidación de D1–D10 pertenece a
#630. No documenta como implementadas las decisiones restantes, incluido el editor rico D4.

## Contexto

La emisión individual buscaba una plantilla por códigos de tipo reservados: `constancia` y
`certificate`. Era una regla invisible y el catálogo inicial ni siquiera incluía `constancia`.
La restricción de una plantilla activa por tipo impedía clasificar varias plantillas igual.

## Decisión

- Cada plantilla declara `issuance_use`: `none`, `enrolment_certificate` o `study_certificate`.
  «Ninguna» permite crear plantillas sin asociarlas a una emisión automática.
- Como máximo hay una plantilla activa por institución y uso distinto de `none`.
  El tipo documental conserva su catálogo institucional y queda como clasificación.
- La emisión individual selecciona por uso, nunca por código de tipo.
- Si no hay plantilla activa, versión publicada o contenido publicado, se conserva el texto
  predeterminado y Plantillas muestra el aviso de fallback correspondiente.
- Reemplazar exige confirmar el UUID exacto de la plantilla activa. Crear/actualizar y
  desactivar la anterior suceden en una transacción; si falla código, validación o versión,
  se revierte todo. Un cambio concurrente del ocupante exige nueva confirmación.
- Se conserva la plantilla anterior, sus versiones y las emisiones históricas vinculadas.
  El nuevo uso se registra también en cada versión nueva y en auditoría.

## Concurrencia y privacidad

Los servicios de crear, actualizar y desactivar bloquean primero la institución y después la
plantilla cuando corresponde. Esto serializa cambios del catálogo institucional, incluso cuando
todavía no existe un ocupante que bloquear. Una restricción única parcial de PostgreSQL refuerza
la invariante. No se introduce una política de autorización nueva: se mantienen sesión, institución
y `scope_assign` con alcance institucional para las escrituras del catálogo.

La consulta de disponibilidad devuelve dos usos y metadatos mínimos de sus plantillas activas.
La vista previa recibe datos sintéticos completos y usa el mismo sustituidor seguro de marcadores
que la emisión; esta entrega conserva la salida de texto y no implementa el motor PDF de D4.

## Migración y compatibilidad

`documents.0016_template_issuance_use` asigna el uso correspondiente a las plantillas activas
de tipos `constancia` y `certificate`. Las demás, incluidas las desactivadas, reciben `none`.
Las versiones anteriores incorporan el metadato equivalente según su código histórico de tipo;
no se reescriben contenido, secuencia, nombres, fechas, identificadores ni referencias de emisión.

Las altas nuevas que omiten el uso reciben `none`; no se infiere a partir del tipo. PATCH que
omite el campo conserva el uso actual. Los consumidores que quieran destinar una plantilla nueva
a una emisión deben enviarlo explícitamente. El helper interno legado que consulta por tipo se
conserva para compatibilidad, pero falla si el tipo tiene varias activas y no interviene en emisión.

La reversión comprueba que no haya varias activas del mismo tipo antes de restaurar la restricción
anterior. Si hay conflictos requiere desactivarlos explícitamente; no elimina ni desactiva historia
de forma automática. Las migraciones de prueba verifican contenido y referencias conservados.

## Requerimientos y evidencia

RF-PLA-007 conserva su ID y cambia de unicidad por tipo a unicidad por uso. RF-PLA-008 registra
el uso explícito, migración y aviso de fallback. RF-PLA-002/006 y RF-EMI-001 se verifican en las
regresiones de marcadores completos y selección independiente del tipo. RF-PLA-005 mantiene
versiones inmutables. El catálogo y la matriz describen el alcance verificable y lo pendiente.
