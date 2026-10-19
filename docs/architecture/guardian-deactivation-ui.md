# Desactivación de encargados — G3, #632

## Alcance y decisión

Desde el detalle existente de Padres de familia se permite desactivar el perfil de
encargado mediante confirmación. La decisión explícita del usuario es crear
`guardian.deactivate`, con alcance del módulo `students`, donde reside Encargados.
No se reutiliza `scope.assign` ni el permiso docente de T3.

Rama creada desde `develop` actualizado a `0d6eeab`. G2 (#656), T3 (#655) y las demás
entregas abiertas son independientes. Este PR no incorpora G2 ni cambia paginación,
CSV, edición o alta. Al integrar #656 se deben conservar sus cambios de listado y
el `list.refresh()` posterior a la baja. G4 sigue pendiente.

Revisados AGENTS, ADR-0004/0005/0006/0008, guía UX, autorización y requerimientos
de permisos, alcances y bitácora. El diseño mantiene la baja lógica y las reglas
de alcance derivado existentes; no introduce cierres automáticos de vínculos.

## Autorización y contratos

`DELETE /api/v1/students/guardians/{id}/` conserva el identificador entero, el cuerpo
vacío y la respuesta 204. Ahora exige sesión activa y `guardian.deactivate`
(codename Django `guardian_deactivate`) con alcance `module_key=students`, o
superusuario activo. Permiso sin alcance, alcances de docentes/identidad/estudiante
individual y roles/asignaciones vencidos no autorizan esta operación sobre el padrón.
El servicio vuelve a evaluar el permiso al ejecutar; no confía en el botón.

El catálogo publica el permiso en el grupo Estudiantes. La migración de datos
`students.0008_seed_guardian_deactivate_permission` lo registra sobre el content type
de rol de identidad sin concederlo a roles existentes. Depende de la migración
vigente de identidad y de students; permanece independiente de `identity.0018`
de T3. Es idempotente y su reversión no borra permisos ni asignaciones históricas.
Se administra con las pantallas existentes de roles/alcances; no requiere variables.

Las representaciones de encargado añaden `actions: {deactivate: boolean}` de solo
lectura. Se deriva en consultas de dominio; los serializadores comparten la decisión
de permiso por respuesta, incluso al anidar encargados, sin una consulta de permisos
por fila. Sin request o capacidad explícita la acción es falsa. Los GET no registran
intentos de escritura. Las reglas de lectura y demás escrituras permanecen como
estaban; la brecha general de #643 no se declara resuelta.

## Efectos y auditoría

El servicio comprueba autorización antes de la transacción para conservar la auditoría
de rechazo. Bloquea el perfil con `select_for_update`, cambia solo `is_active` y fecha
de actualización y registra `students.guardian.deactivated` en la misma transacción.
Contexto: UUID del perfil y transición `is_active: {old: true, new: false}`; no nombres,
CUI o contactos. Si falla la auditoría se revierte la baja. Una petición repetida sobre
el perfil ya desactivado devuelve 204 sin nuevo evento ni cambio de fecha.

La denegación de un actor autenticado registra `identity.authorization.denied`,
recurso Guardian, permiso, alcance solicitado y motivo `missing_permission_or_scope`.
Un identificador inexistente conserva 404 y la sesión anónima se rechaza antes del servicio.

No se elimina persona, cuenta, estudiante o relación; no se finalizan vínculos ni se
cambia su condición de principal. La cuenta conserva sus otros roles y accesos.
La regla vigente de `guardian_student_queryset` deja de otorgar alcance estudiantil
por un perfil desactivado. El detalle continúa consultable y el listado lo excluye
por defecto; `include_inactive=true` permite encontrarlo. Esta operación no reactiva
perfiles ni permite usar un encargado desactivado para nuevos vínculos.

## Interacción

El botón se muestra solo con perfil activo y `actions.deactivate === true`. El detalle
se sustituye por la confirmación, cargada bajo demanda para mantener el presupuesto.
La confirmación identifica al encargado y explica conservación de cuenta/historial
y pérdida del acceso derivado. Cancelar restaura el detalle sin DELETE.

Mientras se procesa bloquea confirmar, cancelar, Escape y doble envío. Un error
conserva la confirmación y muestra el motivo con opción de reintentar. Al recibir
204 cierra y anuncia éxito; refresca el listado sin simular un registro actualizado.
Un fallo posterior de lectura no vuelve a ofrecer una escritura ya confirmada.
El cliente usa `apiClient.del`, conservando sesión, CSRF e invalidación existentes.

## Evidencia y límites

- `backend/tests/api/test_guardian_deactivation_ui_api.py`: permiso/alcance, vigencia,
  superusuario, rechazo auditado, capacidad de UI, reevaluación, sin N+1,
  conservación de persona/cuenta/vínculos, alcance derivado revocado, transacción,
  idempotencia y migración sin concesión automática.
- `backend/tests/api/test_guardians_api.py` y
  `backend/tests/permissions/test_guardian_derived_scope.py`: contratos e historial.
- `frontend/src/test/GuardianDeactivation.test.jsx`: capacidad ausente/falsa y perfil
  desactivado, confirmación, cancelación, error/reintento, bloqueo de envío y recarga.
- `frontend/src/test/guardianDeactivationService.test.js`: DELETE real del adaptador,
  identificador entero, sin cuerpo. Pruebas existentes de formularios conservadas.

Frontend completo: 537 pruebas aprobadas en 68 archivos, cobertura de líneas
88,21 %. Verificación focal final: 9 pruebas UI/adaptador, incluyendo la llamada
real a `apiClient.del`. Regresión API final: 76 pruebas aprobadas. Herramientas:
69 pruebas; políticas GitHub: 7. ESLint, Prettier y `git diff --check` aprobados.

Backend completo local con PostgreSQL: 2.097 aprobadas, 23 omitidas, cobertura 95,38 %.
Check Django, ausencia de migraciones de modelo pendientes, Ruff y build aprobados.
OpenAPI validado: cero errores, 25 advertencias existentes en otros endpoints.
Build: 226.009/230.000 bytes gzip iniciales; ruta máxima 19.278/20.000 y página fría
máxima 245.287/250.000. Node local 24, Python 3.11, PostgreSQL 18; CI valida versiones
fijadas. Docker local no ejecutado.

Chrome real en 1440×1000 y 390×844: cancelación sin DELETE, una sola baja al
confirmar y recarga del listado; sin desbordamiento de página en móvil. La base
de demostración confirma perfil desactivado, persona y vínculo vigentes, un solo
evento y perfil cancelado todavía activo.

Vista local aislada: `http://127.0.0.1:5194/app/padres-de-familia`. Buscar `EncargadoG3`.
Datos de prueba sintéticos, cookies y capturas quedan fuera del repo en
`tmp/local-runtime/632-g3-*`.

RF-PER-001/004, RF-ALC-001/006 y RF-BIT-001/002/004 se trazan como evidencia de esta
operación, sin cambiar sus estados globales ni declarar resuelto todo el issue.

Reversión preferida: retirar la UI conservando el control del DELETE y su auditoría.
Antes de revertir también el backend, bloquear esa operación para no restaurar la
brecha de sesión sin permiso. La migración no transforma ni elimina datos del padrón.

Comandos de validacion desde `backend/`: `python -m pytest --create-db --reuse-db -q`
(recrea solo la base automatica de pruebas), `python manage.py check`,
`python manage.py makemigrations --check --dry-run` y `python manage.py spectacular
--validate --file <archivo-temporal>`. Regresion final con `--no-cov --reuse-db`:
`tests/api/test_guardian_deactivation_ui_api.py`, `tests/api/test_guardians_api.py`,
`tests/permissions/test_guardian_derived_scope.py` y `tests/api/test_community_list_filters_api.py`.
Desde `frontend/`: `npm run test:coverage -- --maxWorkers=1 --no-file-parallelism`,
`npx vitest run src/test/GuardianDeactivation.test.jsx src/test/guardianDeactivationService.test.js
--maxWorkers=1 --no-file-parallelism`, `npm run lint`, `npm run build` y Prettier
sobre los archivos modificados. Ruff y las pruebas de herramientas/politicas se
verifican desde la raiz siguiendo los comandos de CI.
