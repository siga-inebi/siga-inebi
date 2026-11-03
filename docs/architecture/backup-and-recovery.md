# Respaldo y Recuperacion

## Proposito

Definir como se respalda SIGA-INEBI, como se restaura en la infraestructura
objetivo y contra que metas se mide esa recuperacion.

- `RNF-RES-001` — *El respaldo de la base de datos es independiente del de
  archivos y se restaura en la infraestructura objetivo* (MoSCoW: Debe).
- `RNF-RES-002` — *Punto y tiempo objetivo de recuperacion declarados y probados
  antes de la entrega* (MoSCoW: Debe).

## Dos pilas, dos esquemas

Los binarios viven fuera de la base de datos
(`docs/architecture/file-storage-strategy.md`), asi que hay dos cosas distintas
que respaldar y no una:

| Pila | Contenido | Artefacto | Script |
| --- | --- | --- | --- |
| `database` | Metadatos, expedientes, bitacora, integridad, vinculos | `siga-db-<UTC>.dump` (`pg_dump --format=custom`) | `scripts/backup/backup-database.sh` |
| `files` | Adjuntos y documentos persistidos bajo `MEDIA_ROOT` | `siga-files-<UTC>.tar.gz` | `scripts/backup/backup-files.sh` |

**La independencia es una propiedad verificable, no una intencion.** Cada pila
tiene su directorio, su artefacto, su manifiesto y su par de scripts. Ningun
script de una llama a uno de la otra, y ningun manifiesto menciona a la otra
pila. Restaurar una sola es un caso previsto y probado, no un accidente.

Restaurar solo la base deja documentos con metadatos sin binario. Esa situacion
no es ambigua: `python manage.py check_document_storage_integrity` los reporta
como `missing`. Restaurar solo los archivos deja binarios que ninguna fila
referencia todavia, lo cual es inofensivo y reversible.

## Manifiestos

Cada artefacto se acompana de un `.manifest.json` con su `sha256`, tamano,
instante de creacion en UTC y los datos propios de su pila (nombre de la base y
version de `pg_dump`; ruta de origen y numero de archivos). Sirve para tres
cosas:

1. **Verificar antes de restaurar.** Los scripts de restauracion comprueban el
   checksum y se niegan a escribir nada si no coincide. Un respaldo que no se
   puede verificar no es un respaldo.
2. **Medir el RPO** sin depender de la `mtime` del archivo, que un copiado entre
   hosts reescribe.
3. **Documentar la version de las herramientas**, que es parte del respaldo y no
   un detalle del host que lo produjo.

## Version de PostgreSQL

`pg_dump` y `pg_restore` tienen que compartir **version mayor** con el servidor.
Un dump producido por otra mayor no se puede restaurar en la infraestructura
objetivo, que es exactamente lo que `RNF-RES-001` exige garantizar.

Esto no se deja al azar del host:

- el servidor esta fijado en `postgres:16-alpine` (`compose.yml`);
- la imagen del backend instala `postgresql-client-16` desde el repositorio
  oficial de PostgreSQL, porque el paquete `postgresql-client` de Debian sigue
  su propia version (hoy 17) y no coincidiria;
- `make backup-database`, `make restore-database` y `make recovery-drill` se
  ejecutan **dentro del contenedor de la base**, cuyo cliente coincide por
  construccion;
- si aun asi hay desajuste, los scripts lo detectan antes de escribir y explican
  que hacer, en vez de reventar a media restauracion con
  `unrecognized configuration parameter`.

## Operacion

```sh
make backup            # ambas pilas, cada una autonoma
make backup-database   # solo la base
make backup-files      # solo los archivos

make restore-database  # restaura el respaldo mas reciente de la base
make restore-files     # restaura el respaldo mas reciente de archivos

make backup-check      # verifica el RPO declarado
make recovery-drill    # restauracion cronometrada en una base desechable (RTO)
```

`BACKUP_ROOT` define donde viven los artefactos (por defecto `./backups`, que
esta en `.gitignore`: contienen datos reales del establecimiento y no se
versionan jamas). Las credenciales viajan por `PGPASSWORD` o `DATABASE_PASSWORD`
del entorno; ningun script las imprime ni las guarda.

**El destino de los respaldos debe estar fuera del host que corre la
aplicacion.** Un respaldo en el mismo disco que la base no sobrevive al fallo
que lo justifica. `BACKUP_ROOT` apunta a un directorio local por comodidad de
desarrollo; en el establecimiento apunta a almacenamiento externo.

### Cadencia sugerida

| Tarea | Cadencia | Por que |
| --- | --- | --- |
| `backup-database` | Diaria, fuera de la jornada lectiva | Sostiene el RPO de 24 h |
| `backup-files` | Diaria, fuera de la jornada lectiva | Misma ventana, artefacto separado |
| `backup-check` | Diaria, despues de las anteriores | Convierte el RPO declarado en una afirmacion comprobada |
| `recovery-drill` | Antes de cada entrega y al menos una vez por ciclo | `RNF-RES-002` pide el RTO *probado*, no declarado |

`backup-check` corre como comando de gestion, asi que deja su fila `TaskRun` y
su linea de log como cualquier otra tarea programada
(`docs/architecture/operations-monitoring.md`).

## Metas de recuperacion declaradas

| Meta | Valor declarado | Variable |
| --- | --- | --- |
| RPO (punto objetivo de recuperacion) | **24 horas** | `RECOVERY_POINT_OBJECTIVE_HOURS` |
| RTO (tiempo objetivo de recuperacion) | **4 horas**, dentro de la ventana de jornada lectiva | `RECOVERY_TIME_OBJECTIVE_HOURS` |

**Estos valores son una declaracion de referencia, no una cifra institucional
confirmada.** `PD-002` pedia definirlos y quedaba abierta; se cierran aqui con
la misma regla que `RNF-CAP-001` uso para la matricula: se declara un valor
explicito, se deja escrito que es una referencia, y se reemplaza en cuanto el
establecimiento confirme el suyo. Son variables de entorno precisamente para que
ese reemplazo no toque codigo.

Justificacion de los valores:

- **RPO 24 h.** La cadencia sostenible sin infraestructura de replicacion es un
  respaldo nocturno. Un RPO menor exigiria archivado continuo de WAL, que
  `ADR-0009` y el perfil de 1 vCPU / 2 GB de `RNF-CAP-001` no sostienen hoy. La
  perdida maxima es un dia lectivo de capturas.
- **RTO 4 h.** `RNF-DIS-001` acota la disponibilidad comprometida a la jornada
  lectiva y no exige alta disponibilidad ni failover automatico. Cuatro horas
  caben dentro de una jornada y son holgadas frente al tiempo medido.

### Prueba del RTO

`make recovery-drill` restaura ambas pilas de verdad — la base en una base
desechable (`${POSTGRES_DB}_drill`, nunca sobre produccion; el script se niega a
correr sin ese nombre) y los archivos en un directorio aparte — cronometra y
falla si excede el RTO declarado.

Medicion en el entorno de desarrollo (base de esquema completo, sin volumen de
datos de un ciclo real): **1 segundo**, muy dentro del presupuesto de 4 horas.
La cifra escala con el volumen de datos, asi que el simulacro debe repetirse
contra un respaldo de tamano representativo antes de la entrega; el presupuesto
de 4 h existe justamente para absorber ese crecimiento.

## Pendiente: guardia de archivos prohibidos de `pr-validation`

`.github/workflows/pr-validation.yml` rechaza un PR que incluya archivos cuya
ruta contenga `secret`, `credential`, `backup` o `dump`. La regla es correcta
para su proposito -- que un volcado o una credencial no entren al repositorio --
pero acierta tambien al codigo, las pruebas y la documentacion que *hablan* del
tema: `scripts/backup/`, `backend/apps/common/backups.py`,
`backend/tests/integration/test_backup_and_recovery.py` y este mismo documento.

**Con la regla actual, este PR falla la validacion en cuanto apunte a
`develop`.** No se corrige aqui a proposito: modificar un control de CI merece su
propio cambio revisado aparte, no ir de polizon en el PR al que le estorba.

El ajuste propuesto es acotar esa regla a artefactos de datos, exceptuando las
extensiones de codigo y documentacion (`.py`, `.sh`, `.md`, `.yml`, `.jsx`, ...)
y dejando intactas las reglas duras (`.env`, `*.sql`, `*.sqlite3`, `*.pem`,
`media/uploads/`). `backups/` esta en `.gitignore`, asi que un artefacto real
sigue sin poder llegar por esa via. La alternativa -- renombrar el codigo para
esquivar una subcadena -- se descarta: deja nombres contorsionados cuya razon de
ser nadie recuerda seis meses despues.

## Verificacion

| Escenario | Prueba |
| --- | --- |
| Cada pila se respalda y se restaura por su cuenta | `backend/tests/integration/test_backup_and_recovery.py::test_file_stack_backs_up_and_restores_on_its_own`, `...::test_database_stack_backs_up_and_restores_on_its_own` |
| El manifiesto describe una sola pila | `...::test_file_backup_manifest_describes_only_its_own_stack` |
| Restaurar una pila no necesita la otra | `...::test_restoring_files_does_not_need_the_database_backup`, `...::test_database_backup_does_not_produce_a_file_artifact` |
| Un artefacto alterado se rechaza antes de escribir | `...::test_a_tampered_backup_is_refused_before_restoring_anything` |
| Respaldos frescos cumplen el RPO | `...::test_fresh_backups_in_both_stacks_meet_the_declared_rpo` |
| Un respaldo viejo incumple y falla con codigo distinto de cero | `...::test_a_backup_older_than_the_rpo_fails_the_check` |
| La ausencia de respaldo es incumplimiento, no caso neutro | `...::test_a_missing_backup_is_a_breach_not_a_neutral_case` |
| Cada pila se mide por separado | `...::test_each_stack_is_measured_separately` |
| Un manifiesto ilegible se trata como ausente | `...::test_an_unreadable_manifest_is_treated_as_absent_not_as_fresh` |
| Rechazo por autorizacion y contrato del endpoint | `backend/tests/api/test_platform_monitoring_api.py::test_backup_health_reports_each_stack_separately` |

Se corren con `make test-backend`. Las dos pruebas de la pila `database`
necesitan un cliente de PostgreSQL de la misma version mayor que el servidor: la
imagen del backend lo trae fijado, y en un host donde no coincida se omiten en
vez de fallar por el entorno.

## Consulta

`GET /api/v1/platform/backup-health/` devuelve una fila por pila con la edad del
respaldo mas reciente y si cumple el RPO. Requiere el permiso
`platform.monitor`. Nunca agrega las dos pilas en un solo indicador: que la base
este respaldada no dice nada de los archivos.
