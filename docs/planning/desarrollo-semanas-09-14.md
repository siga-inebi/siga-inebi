# Plan de desarrollo, semanas 9 a 14

Este documento formaliza el cronograma, el plan de iteraciones, la revisión del Product Backlog,
el Sprint Backlog inicial y las asignaciones verificables de la etapa. El
[GitHub Project de desarrollo](https://github.com/orgs/siga-inebi/projects/1) es la fuente viva para
estado, responsable y seguimiento; este documento conserva los acuerdos y resultados esperados.

- **Periodo:** 14 de agosto al 24 de septiembre de 2026
- **Última revisión:** 17 de agosto de 2026
- **Detalle operativo de S9:** [`sprint-2026-08-14.md`](./sprint-2026-08-14.md)

## Evidencia de los entregables

| Entregable solicitado | Evidencia |
|---|---|
| Cronograma detallado | Calendario S9-S14 de este documento y calendario diario de S9. |
| Plan de iteraciones o sprints | Objetivo, secuencia y resultado esperado de cada sprint. |
| Product Backlog revisado | Issues priorizados, milestones y exclusiones documentadas en el Project. |
| Sprint Backlog inicial | Milestone S9 y distribución por carril detallada más abajo. |
| Asignaciones individuales verificables | Assignee por issue y evidencia mediante PR, pruebas, CI y trazabilidad. |

## Cronograma y plan de iteraciones

Cada sprint corre de viernes a jueves. El trabajo pendiente de un sprint conserva prioridad y pasa
al inicio del siguiente antes de abrir alcance nuevo. Las sesiones de martes y jueves se usan para
demostrar avances, resolver bloqueos y actualizar el Project.

| Sprint | Fechas | Objetivo y orden de trabajo | Entregable esperado |
|---|---|---|---|
| **S9** | 14-20 ago | Integrar plataforma y luego los cortes verticales de seguridad, estructura, expediente, bitácora, documental, asistencia y evaluación. | Flujos principales conectados al API real, con pruebas y CI verde. El detalle diario está en el [plan de S9](./sprint-2026-08-14.md). |
| **S10** | 21-27 ago | Resolver primero el overflow de S9. Completar el siguiente paquete Debe/Debería de cada carril. | Seguridad de sesión, estructura restante, movimientos iniciales, auditoría transversal, archivos/emisión, captura y resultados ampliados. Primer video interno de caminos felices. |
| **S11** | 28 ago-3 sep | Construir sobre los flujos base ya integrados: horarios, movimientos, captura completa, resultados, emisión y credencial. | Flujos interdominio demostrables con permisos, auditoría y pruebas de integración. |
| **S12** | 4-10 sep | Completar justificaciones, aulas y RNF vinculados a seguridad, privacidad, consistencia y rendimiento. | Justificaciones completas, controles no funcionales verificables y estructura académica complementaria. |
| **S13** | 11-17 sep | Cerrar huecos Debe e integrar worker, respaldos y parametrización. Atender Podría solo si el carril está al día. | Sistema integrado, regresión preliminar y borrador de demostración para aceptación. |
| **S14** | 18-24 sep | Congelar alcance funcional nuevo. Ejecutar regresión, revisión de seguridad y usabilidad, aceptación y correcciones UX. | CI y regresión en verde, video de aceptación y registro de observaciones o correcciones. |

### Secuencia dentro de cada sprint

1. Confirmar que cada issue cumple la [Definition of Ready](../development/definition-of-ready.md).
2. Resolver overflow y dependencias antes de iniciar alcance nuevo.
3. Implementar por carril en cambios revisables, con pruebas en el mismo PR.
4. Revisar e integrar en `develop`; una PR abierta no cuenta como entrega terminada.
5. Actualizar Project, trazabilidad y riesgos al cierre del jueves.

## Product Backlog revisado

El Product Backlog se mantiene en los issues del repositorio y se visualiza en el
[Project público](https://github.com/orgs/siga-inebi/projects/1). Los milestones S9-S14 expresan la
prioridad temporal. Las etiquetas representan la prioridad MoSCoW:

| Etiqueta | Prioridad |
|---|---|
| `priority:high` | Debe |
| `priority:medium` | Debería |
| `priority:low` | Podría |

### Criterios de revisión

Un issue permanece en la cola de ejecución cuando:

- corresponde al alcance contractual vigente;
- tiene criterio de aceptación comprobable;
- conserva una prioridad válida;
- tiene milestone, responsable y dominio definidos antes de entrar al sprint;
- puede producir evidencia mediante código, prueba, documento, configuración o PR.

Los issues ambiguos no se programan. [#168](https://github.com/siga-inebi/siga-inebi/issues/168)
y [#214](https://github.com/siga-inebi/siga-inebi/issues/214) quedan fuera de la cola hasta que sus
criterios de aceptación sean explícitos. Las épicas #62-#68 y el chore #40 sirven para seguimiento,
no representan unidades individuales de implementación.

### Estado de la revisión al 17 de agosto

| Grupo | Cantidad | Tratamiento |
|---|---:|---|
| Issues con milestone S9-S13 | 179 | Backlog priorizado y distribuido; 5 ya estaban cerrados al revisar. |
| Elementos planificados visibles en el Project | 177 | Tienen seguimiento por sprint en el tablero. |
| Épicas y seguimiento fuera de sprint en el Project | 8 | Agrupan resultados, no se estiman como tareas individuales. |
| Issues planificados pendientes de agregar al Project | 2 | #297 en S11 y #280 en S12; ambos ya tienen assignee y milestone. |
| Issues bloqueados por ambigüedad | 2 | #168 y #214, sin programación. |
| Issues nuevos para S14 | 0 | S14 se reserva para calidad, aceptación y correcciones. |

La diferencia entre milestones y Project es administrativa, no de alcance. Se solicitó al líder
agregar [#297](https://github.com/siga-inebi/siga-inebi/issues/297) y
[#280](https://github.com/siga-inebi/siga-inebi/issues/280) al tablero oficial.

## Sprint Backlog inicial, S9

El milestone S9 contiene 51 issues con responsable: 46 permanecían abiertos y 5 estaban cerrados al
momento de la revisión. El plan detallado también registra el issue
[#106](https://github.com/siga-inebi/siga-inebi/issues/106), cerrado durante S9 pero actualmente sin
milestone; por eso no está incluido en el conteo del Project. La selección prioriza capacidades base
que desbloquean a los demás dominios. El orden, las dependencias y los criterios de entrega están en
[`sprint-2026-08-14.md`](./sprint-2026-08-14.md).

| Carril | Responsable | Issues S9 | Resultado verificable |
|---|---|---:|---|
| Seguridad | Roí (`1Roy1`) | 5 + #106 | Alcance y cuentas integrados con pruebas de autorización. |
| Académico | Estuardo (`EstuardoVasquez`) | 6 | Ciclo, secciones, cupos y asignaciones disponibles. |
| Expediente | Santiago (`SantiUrbinax`) | 7 | Registro y consulta del estudiante, encargados y contactos. |
| Bitácora | Luis (`LuisOvalleH`) | 6 | Registro, consulta y exportación restringida de auditoría. |
| Documental | Josué (`JoshSantizo`) | 14 | Archivos, documentos, plantilla activa y emisión individual. |
| Asistencia | Diana (`DianaMorales03`) | 6 | Presencia, porcentaje y captura idempotente. |
| Evaluación | Emilio (`emilioxmedina`) | 5 | Captura de calificaciones y consulta del resultado. |
| Plataforma | Daniel (`daniel-baf`) | 2 | Compatibilidad y peso de página verificados. |

## Asignación individual verificable

Cada issue de implementación tiene una persona responsable. El resultado individual no se acredita
por actividad declarada, sino por evidencia enlazada desde el issue.

| Evidencia | Cómo se comprueba |
|---|---|
| Implementación | PR que referencia el issue y está integrada en `develop`. |
| Calidad | Pruebas del camino feliz y del rechazo relevante, con CI en verde. |
| Revisión | Review o aprobación registrada en GitHub. |
| Requerimiento | Matriz de trazabilidad actualizada cuando se implementa un RF/RNF. |
| Documentación o configuración | Archivo o cambio versionado y revisado mediante PR. |
| Demostración | Video o evidencia enlazada en el issue o épica correspondiente. |

La [Definition of Done](../development/definition-of-done.md) determina cuándo una tarea puede
cerrarse. En particular, un RF no se considera completado sin prueba verificable y trazabilidad.

## Dependencias y control de cambios

El orden entre carriles protege el camino crítico:

1. Plataforma habilita la base compartida de frontend y CI.
2. Seguridad y Académico habilitan alcance, ciclo y estructura.
3. Expediente habilita documentos, asistencia, credencial y movimientos.
4. Documental y Evaluación habilitan emisión y resultados finales.
5. Bitácora define el contrato de auditoría consumido transversalmente.

Si una dependencia no llega, el consumidor trabaja con el contrato y pruebas disponibles, pero no
integra supuestos ficticios. El alcance pendiente vuelve al frente del siguiente sprint. Cualquier
cambio material de requerimiento se registra según
[`change-control.md`](../requirements/change-control.md).

## Cierre semanal

Al cierre de cada jueves se registra en el Project:

```text
Carril:
Sprint: EN RIESGO | EN CURSO | MERGEADO
PRs:
Entregable verificable:
Overflow al siguiente sprint:
Bloqueo recibido o causado:
```

El plan se revisa contra el estado real del repositorio. Los cambios de responsable, sprint o
alcance se actualizan primero en issues y milestones; este documento se modifica cuando cambie un
acuerdo de etapa, no por cada movimiento operativo del tablero.
