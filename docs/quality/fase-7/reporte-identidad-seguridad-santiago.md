# Reporte de validación de identidad y seguridad — Santiago

## Estado

Validación final del área ejecutada sobre `phase7-rc1`, SHA
`db96ad6372620bb9bd3519af8dd7b1fc8e8733a9`. Este reporte no sustituye la
aceptación institucional y conserva explícitas las decisiones de alcance
pendientes. D1 está completado documentalmente conforme a
`cierre-d1-identidad-santiago.md`: incluye inventario, perfiles sintéticos,
ejecuciones vinculadas y revisión independiente, pero no afirma preparación
manual en QA, UAT ni aceptación institucional.

D2 también está completado conforme a
`cierre-d2-identidad-seguridad-santiago.md`. D3 está cerrado documentalmente en
`cierre-d3-identidad-seguridad-santiago.md`. D4 fue ejecutado y validado con la
corrección del PR #589 integrada en RC1. Los controles propios de D5 también
fueron ejecutados y validados; faltan la revisión de Roí y las fusiones externas.

## Alcance evaluado

- Autenticación, bloqueo temporal, cierre y expiración de sesiones.
- Cambio de contraseña y provisión administrativa de cuentas.
- Roles, permisos atómicos, denegación por defecto y vigencia inmediata.
- Alcances institucionales, docentes, de encargados y de ciclo activo.
- Controles frontend de login, logout, expiración, bloqueo y cambio de clave.
- Análisis estático y auditoría de dependencias backend/frontend.
- Pérdida inmediata del alcance de encargado al terminar el vínculo, reemplazo
  de la relación principal, conservación histórica y auditoría de rechazos.

El catálogo contiene 29 casos `CP-SEG-*`. Se ejecutaron los 17 clasificados
como incluidos o condicionados. Los 12 casos fuera del candidato conservan
estado `No ejecutado`; no se usaron sus pruebas existentes para declarar
aceptación.

## Resultados

| Ejecución | Control | Resultado |
| --- | --- | --- |
| EJ-D1-037 | Backend de identidad, autorización y alcance | Aprobado: 158 pruebas; cuatro advertencias de deprecación |
| EJ-D1-038 | Frontend de autenticación y sesiones | Aprobado: 33 pruebas en tres archivos |
| EJ-D1-039 | Bandit y `pip-audit` | Aprobado: sin hallazgos Bandit; cero vulnerabilidades conocidas y una excepción versionada |
| EJ-D1-040 | `npm audit --audit-level=high` | Fallido: 8 vulnerabilidades, vinculadas a INC-003 |
| EJ-D1-041 | Pérdida de alcance del encargado y regresión dirigida | Aprobado y revisado por Diana: 28 comprobaciones coincidentes; INC-IDENT-001 registra tres rechazos sin evento de auditoría |
| EJ-D1-042 | Reauditoría de dependencias frontend | Aprobado: 0 vulnerabilidades con Vitest 4.1.11; reemplaza EJ-D1-040 para el estado vigente |

Catorce requisitos incluidos quedaron `Aprobado` en el catálogo. Tres
requisitos condicionados quedaron `Bloqueado`: sus controles pasan, pero el
estado de implementación/documentación y DEC-QA-002 impiden aceptarlos.

## Incidencias y riesgos

- **INC-003, cerrada en RC1:** los ocho hallazgos pertenecen a las
  ejecuciones históricas EJ-D1-036/EJ-D1-040. El PR #537 actualizó a Vitest
  4.1.11 y la repetición en RC1 confirmó `npm audit` con cero vulnerabilidades.
- **Riesgo backend resuelto en RC1:** los PR #579/#580 limpian la allowlist,
  actualizan a `pytest 9.0.3` y permiten ejecutar `pip-audit` sin excepciones.
- **INC-005, abierta P0:** la suite backend global del PR obtuvo 15 fallos y
  1557 aprobaciones. La suite dirigida de identidad aprobó; coordinación debe
  hacer triage de los fallos en academics, audit y form suggestions.
- **INC-IDENT-001, cerrada en RC1:** la revisión cruzada de EJ-D1-041
  confirmó el resultado funcional y detectó tres rechazos HTTP 403 sin evento.
  El PR #589 agrega la auditoría faltante y la repetición integrada en RC1
  aprobó 244 pruebas. La fusión individual del PR a `develop` sigue pendiente.
- **PD-004/PD-005, abiertas:** el HTTP 200 previo al cierre depende de que el
  rol de encargado tenga `student_view_sensitive`; Pablo debe definir la
  composición institucional del rol. La prueba no fija esa política.
- Cuatro advertencias `RemovedInDjango60Warning` no provocaron fallos, pero
  deben revisarse antes de migrar a Django 6.

## Pendientes para cierre

Los siguientes puntos corresponden a D2–D5 y al cierre final del dominio; no
reabren el cierre documental de D1:

1. Fusionar el PR #589 a `develop`; la regresión en RC1 ya está aprobada.
2. Pablo debe resolver la composición del rol encargado bajo PD-004/PD-005.
3. Fusionar los PR #579/#580 a `develop`; `pip-audit` sin excepciones ya aprobó
   en RC1 y la revisión de Daniel está registrada en el PR #574.
4. Pablo y la contraparte deben resolver DEC-QA-002 y las discrepancias de
   clasificación entre catálogo y matriz canónica.
5. Incorporar la revisión independiente de Roí al informe de seguridad.
6. Mantener AUT-005 y CTA-005 sin aceptación hasta contar con alcance y prueba
   verificable.

## Conclusión

Los controles de identidad y autorización están ejecutados y validados sobre
`phase7-rc1`. Las dos incidencias de seguridad del área están cerradas para ese
candidato y no quedan excepciones de dependencias. Permanecen externas la
revisión de Roí, las fusiones a `develop`, las decisiones PD-004/PD-005 y la
aceptación institucional.
