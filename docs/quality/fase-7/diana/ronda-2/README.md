# Ronda 2 de Diana — integración y regresión del expediente

Fecha: 13 de octubre de 2026, America/Guatemala (corridas entre 04:04 y 04:19 UTC del 14).
Código evaluado: `develop` en `68fa7753d0578abfa37a153df8a7f68e4b46a2bd`, árbol limpio al iniciar.
Responsable: Diana. Ejecución técnica asistida por Claude Code; revisión de Santiago pendiente.
Diagnóstico local; no constituye aceptación institucional ni UAT.

## Resumen

| Pendiente asignado | Ejecución | Resultado |
| --- | --- | --- |
| Regresión de contactos de emergencia y paginación (INC-009) | EJ-DIA-20261013-001 | **Aprobado.** 168 de 168; cero avisos de paginación sin orden (la ronda 1 tenía dos). |
| Cobertura de la sugerencia de código estudiantil | EJ-DIA-20261013-002 y 003 | **Aprobado.** La sugerencia y el alta estaban cubiertas; faltaba el reintento por colisión. Se agregan dos pruebas (PR aparte). |
| Regresión de las pantallas del expediente (INC-013) | EJ-DIA-20261013-004 | **Aprobado.** 31 de 31 con el límite versionado, sin ampliarlo por línea de comandos. |
| Integración persona → estudiante → matrícula | EJ-DIA-20261013-005 | **Fallido en un paso.** 11 de 12; una cuenta sin alcance pudo matricular (INC-DIA-001). |
| Flujo de justificaciones | EJ-DIA-20261013-005 | **Aprobado.** 11 de 11. |
| Flujo de documentos | EJ-DIA-20261013-005 | **Aprobado con un paso bloqueado.** 11 de 12; no existe endpoint que entregue el token de descarga. |

El SHA evaluado es el mismo que la validación de candidata final de identidad y seguridad
(`candidata-final-identidad-seguridad-2026-10-13.md`, PR #597): `68fa775` incluye las correcciones
de INC-009 (#582) e INC-013 (#581). La etiqueta `phase7-rc1` (`db96ad6`) es anterior y no las
incluye. Entre `68fa775` y el `develop` actual no hay cambios en los dominios probados.

## Entorno

| Componente | Valor |
| --- | --- |
| Sistema | Windows 11 con Docker Desktop (contenedores Linux), proyecto aislado `siga_inebi_diana_qa` |
| Backend | Python 3.11.17, Django 5.2.17, pytest 8.4.1, PostgreSQL 16 efímero |
| Frontend | Node 22.23.3, Vitest 4.1.11 con jsdom |
| Datos | Factories sintéticas; ningún dato real. La base de desarrollo no se usó. |

## 1. Regresión del expediente y de INC-009 — EJ-DIA-20261013-001

Se repitieron los 24 nodos de la ronda 1 (`RUN-DIA-20261012-01`) y se agregó
`tests/api/test_form_suggestions_api.py`.

- **Resultado:** 168 aprobadas, 0 fallidas, código de salida 0, 55,64 s de pytest.
- **INC-009:** la ronda 1 registró dos `UnorderedObjectListWarning` en el listado de contactos de
  emergencia; esta corrida, ninguna. Incluye la prueba de regresión
  `test_list_emergency_contacts_has_a_stable_order`.
- **Advertencias restantes:** cuatro `RemovedInDjango60Warning` de `CheckConstraint`, ajenas al dominio.

## 2. Cobertura de la sugerencia de código — EJ-DIA-20261013-002 y 003

| Función | Antes (002, `develop`) | Después (003, con pruebas nuevas) |
| --- | --- | --- |
| `students.services.next_student_code` | Todas sus líneas cubiertas | Igual |
| `students.services.create_student` (alta con código generado) | Todas sus líneas cubiertas | Igual |
| `common.codes.create_with_generated_code` (reintento) | 84 %: el reintento por colisión no se ejercita | 96 %: solo falta la línea 78, inalcanzable por diseño |

La prueba `test_generated_student_code_survives_a_taken_number` dice cubrir la carrera entre dos
altas, pero no llega al reintento: la serie ya ve el número ocupado y salta sola. Las dos pruebas
nuevas provocan la colisión en el INSERT:

- `test_student_code_collision_is_retried_with_a_new_candidate`
- `test_student_code_generation_gives_up_after_repeated_collisions`

Van en la rama `test/students-code-collision-retry` (commit `9e1a070`). La corrida 003 se hizo
sobre ese commit, no sobre `develop`.

## 3. Regresión de las pantallas e INC-013 — EJ-DIA-20261013-004

| Archivo | Casos | Aprobados |
| --- | --- | --- |
| `AlumnosPage.test.jsx` | 15 | 15 |
| `GuardiansPage.test.jsx` | 8 | 8 |
| `personasPage.test.jsx` | 8 | 8 |

31 de 31 en 58,04 s, con el límite versionado y sin `--testTimeout`. En la ronda 1 dos casos
fallaron por el límite de 5 s; el PR #581 les dio 10 s.

## 4. Integración por API — EJ-DIA-20261013-005

HTTP real contra `runserver`: inicio de sesión, cookie de sesión y CSRF. Cuentas sintéticas:

| Cuenta | Permisos del rol | Alcance |
| --- | --- | --- |
| Secretaría | Ver y editar estudiante, ver sensible, matricular, subir y leer documentos | Módulo `students`; el estudiante creado, asignado tras el alta |
| Revisor | Ver estudiante, resolver justificaciones | El estudiante creado |
| Encargado | `auth_login`, `auth_logout`, ver estudiante básico, solicitar justificación | Derivado del vínculo vigente |
| Sin alcance | Ver estudiante, matricular, subir documentos | Ninguno |

La estructura académica (ciclo activo y cerrado, jornada, grado, secciones con cupo, llena y de
ciclo cerrado) y los parámetros de jornada se crearon con factories; en el caso manual los prepara
Josué y Emilio.

### CP-INT-MAT-001 — persona, estudiante y matrícula

| # | Comprobación | Esperado | Observado | Estado |
| --- | --- | --- | --- | --- |
| 1 | Sugerencia de código | 200 | 200 | Coincide |
| 2 | Alta de persona y estudiante sin código explícito | 201 | 201 | Coincide |
| 2 | El código asignado es el sugerido | `EST-2026-0001` | `EST-2026-0001` | Coincide |
| 2 | La persona queda creada y vinculada 1:1 | Sí | Sí | Coincide |
| 3 | Alta con código duplicado | 400 | 400 | Coincide |
| 4 | Consulta sin alcance | 403 | 403 | Coincide |
| 5 | Consulta con alcance | 200 | 200 | Coincide |
| 6 | Matrícula en sección con cupo; el estudiante pasa a activo | 201 | 201 | Coincide |
| 7 | Segunda matrícula activa del mismo estudiante | 400 | 400 | Coincide |
| 8 | Matrícula en sección llena | 400 | 400 | Coincide |
| 9 | Matrícula en ciclo cerrado | 400 | 400 | Coincide |
| 10 | Consulta de la matrícula vigente | 200, 1 | 200, 1 | Coincide |
| 11 | **Matrícula por cuenta con permiso y sin alcance** | **403** | **201** | **Fallido → INC-DIA-001** |

### CP-INT-JUS-001 — justificación de una ausencia

| # | Comprobación | Esperado | Observado | Estado |
| --- | --- | --- | --- | --- |
| 1 | Estado del día antes de justificar | `ausente_pendiente_justificar` | Igual | Coincide |
| 2 | El encargado presenta la justificación | 201, pendiente | 201, pendiente | Coincide |
| 3 | El encargado justifica a un estudiante ajeno | 403 | 403 | Coincide |
| 4 | El encargado adjunta un PDF | 201 | 201 | Coincide |
| 5 | Quien presentó lee el adjunto | 200 | 200 | Coincide |
| 5 | Un tercero sin permiso de revisión lee el adjunto | 403 | 403 | Coincide |
| 6 | Resolver sin permiso de revisión | 403 | 403 | Coincide |
| 7 | El revisor aprueba | 200, aprobada | 200, aprobada | Coincide |
| 8 | Segunda resolución de la misma justificación | 400 | 400 | Coincide |
| 9 | Estado del día después de aprobar | `ausencia_justificada` | Igual | Coincide |
| 9 | Los eventos de asistencia no cambian | 0 | 0 | Coincide |
| 10 | El encargado recibe la notificación | 1 | 1 | Coincide |

Se hizo por API porque justificaciones no tiene pantalla. Si Pablo no acepta la API como
evidencia, este caso sigue pendiente en navegador.

### CP-INT-DOC-001 — expediente documental

| # | Comprobación | Esperado | Observado | Estado |
| --- | --- | --- | --- | --- |
| 1 | Subir un PDF válido a la matrícula | 201 | 201 | Coincide |
| 1 | La suma SHA-256 registrada coincide con el archivo | Igual | Igual | Coincide |
| 2 | Subir un archivo no admitido | 400 | 400 | Coincide |
| 3 | Subir sin alcance | 403 | 403 | Coincide |
| 4 | Expediente documental de la matrícula | 200, 1 | 200, 1 | Coincide |
| 5 | Verificar integridad | 204 | 204 | Coincide |
| 6 | Subir nueva versión; la versión 1 se conserva | 201, versión 2 | 201, versión 2 | Coincide |
| 7 | Verificar un archivo alterado en disco | Rechazo | 400 | Coincide |
| 8 | Descargar sin token o con token inválido | 400 o 403 | 400 | Coincide |
| 9 | Obtener el token de descarga | Endpoint disponible | 404 | **Bloqueado** |

El paso 9 es la limitación ya conocida: el servicio que emite el token existe, pero ninguna vista
lo expone. No se abre incidencia nueva; queda pendiente la decisión de Pablo.

### Bitácora

Quedaron registrados, con su actor: alta del estudiante, matrícula, presentación, adjunto, lectura
del adjunto y resolución de la justificación, recálculo del día, subida, versión, lectura y
verificación de documentos, y los rechazos por `missing_scope`. La matrícula hecha sin alcance
también quedó auditada como `enrolments.student.matriculated`.

## Incidencias

| ID | Estado en `incidencias.csv` | Corrección | Regresión | Siguiente paso |
| --- | --- | --- | --- | --- |
| INC-009 | Verificado técnicamente | PR #582 (`a41007d`) | EJ-DIA-20261013-001 | Revisión de Santiago |
| INC-013 | Verificado técnicamente | PR #581 (`462fd8b`) | EJ-DIA-20261013-004 | Revisión de Santiago |
| INC-008 (fila de Diana) | Anulada por renumeración | Se sigue en INC-013 | — | Ninguno |
| INC-DIA-001 | Abierta, S2 propuesta | — | — | Triage de Pablo y responsable del dominio de matrícula |

### Trazabilidad de INC-008

`incidencias.csv` tiene dos filas `INC-008`:

- **La de Estuardo** (nota final sin redondear, PR #553). Es la dueña legítima del número; no se tocó.
- **La de Diana** (tiempos de espera del frontend). Es la misma incidencia que INC-013, con su
  número anterior. Quedó duplicada al fusionar el PR #578, que agregó INC-013 sin retirar la fila
  original. Se marca como «Anulada por renumeración» y se conserva como historial.

Cadena completa: registrada como INC-008 en el PR #568 → renumerada a INC-013 en el PR #578 →
corregida en el PR #581 → regresión EJ-DIA-20261013-004.

Pendiente ajeno: `INC-009` también está repetido. La fila de Diana (contactos de emergencia) entró
primero, en el PR #568; la de Estuardo (error de red en inglés) llegó después. Renumerar la de
Estuardo le corresponde a él o a Pablo.

### INC-DIA-001 — matrícula sin alcance

Una cuenta con `enrollment_create` y sin ningún alcance matriculó a un estudiante (201). Las reglas
del proyecto exigen permisos atómicos con alcance obligatorio (ADR-0005, `AGENTS.md`).

Causa observada: en `backend/apps/enrolments/api/views.py`, matricular, reinscribir, registrar
traslados y cambios usan `has_atomic_permission`, que no evalúa alcance. Solo una vista usa
`has_scoped_permission`. No se modificó código: corregirlo cambia la autorización de otro dominio y
requiere triage de Pablo. Se usa un prefijo propio para no repetir números con otros PR.

## Evidencia

Artefactos locales, excluidos de Git (`docs/quality/fase-7/evidence/RUN-DIA-20261013-0N/`):

| Corrida | Archivo | SHA-256 |
| --- | --- | --- |
| 01 | `junit.xml` | `da0bae198469bd9268db588b674711021f504e09c7d5013c8880bf5309a50fdf` |
| 01 | `pytest.log` | `ea80a3daf4c62c2044c7e2fda56c0fb7e6ff66312005ee2a76ce3b0382bb24fc` |
| 02 | `junit.xml` | `72a4fc7a46093d6d91c8e153bc31f179add1c87450175468b949ebf431d05d13` |
| 02 | `coverage.json` | `4158952bbea4bf3b0802cfe12785120228093c8955ebacf6a263c39ab3bd779b` |
| 03 | `junit.xml` | `fe2be530d852403cf892548d3e8b8feb19611215d54ed675bb7b1b54506fc082` |
| 03 | `coverage.json` | `5ba51731256568cee504f88b4e7ff980ebe78a35bd6fcec0f88aaa3f11a2c6bf` |
| 04 | `junit.xml` | `3fdcd62f9b9bbe75804ce29dc1334ed4946316bbf658f30b48594a42c8fce2bf` |
| 04 | `vitest.log` | `c759628d9ce6af01cbcf62714dafb1a63d00992997aab9455dd4cc5fc7477cfd` |
| 05 | `salida.txt` | `c38bc7ab0fb879f3a0929a7377af3b01698cce6fcd3008f3f9f1f8815f0ae959` |
| 05 | `integracion.json` | `91b3e17c06140317addb1f163802f9f6393f00b6c9c69bddc91dc539d50d3290` |
| 05 | `integracion.py` (script) | `e46c4da65907c1009c8de20df2fc9b8244ca4646d70b1c9937daceba700d7d5e` |

Las salidas no contienen contraseñas, cookies ni tokens. Los archivos subidos en la corrida 05 se
eliminaron al terminar.

## Límites

- La integración se hizo por API. No sustituye los casos manuales en pareja, en navegador y sobre
  el entorno QA, que siguen pendientes con Josué, Santiago, Emilio y Roí.
- Las corridas usan `68fa775`, la candidata final declarada en el PR #597, no `phase7-rc1`.
- Debe repetirse sobre el commit candidato final.
