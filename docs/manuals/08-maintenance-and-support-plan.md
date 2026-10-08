# Plan básico de mantenimiento y soporte

## Propósito y alcance

Este plan define cómo SIGA-INEBI registra, prioriza, corrige y verifica incidentes, defectos, solicitudes de cambio y mantenimiento preventivo después de una entrega. No autoriza cambios directos en producción, ni compromete disponibilidad continua fuera de la jornada lectiva definida para el establecimiento.

Pablo coordina calidad, trazabilidad y la revisión de cierre. Daniel mantiene la evidencia técnica, los controles automatizados y el manifiesto de versión. El responsable de cada dominio investiga y corrige incidencias de su área, con revisión cruzada independiente.

## Canal y registro oficial

GitHub Issues es el registro técnico oficial hasta que la institución designe una herramienta de soporte. Una solicitud recibida por correo, llamada o reunión se registra allí antes de considerarse atendida. Cada incidencia debe incluir:

- ID, fecha, reportante, responsable y estado.
- Descripción, pasos reproducibles, impacto y evidencia sanitizada.
- Requisito RF/RNF, versión/commit SHA, entorno y datos sintéticos usados para reproducir.
- Severidad, prioridad, decisión de alcance y acción correctiva.
- PR/SHA correctivo, prueba de regresión, revisor y evidencia de verificación.

El expediente de Fase 7 usa `docs/quality/fase-7/incidencias.csv` como exportación de seguimiento. No se registran contraseñas, tokens, cookies, datos de menores, respaldos o archivos reales.

## Clasificación y escalamiento

| Severidad | Ejemplos | Primera respuesta | Objetivo de respuesta | Escalamiento |
| --- | --- | --- | --- | --- |
| Crítica (S1) | Exposición de datos, pérdida/corrupción de historia, indisponibilidad total o duplicación grave. | Pablo y responsable de dominio. | Mismo día hábil. | Dirección institucional y responsable técnico; contener antes de cualquier corrección. |
| Alta (S2) | Operación institucional esencial bloqueada, recuperación fallida o requisito obligatorio incumplido. | Responsable de dominio, coordinado por Pablo. | Mismo día hábil. | Pablo decide prioridad con autoridad institucional si impacta operación. |
| Media (S3) | Función afectada con alternativa temporal y sin incumplir control de seguridad obligatorio. | Responsable de dominio. | Siguiente jornada hábil. | Se programa por impacto y evidencia. |
| Baja (S4) | Defecto visual, texto o mejora no bloqueante. | Responsable de dominio. | Próxima ventana planificada. | Agrupar si no altera comprensión o acceso. |

Los objetivos son tiempos de respuesta, no promesas de resolución ni disponibilidad 24/7. Una incidencia de seguridad, privacidad o pérdida de historia se clasifica por impacto, no por facilidad de corregirla.

## Flujo de corrección

1. Registrar y reproducir incidente en entorno controlado.
2. Evaluar impacto en datos, seguridad, autorización, auditoría, requerimientos y manuales.
3. Abrir issue y rama acotada conforme a [flujo Git](../development/git-workflow.md).
4. Agregar o ampliar prueba de regresión antes o junto con corrección.
5. Abrir Pull Request con RF/RNF afectados, ejecutar CI y obtener revisión independiente.
6. Integrar, identificar SHA y verificar en ambiente correspondiente.
7. Repetir regresión de dependencias afectadas; actualizar trazabilidad, documentación y evidencia.
8. Cerrar issue solo con resultado verificable; conservar historia de ejecuciones e incidencias.

Los cambios de alcance o reglas siguen [control de cambios](../requirements/change-control.md). Un cambio de arquitectura requiere ADR o decisión explícita. La [Definition of Done](../development/definition-of-done.md) aplica a todo cambio funcional.

## Mantenimiento preventivo

| Frecuencia | Actividad | Responsable | Evidencia |
| --- | --- | --- | --- |
| Antes de cada entrega | Ejecutar CI, pruebas en PostgreSQL, cobertura, lint, formato, build y revisión de migraciones. | Daniel + responsable de dominio. | Enlace a corrida, SHA y reportes. |
| Antes de cada entrega y después de incidentes relevantes | Revisar requisitos, trazabilidad, regresión, manuales y cambios de contrato. | Pablo + responsable de dominio. | Matriz y reporte actualizados. |
| Periódica, según calendario institucional | Revisar usuarios, roles, permisos y alcances administrativos. | Administrador autorizado; Santiago valida criterios técnicos. | Bitácora y registro de revisión. |
| Diaria según plan operativo | Verificar salud de respaldos de DB y archivos. | Administrador autorizado + Daniel. | Resultado de `backup-check` y monitoreo. |
| Antes de entrega y al menos una vez por ciclo | Ejecutar simulacro de recuperación. | Daniel + Roí, con revisión de Josué. | Informe de recuperación, RPO/RTO e integridad. |
| En actualización de dependencias | Revisar vulnerabilidades, allowlists, workflows y compatibilidad. | Daniel + Santiago. | Resultado de auditorías y decisión documentada. |
| Periódica | Revisar crecimiento de almacenamiento, logs y tareas programadas. | Daniel + administrador autorizado. | Métricas, TaskRun y acciones. |

La estrategia ejecutable de pruebas está en [Testing Strategy](../development/testing-strategy.md); recuperación y límites se rigen por [Backup and Recovery](../architecture/backup-and-recovery.md). El mantenimiento no borra historial auditable ni reemplaza respaldo por limpieza de datos.

## Comunicación y cierre

Pablo mantiene el tablero de incidencias, comunica S1/S2 a la contraparte institucional y documenta decisiones. El responsable técnico informa causa, impacto, corrección y regresión. Daniel conserva evidencia técnica y confirma que la versión/artefacto coincide con la verificada.

Una incidencia se cierra cuando su evidencia muestra reproducción, corrección revisada, regresión aprobada y trazabilidad/documentación actualizadas. Las incidencias diferidas conservan impacto, razón, responsable y fecha de revisión; no se marcan como resueltas.
