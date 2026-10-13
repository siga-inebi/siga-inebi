# Cierre documental D3 — identidad y seguridad

Fecha de cierre documental: 12 de octubre de 2026.
Responsable: Santiago.

## Resultado

D3 queda **completado documentalmente** para Santiago. Se reconciliaron la
evidencia HTTPS y de cookies del entorno QA, la revisión de dependencias con
Daniel, el informe de seguridad y el borrador del manual de administración.
Este cierre no certifica el candidato final ni sustituye las revisiones
independientes asignadas a Diana y Roí.

## Cookies y TLS

`despliegue-cloud-qa.md` registra una verificación real en Cloud Run:

- la aplicación respondió por HTTPS;
- HTTP redirigió a HTTPS con código 302;
- el inicio de sesión de la cuenta sintética `qa-admin` respondió 200;
- `sessionid` y `csrftoken` presentaron `Secure`;
- `sessionid` presentó `HttpOnly`.

La configuración versionada fija `SameSite=Lax`; RUN-CQ-01 no registró ese
atributo como observación independiente, por lo que no se le atribuye a esa
corrida.

La evidencia corresponde a RUN-CQ-01 y a sus revisiones documentadas, no al
candidato final. D5 debe repetir el control sobre el SHA y la revisión que se
congelen para entrega. No se copiaron cookies, tokens ni credenciales.

## Dependencias

Daniel revisó los hallazgos backend y dejó constancia en el PR #574. La única
excepción vigente de la línea base fue `PYSEC-2026-1845` / `CVE-2025-71176` en
`pytest 8.4.1`, dependencia exclusiva de desarrollo y CI. Los PR #579 y #580
retiran las excepciones obsoletas, actualizan a `pytest 9.0.3` y eliminan la
última excepción; permanecen pendientes de revisión y fusión.

La auditoría frontend histórica fallida se conserva en EJ-D1-040. El PR #537
actualizó Vitest a 4.1.11 y EJ-D1-042 verificó 431 paquetes con cero
vulnerabilidades. INC-003 está corregida técnicamente, pendiente de cierre
formal sobre el candidato final.

## Documentos entregados

- `informe-seguridad.md`: contenido D3 reconciliado; revisión de Roí pendiente.
- `docs/manuals/04-administration-manual.md`: borrador D3 completo; Diana lo
  revisó contra el código y se incorporaron sus cinco correcciones. Queda
  pendiente vincular el PR de su evidencia cuando lo abra y repetir la
  validación sobre el candidato final.
- `docs/manuals/02-technical-manual.md`: aporte de configuración segura,
  separación desarrollo/producción, cookies y TLS.
- `docs/manuals/03-installation-and-configuration.md`: aporte de orígenes,
  cookies, HTTPS y comprobaciones de entrega.

## Pendientes trasladados a D5

1. Fusionar #579/#580 y repetir `pip-audit` sin excepciones.
2. Repetir auditorías backend/frontend sobre el SHA candidato final.
3. Repetir cookies y TLS sobre la revisión final del entorno de entrega.
4. Incorporar la revisión independiente de Roí al informe de seguridad.
5. Vincular el PR de la revisión independiente de Diana y repetirla sobre el
   candidato final.

## Criterio de cierre

D3 se considera terminado porque los controles disponibles están ejecutados y
reconciliados, los hallazgos tienen tratamiento trazable y los documentos
asignados existen como borradores completos. Las fusiones, revisiones y
repeticiones finales se mantienen visibles y no se presentan como realizadas.
