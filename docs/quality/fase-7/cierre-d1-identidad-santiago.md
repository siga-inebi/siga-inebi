# Cierre documental D1 — identidad, autorización y seguridad

Fecha de cierre documental: 12 de octubre de 2026.
Responsable: Santiago.

## Resultado

D1 queda **completado documentalmente** para el alcance asignado a Santiago:
se inventariaron y vincularon las pruebas de login, sesiones, cuentas, roles,
permisos, alcances y privacidad; se definieron los perfiles sintéticos
permitidos y denegados; y existe revisión independiente de la pérdida de
alcance. Este cierre no equivale a UAT, aceptación institucional ni validación
del candidato final.

## Inventario y vínculos

El inventario canónico está en `catalogo-casos.csv`. Los casos de Santiago usan
el prefijo `CP-SEG-*` y conservan separados los requisitos incluidos,
condicionados y fuera del candidato. Las ejecuciones que sustentan la línea
base son:

| Ejecución | Cobertura | Estado |
| --- | --- | --- |
| `EJ-D1-037` | Identidad, autorización, permisos y alcances backend | 158 pruebas aprobadas |
| `EJ-D1-038` | Login, logout, sesiones, bloqueo y cambio de clave frontend | 33 pruebas aprobadas |
| `EJ-D1-041` | Pérdida inmediata del alcance de encargado | Aprobada; revisión independiente en PR #586 |

Los comandos, SHA, entorno y resultados observados permanecen en
`ejecuciones.csv` y
`evidencia-identidad-seguridad-2026-10-12.md`. No se reinterpretan como
aprobados los casos que el catálogo mantiene bloqueados o no ejecutados.

## Perfiles sintéticos definidos

| Perfil | Configuración prevista | Resultado que permite comprobar |
| --- | --- | --- |
| Encargado permitido | Cuenta vinculada a una persona encargada; rol mínimo con `auth.login`, `auth.logout` y `student.view_basic`; vínculo vigente con estudiante A; sin `ScopeGrant` administrativo propio | Lectura básica del estudiante vinculado |
| Secretaría con alcance | Cuenta institucional; permisos administrativos necesarios; alcance explícito sobre estudiante A | Gestión autorizada del vínculo y consulta administrativa |
| Cuenta sin alcance | Mismos permisos atómicos relevantes que secretaría, sin alcance efectivo sobre estudiante A | Denegación por falta de alcance |
| Estudiante ajeno | Estudiante B sin vínculo con el encargado | Denegación sin revelar datos ajenos |
| Encargado de reemplazo | Relación vigente, secundaria, con estudiante A | Reemplazo de la relación principal sin perder historia |

La composición anterior es una preparación de prueba, no una decisión sobre el
rol institucional definitivo. `student.view_sensitive` se excluye del rol
mínimo del encargado para el caso conjunto propuesto; PD-004/PD-005 continúan
abiertas y requieren decisión de Pablo.

## Preparación y revisión independiente

La ejecución local `EJ-D1-041` utilizó cuentas y relaciones sintéticas con los
perfiles permitido, administrativo y sin alcance. Diana reprodujo de forma
independiente el flujo por HTTP real sobre el SHA evaluado y sobre `develop`:
28 comprobaciones coincidieron. Su evidencia está en el PR #586.

No se crearon cuentas nuevas en el QA cloud como parte de este cierre. La
credencial administrativa se conserva en Google Secret Manager y la
preparación del entorno integrado corresponde a Daniel o a una persona con
acceso explícitamente autorizado. Esta limitación se declara para no afirmar
una ejecución manual inexistente y no invalida el cierre documental de D1.

## Hallazgos trasladados

- `INC-IDENT-001`: tres rechazos HTTP 403 observados por Diana no generaron
  evento de bitácora. Su corrección y regresión pertenecen a D2/D4.
- PD-004/PD-005: falta decidir la composición institucional del rol encargado.
- La ejecución manual conjunta en QA y la repetición sobre candidato final no
  forman parte de este cierre documental; permanecen para D4/D5 si se exigen.

## Criterio de cierre

Se considera terminado D1 porque existe inventario trazable, definición de
datos y perfiles sintéticos, ejecuciones vinculadas y revisión independiente.
No se declara que las cuentas propuestas estén creadas en QA, que exista UAT o
que el producto esté aceptado para entrega.
