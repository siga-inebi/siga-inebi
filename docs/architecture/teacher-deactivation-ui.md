# Desactivación del perfil docente — T3, issue #632

## Decisión de autorización

El 19 de octubre de 2026 el responsable del proyecto aprobó explícitamente crear
`teacher.deactivate` con alcance `teachers`, en lugar de reutilizar `scope.assign`.
El DELETE existente solo exigía sesión. Esta entrega cierra esa brecha para la baja docente;
no cambia la autorización de alta, edición o lectura, que continúa seguida en #643.

Se aplica ADR-0005, denegación por defecto y alcance obligatorio. Código público
`teacher.deactivate`, codename Django `teacher_deactivate`, grupo «Docentes».
Una cuenta ordinaria requiere permiso y grant vigente con `module_key="teachers"`.
Permiso sin grant, otro módulo, rol inactivo y vigencias vencidas no autorizan.
Se conserva la excepción administrativa de superusuario del proyecto.

## Contratos y arquitectura

- `DELETE /api/v1/teachers/{id}/` conserva el identificador entero y 204 sin cuerpo.
  Ahora exige la autorización descrita: es un cambio de seguridad explícito, no solo de UI.
  Deniega con 403 y audita el intento; un ID inexistente conserva 404.
- Lista, detalle y respuestas de escritura agregan `actions: {deactivate: boolean}` de solo
  lectura. La capacidad es falsa para perfiles desactivados o sin autorización y nunca
  sustituye la comprobación al ejecutar el DELETE. Leer capacidades no audita escrituras
  no intentadas. El permiso global del módulo se resuelve una vez por respuesta, sin N+1.
- `teachers/authorization.py` concentra permiso, alcance y denegaciones; `queries.py`
  determina capacidades; la vista adapta HTTP y el serializador publica los resultados.
- `deactivate_teacher` exige actor autorizado, bloquea la fila y confirma baja y evento
  dentro de una transacción. Un error al auditar revierte la baja. Repetir sobre un perfil
  ya desactivado devuelve 204 sin cambiar fecha ni duplicar evento.
- Evento existente `teachers.teacher.deactivated`: actor, Teacher, ID, código y transición
  `is_active: {old: true, new: false}`; conserva los metadatos del contexto de solicitud.

## Conservación y experiencia

La baja solo cambia `Teacher.is_active`. Conserva persona, cuenta de acceso y sus roles,
asignaciones docentes y documentos. No cierra asignaciones ni ciclos, no revoca acceso y no
desactiva la cuenta. La confirmación explica estas consecuencias y muestra nombre y código.
Esas operaciones se administran por sus flujos propios; T3 no modifica sus reglas.

La ficha muestra la actividad del perfil y ofrece «Desactivar docente» al final, en rojo,
únicamente con capacidad positiva del servidor. Al abrir la confirmación se cierra la ficha;
cancelar vuelve a ella sin escribir. La confirmación se carga bajo demanda y bloquea doble
envío, Cancelar, Escape y cierre por fondo mientras procesa. Un rechazo conserva el destino
y muestra el motivo. Un DELETE confirmado cierra la confirmación, informa el éxito y recarga
el listado. Si falla esa lectura, «Reintentar listado» repite solo GET, nunca el DELETE.

La lista del servidor excluye desactivados por defecto; su detalle e historial siguen
disponibles. La UI de «Mostrar desactivados», URL y paginación de servidor se entrega en
#654 (T2/T4), que está separada; esta rama nace de `develop`, sin incorporarla.

## Migración y operación

`identity.0018_seed_teacher_deactivate_permission` crea/actualiza el permiso de forma
idempotente y no lo concede a roles existentes. Tras desplegar, Administración debe añadir
«Desactivar docentes» al rol correspondiente y asignarlo con alcance de módulo «Expedientes
docentes» (`teachers`). El seeder demo deriva sus permisos del catálogo y solo afecta el
entorno de demostración cuando se ejecuta expresamente.

La reversa de datos es deliberadamente vacía: no elimina permisos ni concesiones posteriores.
No requiere variables nuevas ni cambios de esquema. Una reversión operativa puede retirar
la UI conservando la protección del DELETE. No debe restaurarse el DELETE abierto a cualquier
sesión al revertir el backend; mantener el control de autorización o bloquear esa operación
hasta una corrección. No hay cambios de datos personales o historial que restaurar.

## Pruebas y trazabilidad

- `backend/tests/api/test_teacher_deactivation_ui_api.py`: permiso/alcance, revocación,
  vigencias, rol inactivo, superusuario, capacidades sin auditoría espuria, consultas
  constantes por página, conservación, rollback, idempotencia y migración sin concesiones.
- `backend/tests/api/test_teachers_api.py`: DELETE autorizado y regresión de contratos.
- `frontend/src/test/TeacherDeactivation.test.jsx`: confirmación identificada, cancelación,
  ausencia de capacidad, inactivo, doble envío, Escape, rechazo/reintento y fallo de recarga.
- `frontend/src/test/moduleServices.test.js`: DELETE existente sin cuerpo.

T3 se vincula a RF-PER-001/004, RF-ALC-001 y RF-BIT-001/002/004 por sus contratos de permiso,
alcance y auditoría. La matriz agrega evidencia sin cambiar estados globales de cumplimiento.
Se preservan ADR-0004/0005/0006/0008 y PostgreSQL.

Validación local: backend completo, 2.097 aprobadas y 23 omitidas, 95,38 % de cobertura;
frontend, 537 aprobadas en 68 archivos, 88,22 % de líneas con Vitest 3.2.7. PostgreSQL 18,
Python 3.11 y Node 24 locales; CI valida las versiones fijadas. La primera selección sobre
la base de pruebas reutilizada encontró permisos iniciales ausentes en identidad; recrear
solo `test_siga_inebi` permitió aprobar las 66 pruebas API y la suite completa sin cambios
ajenos al dominio. La base de demostración no se recreó ni alteró con esa operación.

ESLint, Prettier, Ruff, check Django, ausencia de migraciones de esquema pendientes y
OpenAPI aprobaron; este último conserva 25 advertencias existentes y cero errores.
Herramientas de requerimientos/carga: 69 aprobadas; políticas GitHub: 7.
Build: inicial 226.018/230.000 bytes gzip; ruta máxima 19.718/20.000 y página fría máxima
245.736/250.000. No se ejecutó Docker localmente.

Chrome real, escritorio 1440×1000 y móvil 390×844, solo datos sintéticos: confirmación con
nombre/código, cancelación sin escritura, una baja real con un DELETE y un evento, recarga
y detalle desactivado conservado con capacidad falsa. No se versionan sesiones, bases,
capturas ni descargas. Vista local: `http://127.0.0.1:5192/app/docentes`; «DocenteT3
Confirmacion» queda activo para revisión y «DocenteT3 Baja» conserva la baja comprobada.
Resultados CI en el PR de esta entrega.
