# Revisión cruzada de EJ-D1-041 — pérdida de alcance del encargado

Fecha: 12 de octubre de 2026, America/Guatemala.
Ejecución revisada: `EJ-D1-041` de Santiago (PR #574), sobre el SHA
`9dd90e35dae2eace07dec635ba7eb7e3a6ec402e`.
Revisora: Diana. Ejecución técnica asistida por Claude Code.
Reproducción independiente; no es candidato formal, aceptación institucional ni UAT.

## Resultado

**La reproducción confirma el resultado de Santiago.** Las 28 comprobaciones coincidieron con
lo esperado en dos corridas: una sobre el mismo SHA que usó Santiago y otra sobre `develop`
(`5ed5fd24d02f494053c53dbbbafe50a8412534e5`).

El vínculo terminado conserva su historial y revoca el acceso del encargado de inmediato.
La revisión deja además dos observaciones que no invalidan el resultado (sección
«Observaciones»).

## Cómo se reprodujo

- Datos sintéticos creados con las factories del proyecto en una base PostgreSQL 16 efímera
  y aislada (proyecto Compose `siga_inebi_diana_qa`). No se usó la base de desarrollo.
- Peticiones HTTP reales contra `runserver`: inicio de sesión, cookie de sesión y token CSRF.
  No se usó `force_login`.
- Configuración `config.settings.test`, Python 3.11 y Django 5.2 dentro de la imagen `backend-test`.

| Cuenta sintética | Permisos del rol | Alcance |
| --- | --- | --- |
| Encargado | `student_view_basic`, `student_view_sensitive` | Derivado de su vínculo vigente y principal. |
| Encargado de reemplazo | — (sin cuenta) | Vínculo vigente, no principal. |
| Encargado solo básico | `student_view_basic` | Derivado de un vínculo vigente, no principal. |
| Secretaría | Los dos anteriores y `student_edit_basic` | Explícito sobre el estudiante vinculado. |
| Cuenta sin alcance | Los mismos que secretaría | Ninguno. |

Estudiantes: uno vinculado y uno ajeno, cada uno con una nota de salud y una observación.

## Comprobaciones pedidas

| # | Comprobación | Esperado | Observado | Estado |
| --- | --- | --- | --- | --- |
| 1 | El encargado consulta salud del estudiante vinculado | 200 | 200 | Coincide |
| 1 | El encargado consulta observaciones del vinculado | 200 | 200 | Coincide |
| 2 | El encargado consulta salud del estudiante ajeno | 403 | 403 | Coincide |
| 2 | El encargado consulta observaciones del ajeno | 403 | 403 | Coincide |
| 3 | Secretaría termina el vínculo principal sin reemplazo | 400 | 400 | Coincide |
| 3 | Secretaría termina el vínculo usando el reemplazo | 200 | 200 | Coincide |
| 4 | Encargado, misma sesión, consulta salud tras el cierre | 403 | 403 | Coincide |
| 4 | Encargado, misma sesión, consulta observaciones tras el cierre | 403 | 403 | Coincide |
| 4 | La sesión del encargado sigue abierta (`auth/me/`) | 200 | 200 | Coincide |
| 5 | La relación terminada sigue consultable por API | 200 | 200 | Coincide |
| 5 | La relación terminada conserva la fila, con fecha de fin y sin ser principal | Sí | Sí | Coincide |
| 5 | Un segundo cierre de la misma relación se rechaza | 400 | 400 | Coincide |
| 6 | La relación de reemplazo queda vigente y principal (API y base) | Sí | Sí | Coincide |
| 6 | Queda un solo encargado principal vigente | 1 | 1 | Coincide |
| 7 | El cierre aparece en la bitácora, atribuido a secretaría | 1 evento | 1 evento | Coincide |
| 7 | Los rechazos posteriores al cierre aparecen en la bitácora | 2 eventos | 2 eventos, motivo `missing_scope` | Coincide |

El paso 4 se hizo sin volver a iniciar sesión: la pérdida de acceso no depende de cerrar la
sesión del encargado.

## Controles adicionales de la revisión

| Comprobación | Esperado | Observado | Estado |
| --- | --- | --- | --- |
| Cuenta con permisos y sin alcance consulta salud | 403 | 403 | Coincide |
| Cuenta con permisos y sin alcance intenta terminar el vínculo | 403 | 403 | Coincide |
| Encargado con solo permiso básico consulta salud del vinculado | 403 | 403 | Coincide |
| El propio encargado intenta terminar su vínculo | 403 | 403 | Coincide |
| Secretaría envía el cierre con un token CSRF inválido | 403 | 403 | Coincide |

Cookies observadas en HTTP local: `sessionid` con `HttpOnly` y `SameSite=Lax`; `csrftoken`
con `SameSite=Lax` y legible por el cliente. Ninguna lleva `Secure` en HTTP local, igual que
reportó Santiago; no sustituye la verificación en el entorno HTTPS.

## Observaciones

### 1. No todos los rechazos quedan en la bitácora

De los ocho rechazos 403 de autorización de la corrida, cinco generaron evento
`identity.authorization.denied` y tres no:

| Rechazo | ¿Evento en bitácora? |
| --- | --- |
| Encargado consulta salud y observaciones tras el cierre (2) | Sí, `missing_scope` |
| Cuenta sin alcance consulta salud e intenta terminar el vínculo (2) | Sí, `missing_scope` |
| Encargado intenta terminar su propio vínculo (1) | Sí, `missing_permission` |
| Encargado **vigente** consulta salud y observaciones del estudiante **ajeno** (2) | **No** |
| Encargado con solo permiso básico consulta salud del vinculado (1) | **No** |

La comprobación 7 de Santiago se cumple tal como la redactó (los rechazos posteriores al
cierre sí se auditan). La brecha está en los rechazos del paso 2: un encargado con alcance
vigente que intenta leer datos sensibles de un estudiante que no es suyo recibe 403, pero el
intento no deja rastro.

Es coherente con lo que declara el manual técnico en PDF del 29 de septiembre de 2026
(sección 5.6): RNF-SEG-003 figura `In Progress` y «otros intentos denegados quedan fuera del
corte actual». Se reporta a Santiago para que decida si
se registra como incidencia; no se asigna identificador aquí para no duplicar números con
los PR abiertos.

### 2. Qué puede leer un encargado depende de los permisos de su rol

El alcance del encargado se deriva de su vínculo vigente, pero el permiso sale de su rol. Con
`student_view_sensitive` en el rol, el encargado lee salud y observaciones del estudiante
vinculado (paso 1: 200). Con solo `student_view_basic`, recibe 403.

El manual técnico en PDF del 29 de septiembre de 2026 (sección 5.2) describe el alcance
derivado del encargado como «solo `student_view_basic`». El código no limita el alcance derivado a ese permiso: lo aplica a
cualquier permiso que tenga el rol. No es un defecto demostrado, pero qué permisos lleva el
rol de encargado es una decisión institucional abierta (PD-004 y PD-005) y conviene fijarla
antes de la entrega.

## Evidencia

Artefactos locales, excluidos de Git (`docs/quality/fase-7/evidence/REV-DIA-EJ-D1-041/`):

| Archivo | Contenido | SHA-256 |
| --- | --- | --- |
| `salida-9dd90e3.txt` | Corrida sobre el SHA de Santiago | `071700941da80c4e49a644829cc3c36b585200025e0fd697299d9f7b4768533e` |
| `salida-develop.txt` | Corrida sobre `develop`, con el orden de eventos de bitácora | `70e54fa49f82c9199de2d39a31bb0e304e6186400228eec24d0801333683d4ee` |
| `review.py` | Script de reproducción (versión de la segunda corrida) | `735b85ce6a2e74149f405d38689ebf7bf49126d5d1615b06500d54189e046faa` |

Las salidas no contienen contraseñas, cookies ni tokens: solo códigos HTTP, banderas de
cookies y nombres de cuentas sintéticas.

## Límites

- Reproducción por API en HTTP local. No cubre navegador real, cookies `Secure`, TLS ni el
  entorno QA en la nube.
- El caso manual en pareja previsto en el plan (sesiones de navegador con Santiago en QA)
  sigue pendiente; esta revisión no lo sustituye.
- Debe repetirse sobre el commit candidato final.
