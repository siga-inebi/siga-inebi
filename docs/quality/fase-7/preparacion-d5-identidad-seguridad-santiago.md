# Preparación D5 — identidad, autorización y seguridad

D5 no puede cerrarse antes de que Daniel y Pablo identifiquen el candidato
final mediante un SHA y un entorno de entrega. Esta lista evita confundir el
borrador completo con la certificación final.

## Controles que Santiago debe confirmar

- [ ] PR #589 fusionado y regresión de auditoría aprobada sobre el candidato.
- [ ] PR #579 y PR #580 integrados; `pip-audit` ejecutado sin excepciones
  obsoletas y con la excepción temporal de `pytest` eliminada.
- [x] Suite dirigida de identidad/autorización repetida sobre `phase7-rc1`:
  ejecutada y validada.
- [x] Suite frontend de autenticación y sesiones repetida sobre `phase7-rc1`:
  ejecutada y validada.
- [x] `npm audit --json`, Bandit y `pip-audit` repetidos sobre `phase7-rc1`:
  ejecutados y validados.
- [x] Cookies `Secure`/`HttpOnly` y redirección HTTPS verificadas nuevamente en
  el entorno final sin copiar secretos ni tokens.
- [ ] PR #590 integrado y manual de administración validado contra la versión
  final; cualquier cambio posterior vuelve a abrir las secciones afectadas.
- [ ] Revisión de Roí incorporada al informe de seguridad.
- [ ] Excepciones y decisiones PD-004/PD-005 declaradas con responsable y
  decisión vigente; no se asumen resueltas.
- [x] Informe de seguridad y manual revisados contra el SHA evaluado: ejecutado
  y validado.

## Evidencia mínima de la repetición

Cada corrida debe registrar identificador, SHA, fecha, entorno PostgreSQL,
comando, código de salida, resultado y vínculo a evidencia sanitizada en
`ejecuciones.csv` e `indice-evidencias.csv`. D5 solo se marca completado cuando
todos los controles aplicables tengan evidencia del mismo candidato final.
