# Evidencia de identidad y seguridad — 12 de octubre de 2026

## Contexto común

- SHA evaluado: `450d0a805c34e779f3d2cd024cff8c2b985e133a`.
- Ejecutor: Santiago.
- Zona horaria: America/Guatemala.
- Entorno: Docker Compose local, PostgreSQL 16, datos sintéticos generados por
  factories; no se utilizaron secretos ni datos institucionales reales.
- Revisión cruzada: Diana confirmó `EJ-D1-041` en el PR #586; Daniel revisó
  las dependencias en el PR #574. Las demás repeticiones sobre candidato final
  permanecen pendientes.

<a id="ev-ej-d1-037-01"></a>

## EV-EJ-D1-037-01 — Backend dirigido

Comando: `docker compose exec -T backend pytest -q --no-cov` seguido de los 16
archivos API, permisos, unidad e integración vinculados en
`catalogo-casos.csv`.

Resultado observado: 158 pruebas aprobadas en 159.26 segundos, código de salida
0. Pytest informó cuatro `RemovedInDjango60Warning`; no hubo fallo funcional.

<a id="ev-ej-d1-038-01"></a>

## EV-EJ-D1-038-01 — Frontend dirigido

Comando: `docker compose exec -T frontend npm run test --
src/test/App.test.jsx src/test/ChangePasswordWindow.test.jsx
src/test/apiClient.test.js`.

Resultado observado: tres archivos y 33 pruebas aprobadas en 23.86 segundos,
código de salida 0. Se comprobaron login, logout, expiración, bloqueo, cambio de
contraseña y manejo de sesión del cliente HTTP.

<a id="ev-ej-d1-039-01"></a>

## EV-EJ-D1-039-01 — Seguridad backend

Comandos: `bandit -q -r apps config` y `pip-audit -r requirements/dev.txt` con
la lista de excepciones versionada en el `Makefile`.

Resultado observado: Bandit aprobó sin hallazgos; `pip-audit` informó cero
vulnerabilidades conocidas y una excepción ignorada. Código de salida conjunto
0. Daniel revisó el resultado: la excepción aplicable es `PYSEC-2026-1845`
(`CVE-2025-71176`) sobre `pytest 8.4.1`, dependencia exclusiva de desarrollo y
CI que no entra en la imagen productiva. La aceptación es temporal; los PR
#579 y #580 retiran seis entradas obsoletas de la allowlist, actualizan a
`pytest 9.0.3` y eliminan la excepción restante antes del candidato final.

<a id="ev-ej-d1-040-01"></a>

## EV-EJ-D1-040-01 — Dependencias frontend

Comando: `docker compose exec -T frontend npm audit --audit-level=high`.

Resultado observado: código de salida 1; ocho vulnerabilidades: dos críticas,
cuatro altas y dos moderadas. Este es un resultado histórico del SHA evaluado;
no se ejecutó `npm audit fix` ni se modificó el lockfile durante esa corrida.
La corrección se versionó posteriormente en el PR #537 con Vitest 4.1.11 y se
verificó en EJ-D1-042. Resultado vinculado a INC-003.

<a id="ev-ej-d1-041-01"></a>

## EV-EJ-D1-041-01 — Pérdida de alcance del encargado

Ejecución local sobre el SHA `9dd90e35dae2eace07dec635ba7eb7e3a6ec402e`,
con PostgreSQL 16 y datos exclusivamente sintéticos. Se prepararon una cuenta
de encargado con relación vigente, una cuenta de secretaría con alcance
explícito al estudiante y una cuenta con los mismos permisos atómicos pero sin
alcance.

Resultado observado por API:

- El encargado inició sesión y consultó salud y observaciones del estudiante
  vinculado: HTTP 200.
- El mismo encargado intentó consultar un estudiante ajeno: HTTP 403.
- Una solicitud de cierre con el token CSRF anterior fue rechazada: HTTP 403.
  Tras enviar el token rotado de la sesión, la solicitud autorizada fue
  aceptada: HTTP 200.
- La secretaría terminó la relación principal usando una relación vigente de
  reemplazo. La relación original conservó su registro y recibió fecha de fin;
  la relación de reemplazo quedó vigente y principal.
- Después del cierre, la cuenta del encargado recibió HTTP 403 al consultar
  tanto salud como observaciones del estudiante anteriormente vinculado.
- La bitácora conservó el evento de cierre y los rechazos posteriores con
  motivo `missing_scope`.

Regresión ejecutada: 124 pruebas de permisos, auditoría, sesiones, provisión de
cuentas, vínculos, salud y observaciones. Resultado: 124 aprobadas en 122.83
segundos, código de salida 0 y cinco advertencias no bloqueantes.

Configuración local observada: cookies de sesión `HttpOnly` y `SameSite=Lax`;
CSRF activo con rotación de token. Los indicadores `Secure` permanecen
desactivados en HTTP local, por lo que esta ejecución no sustituye la
verificación de cookies seguras y TLS en el entorno HTTPS de entrega.

Diana completó en el PR #586 la revisión cruzada sobre este SHA y sobre `develop` con datos
sintéticos propios: sus 28 comprobaciones coincidieron con el resultado. La
revisión encontró que tres de ocho rechazos HTTP 403 no generaron evento de
bitácora; el hallazgo queda registrado como INC-IDENT-001. También confirmó
que el acceso previo HTTP 200 depende de asignar `student_view_sensitive` al
rol de encargado. Esa asignación no se declara como regla aceptada: continúa
pendiente de decisión con Pablo bajo PD-004/PD-005.

<a id="ev-ej-d1-042-01"></a>

## EV-EJ-D1-042-01 — Reauditoría de dependencias frontend

Ejecución sobre el SHA `bfb502d69c11f47d13f078bc28080ddf23299564`,
con Node 22, lockfile versionado y Vitest 4.1.11. Comando:
`docker compose run --rm --no-deps -T frontend npm audit --json`.

Resultado observado: 431 paquetes auditados y 0 vulnerabilidades informativas,
bajas, moderadas, altas o críticas; código de salida 0. Esta ejecución reemplaza
EJ-D1-040 para el estado técnico vigente y enlaza la corrección del PR #537.
La ejecución histórica fallida permanece conservada. INC-003 queda corregida
técnicamente, pendiente de cierre formal y repetición sobre el SHA candidato
final.

## Evidencia complementaria de CI

El job `backend-tests` del PR #547 ejecutó 1572 pruebas: 1557 aprobaron y 15
fallaron en módulos académicos, auditoría y sugerencias de formulario. El
hallazgo quedó separado como INC-005 porque la suite dirigida de identidad
aprobó. URL registrada en `incidencias.csv`.

## Limitaciones

Esta evidencia pertenece a una línea base local. No reemplaza la repetición
sobre el SHA candidato final, la revisión cruzada ni las comprobaciones de TLS
y cookies en el entorno HTTPS de entrega.
