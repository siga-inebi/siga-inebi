# Domain Map

## Dominios nucleares

| Dominio | Responsabilidad principal | Dependencias clave |
| --- | --- | --- |
| identity-access | Autenticacion, cuentas, roles, permisos, alcances, sesiones | people-registry, institutional-structure |
| people-registry | Persona institucional base para cuentas y actores | Ninguna |
| student-records | Expediente estudiantil, fotografia, salud, contactos, encargados | people-registry |
| school-cycle | Ciclos, estados, apertura, cierre, historia | institutional-structure |
| institutional-structure | Grados, secciones, subareas, jornadas, asignaciones, horarios | school-cycle |
| enrollment-lifecycle | Matricula, reinscripcion, retiros, cambios, promociones | student-records, school-cycle, institutional-structure |
| attendance-capture | Credencial, QR, turnos, lotes, eventos de asistencia | enrollment-lifecycle, identity-access |
| attendance-governance | Estado diario, cierres, justificaciones, alertas | attendance-capture, school-cycle |
| academic-evaluation | Unidades, notas, recuperacion, resultados | enrollment-lifecycle, institutional-structure |
| document-management | Documentos, tipos, acceso, descargas seguras | file-storage, identity-access |
| document-generation | Plantillas, emision, folios, documentos oficiales | academic-evaluation, enrollment-lifecycle |
| audit-compliance | Bitacora, lecturas sensibles, intentos denegados | Todos |
| file-storage | Metadatos, integridad, retencion, referencias a binarios | document-management, student-records |
| reporting-notifications | Alertas y reportes minimos | attendance-governance, academic-evaluation |

## Dependencias fundacionales

```text
people-registry
  -> identity-access
  -> student-records

school-cycle
  -> institutional-structure
  -> enrollment-lifecycle
  -> academic-evaluation

enrollment-lifecycle
  -> attendance-capture
  -> document-generation

attendance-capture
  -> attendance-governance

file-storage
  -> document-management

audit-compliance
  -> transversal a todos
```

## Fronteras recomendadas

- Reglas de negocio viven en dominio backend, no en vistas ni componentes.
- Authz se consulta como servicio de dominio o capa compartida, no inline en UI.
- Dominios comparten identificadores estables, no tablas internas acopladas sin API interna clara.
- Las mutaciones de dominios dependientes de `school-cycle` consultan su politica compartida de
  estado antes de escribir; los rechazos de ciclos cerrados no alteran la historia conservada.
