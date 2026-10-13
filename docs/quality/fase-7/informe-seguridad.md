# Informe de seguridad — línea base D1–D3

## Alcance y limitaciones

Pablo ejecutó la revisión inicial del frontend sobre el SHA
`0c8f0d396231f46809b95cc088d5f2c557cb919f`. Santiago repitió los controles
disponibles el 11 de octubre de 2026 sobre el SHA
`3bcca08860b07c7086ac11b914a7262e7a68d282`, usando Docker, Python 3.11 y
PostgreSQL 16. El 12 de octubre Santiago repitió la validación sobre
`450d0a805c34e779f3d2cd024cff8c2b985e133a`: 158 pruebas backend y 33 pruebas
frontend dirigidas aprobaron; Bandit y la auditoría backend también aprobaron.

Esta no es la certificación de la versión final. La revisión de dependencias de
Daniel y la verificación HTTPS de RUN-CQ-01 completan el alcance documental de
D3; permanecen pendientes la revisión de Roí y la repetición de controles sobre
el SHA y la revisión cloud del candidato final.

## Resultado histórico de dependencias frontend

En los SHA históricos de EJ-D1-036 y EJ-D1-040, `npm audit --json` informó 8
vulnerabilidades en el lockfile: 2 críticas, 4 altas y 2 moderadas.

| Componente | Severidad reportada | Hallazgo | Acción |
| --- | --- | --- | --- |
| `vitest` / `tinypool` | Crítica | Gadgets de contaminación de prototipo/RCE en opciones de worker de pruebas. | Corregido en PR #537 con Vitest 4.1.11; no fue necesario Vitest 5 ni `npm audit fix --force`. |
| `brace-expansion` | Alta | Denegación de servicio por expansión/recursión no acotada. | Trazar cadena transitiva y actualizar lockfile con revisión. |
| `js-yaml` | Alta | Uso excesivo de CPU mediante fuentes de combinación vacías. | Trazar cadena transitiva y actualizar lockfile con revisión. |
| `nanoid` | Alta | Generador personalizado puede iterar indefinidamente con tamaño cero. | Trazar cadena transitiva y actualizar lockfile con revisión. |
| `source-map-js` | Alta | Denegación de servicio por offsets de secciones de source maps. | Trazar cadena transitiva y actualizar lockfile con revisión. |
| `@vitest/coverage-v8` / `@vitest/mocker` | Moderada | Dependencias de la cadena de Vitest. | Resolver junto con actualización de Vitest. |

Los paquetes señalados pertenecían principalmente a herramientas de
desarrollo/prueba. El PR #537 actualizó el lockfile a Vitest 4.1.11 y documentó
la regresión. EJ-D1-042 repitió `npm audit --json` sobre el SHA
`bfb502d69c11f47d13f078bc28080ddf23299564` y obtuvo cero vulnerabilidades.
Las ejecuciones fallidas se conservan como evidencia histórica.

## Dependencias backend

Bandit no informó hallazgos. Daniel confirmó que la única excepción aplicable
de `pip-audit` es `PYSEC-2026-1845` (`CVE-2025-71176`) sobre `pytest 8.4.1`.
Pytest solo se instala en desarrollo y CI y no forma parte de la imagen
productiva, por lo que la excepción se acepta temporalmente durante integración.
Los PR #579 y #580 eliminan seis IDs obsoletos, actualizan a `pytest 9.0.3` y
retiran la excepción antes del candidato final.

## Controles ejecutados

| Control | Resultado | Evidencia |
| --- | --- | --- |
| ESLint frontend | Aprobado | EJ-D1-003 |
| Pruebas frontend | 283 aprobadas; dos advertencias de `src=""` | EJ-D1-003, INC-004 |
| Build y presupuesto estático | Aprobado | EJ-D1-003 |
| Identidad, autorización y alcance backend | 158 pruebas aprobadas en PostgreSQL 16 | EJ-D1-037 |
| Autenticación y sesiones frontend | 33 pruebas aprobadas | EJ-D1-038 |
| Bandit y `pip-audit` backend | Aprobado con excepción temporal de pytest revisada por Daniel | EJ-D1-039; PR #579; PR #580 |
| `npm audit --audit-level=high` histórico | Fallido: 8 vulnerabilidades en el SHA evaluado | EJ-D1-040, INC-003 |
| `npm audit --json` vigente | Aprobado: 0 vulnerabilidades con Vitest 4.1.11 | EJ-D1-042, PR #537 |
| Configuración de cookies | QA: `sessionid` y `csrftoken` con `Secure`; `sessionid` con `HttpOnly`. Configuración versionada: `SameSite=Lax` | RUN-CQ-01; `despliegue-cloud-qa.md`; `backend/config/settings/base.py` |
| HTTPS y redirección | Aprobado en QA: HTTPS respondió 200 y HTTP redirigió con 302 | RUN-CQ-01; `despliegue-cloud-qa.md` |
| Repetición en candidato final | Pendiente para D5 | Requiere SHA y revisión cloud final confirmados |

## Conclusión

INC-003 está corregida técnicamente y ya no representa un riesgo activo; su
cierre formal requiere repetir la auditoría sobre el candidato final. D3 queda
completado documentalmente: Daniel revisó dependencias y RUN-CQ-01 verificó
cookies y HTTPS en QA. La seguridad del candidato final no puede aceptarse
hasta fusionar #579/#580, repetir los controles sobre el SHA final e incorporar
la revisión independiente de Roí.
