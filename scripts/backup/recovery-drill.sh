#!/usr/bin/env sh
# Simulacro de recuperacion: mide el RTO real (RNF-RES-002).
#
# El requerimiento pide que el tiempo objetivo de recuperacion este "declarado y
# probado antes de la entrega". Declararlo es escribir un numero; probarlo es
# esto: restaurar de verdad en una base desechable, cronometrar, y comparar
# contra el objetivo.
#
# Se restaura SOBRE UNA BASE APARTE ($DRILL_DATABASE_NAME), nunca sobre la de
# produccion. Si esa variable no esta puesta, el script se niega a correr: un
# simulacro que borra la base real no es un simulacro.
#
# Uso:
#   DRILL_DATABASE_NAME=siga_inebi_drill DATABASE_USER=siga_inebi \
#   DATABASE_HOST=localhost PGPASSWORD=... \
#   sh scripts/backup/recovery-drill.sh

set -eu

script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
. "$script_dir/common.sh"

require_command pg_restore
require_command psql
require_command tar

drill_db="${DRILL_DATABASE_NAME:-}"
[ -n "$drill_db" ] ||
  die "defina DRILL_DATABASE_NAME con una base desechable; nunca se restaura sobre la de produccion"

db_user="${DATABASE_USER:-siga_inebi}"
db_host="${DATABASE_HOST:-localhost}"
db_port="${DATABASE_PORT:-5432}"
rto_hours="${RECOVERY_TIME_OBJECTIVE_HOURS:-4}"

db_artifact=$(latest_artifact "$DATABASE_BACKUP_DIR" .dump)
[ -n "$db_artifact" ] || die "no hay respaldo de base de datos que restaurar"
files_artifact=$(latest_artifact "$FILES_BACKUP_DIR" .tar.gz)
[ -n "$files_artifact" ] || die "no hay respaldo de archivos que restaurar"

drill_media="${DRILL_MEDIA_ROOT:-$(mktemp -d)}"
mkdir -p "$drill_media"

started=$(date -u +%s)

echo "== 1/2 base de datos =="
psql --host="$db_host" --port="$db_port" --username="$db_user" --dbname=postgres \
  -v ON_ERROR_STOP=1 -c "DROP DATABASE IF EXISTS \"$drill_db\";"
psql --host="$db_host" --port="$db_port" --username="$db_user" --dbname=postgres \
  -v ON_ERROR_STOP=1 -c "CREATE DATABASE \"$drill_db\";"
DATABASE_NAME="$drill_db" sh "$script_dir/restore-database.sh" "$db_artifact"

echo "== 2/2 archivos =="
MEDIA_ROOT="$drill_media" sh "$script_dir/restore-files.sh" "$files_artifact"

finished=$(date -u +%s)
elapsed=$((finished - started))
budget=$((rto_hours * 3600))

cat <<REPORT

Simulacro de recuperacion
- base restaurada en: $drill_db
- archivos restaurados en: $drill_media
- duracion: ${elapsed}s
- RTO declarado: ${rto_hours}h (${budget}s)
REPORT

if [ "$elapsed" -gt "$budget" ]; then
  die "el simulacro tardo ${elapsed}s y excede el RTO declarado de ${budget}s"
fi

echo "resultado: dentro del RTO declarado"
