# Preparación D5 — identidad, autorización y seguridad

El candidato evaluado es `phase7-rc1`, SHA
`db96ad6372620bb9bd3519af8dd7b1fc8e8733a9`. Fue integrado en la rama
`release/phase7-rc1`. Esta lista distingue los controles ya validados de las
revisiones e integraciones externas todavía pendientes.

## Controles que Santiago debe confirmar

- [x] Corrección del PR #589 integrada en `phase7-rc1` y regresión de auditoría
  aprobada sobre el candidato. Su fusión individual a `develop` sigue pendiente.
- [x] PR #579 y PR #580 integrados en `phase7-rc1`; `pip-audit` ejecutado sin
  excepciones y con `pytest 9.0.3`.
- [x] Suite dirigida de identidad/autorización repetida sobre `phase7-rc1`:
  ejecutada y validada.
- [x] Suite frontend de autenticación y sesiones repetida sobre `phase7-rc1`:
  ejecutada y validada.
- [x] `npm audit --json`, Bandit y `pip-audit` repetidos sobre `phase7-rc1`:
  ejecutados y validados.
- [x] Cookies `Secure`/`HttpOnly` y redirección HTTPS verificadas nuevamente en
  el entorno final sin copiar secretos ni tokens.
- [x] PR #590 integrado en `phase7-rc1` y manual de administración validado
  contra el candidato; cualquier cambio posterior reabre las secciones afectadas.
- [ ] Revisión de Roí incorporada al informe de seguridad.
- [x] No quedan excepciones de dependencias vigentes. PD-004/PD-005 permanecen
  declaradas como decisiones institucionales abiertas; no se inventó una regla
  para cerrarlas y los criterios afectados conservan su limitación.
- [x] Informe de seguridad y manual revisados contra el SHA evaluado: ejecutado
  y validado.

## Evidencia mínima de la repetición

Cada corrida debe registrar identificador, SHA, fecha, entorno PostgreSQL,
comando, código de salida, resultado y vínculo a evidencia sanitizada en
`ejecuciones.csv` e `indice-evidencias.csv`. Los controles propios de identidad
y seguridad quedan ejecutados y validados sobre el mismo RC1. La revisión de
Roí y las fusiones a `develop` permanecen como dependencias externas visibles.
