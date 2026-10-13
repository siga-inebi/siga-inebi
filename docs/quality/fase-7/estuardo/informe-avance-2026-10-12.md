# Informe preliminar de avance — Estuardo

**Actividad:** evaluación, usabilidad y aceptación con usuarios (UAT)  
**Fecha de corte:** 12 de octubre de 2026  
**Estado:** avance parcial; no es informe final de usabilidad ni acta de aceptación.  
**Alcance de este informe:** resume evidencia técnica disponible y separa las
actividades que aún dependen de participantes, del candidato de entrega o de
revisión de otros responsables. No declara requisitos aceptados.

## Resumen ejecutivo

Se prepararon casos, guiones, plantillas de registro y una comprobación técnica
previa. También existe evidencia de varias rondas técnicas de evaluación. Las
sesiones piloto con participantes y la UAT institucional todavía no se han
realizado: según el estado registrado en la preparación, faltan confirmar
participantes y agenda con Pablo, y acordar el SHA del candidato que se evaluará.

Por ese motivo, no hay todavía resultados observados de usuarios, tiempos de
tarea, comentarios de participantes, videos de sesiones piloto ni decisiones de
aceptación. El preflight de escritorio y viewport móvil emulado es únicamente
una comprobación técnica; no sustituye esas actividades.

## Estado por jornada y entregable

| Punto | Estado | Evidencia disponible | Qué falta |
| --- | --- | --- | --- |
| **D1 — Preparación** | Parcialmente preparado | Casos de usabilidad/UAT, guion, plantilla de registro y preflight en el [PR #558](https://github.com/siga-inebi/siga-inebi/pull/558). | Pablo debe confirmar participantes institucionales y agenda. Daniel/Pablo deben fijar el SHA candidato. Pablo debe resolver la regla de pesos que el plan pide probar y que no queda definida por la evidencia revisada. |
| **D2 — Evaluación e integración** | Pruebas técnicas documentadas; integración conjunta pendiente | Rondas técnicas y de navegador en los PRs [#556](https://github.com/siga-inebi/siga-inebi/pull/556)–[#563](https://github.com/siga-inebi/siga-inebi/pull/563). La revisión documental del manual de API está en el [PR #584](https://github.com/siga-inebi/siga-inebi/pull/584). | Revisar resultados con Roí y Josué; repetir sobre el SHA candidato final; resolver/triagear incidencias abiertas. QA4-PDF-01 sigue sin corrección validada: el PDF observado requirió reparación y no se encontró acción de descarga en la interfaz. |
| **D3 — Usabilidad piloto** | No ejecutado | Casos y preflight técnico preparados en el PR #558. El preflight cubre escritorio, zoom y viewport móvil emulado. | Confirmar participantes, ejecutar tareas observadas en computadora y Android real, anotar tiempos, ayudas, errores y comentarios, obtener autorización para grabar y preparar el video de cada sesión acordada. |
| **D4 — UAT** | No ejecutado | Escenarios y formato para aprobación/observaciones preparados en el PR #558. | Con candidato y participantes confirmados, cada usuario debe ejecutar los escenarios; registrar resultado por caso y SHA, aprobación/observaciones y cualquier incidencia. El facilitador no ejecuta las tareas en su lugar. |
| **D5 — Revalidación y cierre** | Pendiente | Existe evidencia de evaluaciones técnicas y de una revisión documental de API iniciada por Estuardo. | Revalidar con usuarios los cambios que correspondan; elaborar `informe-usabilidad.md` y `informe-aceptacion-usuarios.md`; obtener revisión cruzada de Roí; cerrar índice, SHA y revisión del material audiovisual. |
| **Manual de usuario en video** | Existe según confirmación de Estuardo; validación documental pendiente | Estuardo confirma que ya tiene el manual de usuario en video. | Registrar ubicación accesible, títulos, módulos, roles, duración y SHA-256; Emilio y el revisor independiente deben validar la versión final y la integración de segmentos del equipo. Este material es distinto de los videos de sesiones piloto de D3. |

## Incidencias y dependencias relevantes

- **QA4-PDF-01:** la descarga directa de la boleta respondió HTTP 200, pero la
  inspección encontró que el lector PDF tuvo que reparar sus referencias
  internas. La sesión por interfaz también quedó bloqueada por falta de una
  acción de descarga disponible. Roí debe analizar y corregir el problema; una
  respuesta HTTP exitosa no demuestra que el documento sea válido para el
  usuario.
- **INC-009:** el cambio para manejar el error de red y la regresión de ciclo
  cerrado están en el PR #563. Su descripción deja la incidencia en verificación
  hasta el triage de Pablo y revisión de Emilio.
- **Participantes y candidato:** sin usuarios institucionales confirmados y sin
  un SHA de candidato acordado, no corresponde presentar resultados de usabilidad
  ni UAT como concluyentes.
- **Dispositivos:** el plan de preparación contempla computadora y Android. La
  comprobación registrada de móvil fue emulada; falta documentar modelo, versión,
  navegador y resultado de Android real durante la sesión.
- **Regla de pesos:** el plan pide evaluar pesos, pero la revisión técnica previa
  no encontró una regla de ponderación cerrada. Pablo debe decidir o confirmar
  el criterio antes de reportar esa cobertura como aprobada.

## Próximas acciones

1. Pablo confirma perfiles de participantes y agenda; Daniel/Pablo seleccionan y
   registran el SHA del candidato.
2. Pablo documenta la regla de pesos aplicable o la decisión de alcance.
3. Estuardo coordina con Josué la integración académica y con Roí la documental;
   Roí atiende QA4-PDF-01 y revisa los resultados de evaluación.
4. Estuardo ejecuta las sesiones piloto y UAT con los usuarios confirmados,
   registra cada escenario y conserva videos autorizados sin datos reales.
5. Estuardo completa ambos informes, revalida cambios con usuarios y entrega el
   índice y SHA del manual de usuario en video a Emilio para revisión.

## Evidencia de pull requests

Los documentos de preparación y rondas citados arriba están en PRs abiertos y
algunos forman una cadena de dependencias. Este informe registra su estado, pero
no implica que hayan sido integrados ni que una revisión pendiente esté aprobada.
Al corte de este reporte, el PR #556 tenía los checks de CI aprobados y esperaba
revisión; el PR #558 seguía abierto y la serie #559–#563 también estaba pendiente
de integración/revisión. El PR #584 tenía sus checks aprobados y esperaba revisión.

