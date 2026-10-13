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
participantes y agenda, y acordar el SHA del candidato que se evaluará. Estuardo
informó que Pablo y Daniel no tienen tiempo disponible para completar ahora esa
coordinación; se registra como bloqueo, no como actividad hecha ni como excepción
de alcance aprobada.

Por ese motivo, no hay todavía resultados observados de usuarios, tiempos de
tarea, comentarios de participantes, videos de sesiones piloto ni decisiones de
aceptación. El preflight de escritorio y viewport móvil emulado es únicamente
una comprobación técnica; no sustituye esas actividades.

## Estado por jornada y entregable

| Punto | Estado | Evidencia disponible | Qué falta |
| --- | --- | --- | --- |
| **D1 — Preparación** | Parcial; coordinación bloqueada por disponibilidad | Casos de usabilidad/UAT, guion, plantilla de registro y preflight en el [PR #558](https://github.com/siga-inebi/siga-inebi/pull/558). | No hay participantes/agenda confirmados ni SHA candidato. La regla de pesos sigue sin definición verificable. No se asignan nombres, fechas o SHA supuestos. Hace falta una decisión de alcance para reprogramar o excluir temporalmente las sesiones y documentar el impacto. |
| **D2 — Evaluación e integración** | Ejecución automatizada completada en el SHA registrado; cierre con dependencias pendientes | [Matriz y resultados D2](d2-evaluacion-integracion.md): 196 pruebas de evaluación/reportes, 43 de integración académica/documental y 4 regresiones frontend de INC-008 aprobadas en `e67faeb97729281f2e7e7b9a91125f8612b79ffa`. | Pablo debe confirmar la regla de pesos; Josué y Roí deben hacer revisión conjunta; Roí debe validar QA4-PDF-01; repetir en el SHA candidato final. |
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
- **INC-008:** la corrección integrada en [PR #555](https://github.com/siga-inebi/siga-inebi/pull/555)
  ahora renderiza `final_grade`; las cuatro pruebas focalizadas de frontend y
  las pruebas backend de cálculo pasaron en el SHA indicado en el informe D2.
  La revisión visual manual todavía no está registrada.
- **INC-009:** el cambio para manejar el error de red y la regresión de ciclo
  cerrado están en el PR #563. Su descripción deja la incidencia en verificación
  hasta el triage de Pablo y revisión de Emilio.
- **Participantes y candidato:** sin usuarios institucionales confirmados y sin
  un SHA de candidato acordado, no corresponde presentar resultados de usabilidad
  ni UAT como concluyentes.
- **Disponibilidad para D1:** Estuardo informa que Pablo y Daniel no tienen tiempo
  para completar ahora las tareas pendientes. Si no se reprograman, el responsable
  de alcance debe aceptar expresamente la exclusión temporal y su impacto: no habrá
  evidencia de usabilidad ni aceptación UAT para esos escenarios.
- **Datos sintéticos:** pueden usarse para preparar o repetir pruebas técnicas,
  siempre identificando el entorno y SHA realmente probado. No sustituyen
  participantes institucionales ni permiten inventar sesiones, resultados,
  aprobaciones o el SHA de un candidato.
- **Dispositivos:** el plan de preparación contempla computadora y Android. La
  comprobación registrada de móvil fue emulada; falta documentar modelo, versión,
  navegador y resultado de Android real durante la sesión.
- **Regla de pesos:** el plan pide evaluar pesos, pero la revisión técnica previa
  no encontró una regla de ponderación cerrada. Pablo debe decidir o confirmar
  el criterio antes de reportar esa cobertura como aprobada.

## Próximas acciones

1. El responsable de alcance define si se reprograma D1 o acepta formalmente la
   exclusión temporal de sesiones, usuarios y UAT, registrando el impacto.
2. Si se reprograma, Pablo confirma perfiles/agenda y Daniel/Pablo seleccionan y
   registran el SHA real del candidato. También se documenta la regla de pesos o
   la decisión de alcance correspondiente.
3. Estuardo coordina con Josué la integración académica y con Roí la documental;
   Roí atiende QA4-PDF-01 y revisa los resultados de evaluación.
4. Si se reprograma, Estuardo ejecuta las sesiones piloto y UAT con los usuarios
   confirmados, registra cada escenario y conserva videos autorizados sin datos
   reales.
5. Estuardo completa ambos informes, revalida cambios con usuarios y entrega el
   índice y SHA del manual de usuario en video a Emilio para revisión.

## Evidencia de pull requests

Los documentos de preparación y rondas citados arriba están en PRs abiertos y
algunos forman una cadena de dependencias. Este informe registra su estado, pero
no implica que hayan sido integrados ni que una revisión pendiente esté aprobada.
Al corte de este reporte, el PR #556 tenía los checks de CI aprobados y esperaba
revisión; el PR #558 seguía abierto y la serie #559–#563 también estaba pendiente
de integración/revisión. El PR #584 tenía sus checks aprobados y esperaba revisión.

