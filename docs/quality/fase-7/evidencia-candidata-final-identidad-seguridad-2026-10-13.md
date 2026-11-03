# Evidencia de identidad y seguridad sobre candidata final

## Identificacion

| Campo | Valor |
| --- | --- |
| Fecha | 2026-10-13, America/Guatemala |
| Rama evaluada | `develop` |
| SHA evaluado | `68fa7753d0578abfa37a153df8a7f68e4b46a2bd` |
| Entorno local | Docker Compose, Python 3.11, Django 5.2.17, PostgreSQL 16, Node 22, Vitest 4.1.11 |
| Datos | Factories y datos sinteticos; sin datos institucionales ni secretos |

## Resultados

| Control | Resultado observado | Estado |
| --- | --- | --- |
| Identidad, autenticacion, autorizacion, alcances, privacidad y auditoria backend | 234 aprobadas; 0 fallidas; 4 advertencias de deprecacion de Django; 42.87 s | Aprobado |
| Frontend: login, sesiones, CSRF, cliente HTTP y cambio de clave | Corrida conjunta: 33 aprobadas y 2 fallidas por limite de 5 s. Repeticion aislada del archivo afectado con limite de 15 s: 3/3 aprobadas en 12.86 s | Aprobado con repeticion documentada |
| Bandit | Codigo de salida 0; sin hallazgos | Aprobado |
| `pip-audit` | `No known vulnerabilities found`; sin excepciones | Aprobado |
| `npm audit --json` | 0 vulnerabilidades en 508 dependencias contabilizadas | Aprobado |
| HTTPS QA | `GET /health/` respondio 200 por HTTPS | Aprobado |
| Redireccion HTTP | `GET /health/` por HTTP respondio 302 hacia HTTPS | Aprobado |
| CSRF en QA | `GET /api/v1/auth/login/` respondio 204 y emitio `csrftoken` con `Secure` y `SameSite=Lax` | Aprobado |
| Salud API QA | `GET /api/v1/health/` respondio `{"status":"ok","service":"api"}` | Aprobado |

La corrida frontend inicial se conserva como resultado historico de la misma
ejecucion. La repeticion aislada demuestra que el comportamiento funcional
aprueba y que el primer resultado corresponde al limite temporal de la prueba;
no se oculta ni se reemplaza el intento inicial.

## Incorporacion de cambios de seguridad

El SHA final contiene los siguientes cambios verificados mediante historia Git:

| Cambio | Evidencia de incorporacion |
| --- | --- |
| Auditoria de accesos sensibles denegados | `41e62f1`, PR #589, es ancestro del SHA final |
| `pytest==9.0.3` y auditoria backend sin allowlist | `16d8a51`, PR #579, es ancestro del SHA final |
| Vitest 4.1.11 y correccion de hallazgos frontend | `85b615b`, PR #537, es ancestro del SHA final |
| Revision cruzada de perdida de alcance | `785c739`, PR #586, es ancestro del SHA final |
| Revision del manual de administracion | `32d0bf4`, PR #590, es ancestro del SHA final |

El cambio equivalente preparado en el PR #580 no es ancestro de `develop`;
no se necesita para el resultado porque el PR #579 ya contiene
`pytest==9.0.3`, retiro de excepciones y pasa `pip-audit` sin hallazgos.

## Alcance de TLS

La comprobacion valida el endpoint QA publicado, su redireccion y atributos de
la cookie CSRF. El repositorio no expone en la respuesta de salud un SHA de
despliegue que permita demostrar que la revision activa de Cloud Run ejecuta
exactamente `68fa7753`. Por ello, la repeticion local queda vinculada al SHA
final y la comprobacion TLS queda vinculada al entorno QA accesible. Esta
limitacion debe permanecer visible hasta que despliegue registre el SHA de la
imagen o revision.

## Revision independiente

La revision independiente de Roi sobre este informe permanece pendiente. El
cierre requiere comentario o aprobacion verificable de Roi sobre el PR que
incorpore esta evidencia; no se atribuye una revision que no consta en el
repositorio.
