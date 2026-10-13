# Cierre documental D2 — identidad, autorización y seguridad

Fecha de cierre documental: 12 de octubre de 2026.
Responsable: Santiago.

## Resultado

D2 queda **completado para la línea base evaluada**, sin constituir aceptación
del candidato final. Se ejecutaron positivos y negativos de autenticación,
sesiones, CSRF, múltiples roles, permiso sin alcance y acceso a estudiantes
ajenos. También se comprobó la persistencia de los cambios de autorización y
la auditoría aplicable.

## Evidencia

| Ejecución | Cobertura | Resultado |
| --- | --- | --- |
| `EJ-D1-037` | Identidad, autorización, roles, permisos y alcances backend | 158 pruebas aprobadas |
| `EJ-D1-038` | Login, logout, sesiones, bloqueo y cambio de clave frontend | 33 pruebas aprobadas |
| `EJ-D1-041` | CSRF, acceso propio/ajeno, pérdida inmediata de alcance e historia del vínculo | Aprobada; 28 comprobaciones confirmadas por Diana en PR #586 |

La revisión independiente detectó `INC-IDENT-001`: tres rechazos sensibles
HTTP 403 no dejaban asiento. El hallazgo no invalida los resultados funcionales
de D2; se trasladó correctamente a corrección y regresión en D4.

## Límites

- La evidencia corresponde a los SHA registrados en `ejecuciones.csv`, no al
  candidato final.
- Los casos condicionados y las decisiones PD-004/PD-005 conservan su estado;
  este cierre no define la composición institucional del rol de encargado.
- D5 debe repetir los controles sobre el SHA congelado para entrega.

## Criterio de cierre

D2 se considera terminado porque los controles asignados fueron ejecutados,
sus resultados quedaron vinculados y el defecto observado se registró sin
ocultarlo. Su corrección está en el PR #589 y pertenece al trabajo de D4.
