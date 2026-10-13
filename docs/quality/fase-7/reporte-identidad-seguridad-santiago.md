# Reporte de validación de identidad y seguridad — Santiago

## Estado

Validación de línea base ejecutada el 12 de octubre de 2026 sobre el SHA
`450d0a805c34e779f3d2cd024cff8c2b985e133a`. Este reporte no constituye
aceptación final: el candidato de entrega, la revisión cruzada y varias
decisiones de alcance siguen pendientes.

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
| EJ-D1-041 | Pérdida de alcance del encargado y regresión dirigida | Aprobado técnicamente: accesos previos 200, rechazos posteriores 403, historial y auditoría conservados; 124 pruebas aprobadas |
| EJ-D1-042 | Reauditoría de dependencias frontend | Aprobado: 0 vulnerabilidades con Vitest 4.1.11; reemplaza EJ-D1-040 para el estado vigente |

Catorce requisitos incluidos quedaron `Aprobado` en el catálogo. Tres
requisitos condicionados quedaron `Bloqueado`: sus controles pasan, pero el
estado de implementación/documentación y DEC-QA-002 impiden aceptarlos.

## Incidencias y riesgos

- **INC-003, corregida técnicamente:** los ocho hallazgos pertenecen a las
  ejecuciones históricas EJ-D1-036/EJ-D1-040. El PR #537 actualizó a Vitest
  4.1.11 y EJ-D1-042 confirmó `npm audit` con cero vulnerabilidades. Falta el
  cierre formal mediante repetición sobre el candidato final.
- **Riesgo temporal backend:** `pytest 8.4.1` presenta `PYSEC-2026-1845`, pero
  solo se usa en desarrollo/CI y no entra en producción. Daniel aceptó la
  excepción temporal; los PR #579/#580 limpian la allowlist, actualizan a
  `pytest 9.0.3` y retiran la excepción.
- **INC-005, abierta P0:** la suite backend global del PR obtuvo 15 fallos y
  1557 aprobaciones. La suite dirigida de identidad aprobó; coordinación debe
  hacer triage de los fallos en academics, audit y form suggestions.
- Cuatro advertencias `RemovedInDjango60Warning` no provocaron fallos, pero
  deben revisarse antes de migrar a Django 6.

## Pendientes para cierre

1. Diana debe realizar la revisión cruzada de casos y del resultado técnico de
   pérdida de alcance registrado en EJ-D1-041.
2. Fusionar los PR #579/#580 y repetir `pip-audit` sin excepciones sobre el
   candidato final; la revisión de Daniel ya quedó registrada en el PR #574.
3. Pablo y la contraparte deben resolver DEC-QA-002 y las discrepancias de
   clasificación entre catálogo y matriz canónica.
4. Daniel debe fijar el SHA y entorno del candidato final conforme DEC-QA-001.
5. Repetir EJ-D1-037 a EJ-D1-042 sobre el candidato final.
6. Verificar cookies y TLS en el entorno HTTPS de entrega.
7. Mantener AUT-005 y CTA-005 sin aceptación hasta contar con alcance y prueba
   verificable.

## Conclusión

Los controles automatizados de identidad y autorización ejecutados son
satisfactorios para esta línea base. INC-003 está corregida técnicamente, pero
el dominio no está listo para aceptación final mientras falten la actualización
de pytest, DEC-QA-001, DEC-QA-002, la repetición final y la revisión cruzada.
