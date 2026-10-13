# Evidencia de identidad y seguridad — 12 de octubre de 2026

## Contexto común

- SHA evaluado: `450d0a805c34e779f3d2cd024cff8c2b985e133a`.
- Ejecutor: Santiago.
- Zona horaria: America/Guatemala.
- Entorno: Docker Compose local, PostgreSQL 16, datos sintéticos generados por
  factories; no se utilizaron secretos ni datos institucionales reales.
- Revisión cruzada: pendiente de Diana para funcionalidad y Daniel para
  dependencias.

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
0. La excepción debe permanecer sujeta a revisión de Daniel.

<a id="ev-ej-d1-040-01"></a>

## EV-EJ-D1-040-01 — Dependencias frontend

Comando: `docker compose exec -T frontend npm audit --audit-level=high`.

Resultado observado: código de salida 1; ocho vulnerabilidades: dos críticas,
cuatro altas y dos moderadas. La corrección total propuesta instala Vitest
5.0.3 y constituye un cambio mayor. No se ejecutó `npm audit fix` ni se modificó
el lockfile. Resultado vinculado a INC-003.

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

## Evidencia complementaria de CI

El job `backend-tests` del PR #547 ejecutó 1572 pruebas: 1557 aprobaron y 15
fallaron en módulos académicos, auditoría y sugerencias de formulario. El
hallazgo quedó separado como INC-005 porque la suite dirigida de identidad
aprobó. URL registrada en `incidencias.csv`.

## Limitaciones

Esta evidencia pertenece a una línea base local. No reemplaza la repetición
sobre el SHA candidato final, la revisión cruzada ni las comprobaciones de TLS
y cookies en el entorno HTTPS de entrega.
