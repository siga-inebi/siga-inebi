#!/usr/bin/env sh
# Restauracion de la base de datos en la infraestructura objetivo (RNF-RES-001).
#
# No necesita el respaldo de archivos y no lo menciona: restaurar la base sola
# es un caso valido y previsto. Los documentos quedaran con metadatos sin
# binario hasta que se restaure la otra pila, y esa situacion es DETECTABLE con
# `python manage.py check_document_storage_integrity`, que los reporta como
# `missing` en vez de dejar el sistema en un estado ambiguo.
#
# Uso:
#   DATABASE_NAME=siga_inebi DATABASE_USER=siga_inebi DATABASE_HOST=db \
#   PGPASSWORD=... sh scripts/backup/restore-database.sh [ruta.dump]
#
# Sin argumento toma el respaldo mas reciente de $DATABASE_BACKUP_DIR.

set -eu

script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
. "$script_dir/common.sh"

require_command pg_restore

artifact="${1:-$(latest_artifact "$DATABASE_BACKUP_DIR" .dump)}"
[ -n "$artifact" ] || die "no hay respaldos de base de datos en '$DATABASE_BACKUP_DIR'"

manifest="${artifact%.dump}.manifest.json"
verify_artifact "$artifact" "$manifest"

db_name="${DATABASE_NAME:-siga_inebi}"
db_user="${DATABASE_USER:-siga_inebi}"
db_host="${DATABASE_HOST:-localhost}"
db_port="${DATABASE_PORT:-5432}"

require_command psql
# Se compara contra el servidor DESTINO, no contra el de origen: restaurar en la
# infraestructura objetivo es el punto entero de RNF-RES-001.
require_matching_pg_version \
  "$(pg_restore --version | awk '{print $NF}')" \
  "$(server_major_version "$db_host" "$db_port" "$db_user" postgres)" \
  "restauracion en '$db_name'"

# --clean --if-exists deja la base destino en el estado del respaldo en vez de
# mezclarlo con lo que hubiera: una restauracion parcial silenciosa es peor que
# no restaurar. --exit-on-error para que un fallo a medio camino no se confunda
# con un exito.
pg_restore \
  --clean \
  --if-exists \
  --no-owner \
  --no-privileges \
  --exit-on-error \
  --host="$db_host" \
  --port="$db_port" \
  --username="$db_user" \
  --dbname="$db_name" \
  "$artifact"

echo "base de datos restaurada desde $artifact"
