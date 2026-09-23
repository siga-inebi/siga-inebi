#!/usr/bin/env sh
# Respaldo de la base de datos, independiente del de archivos (RNF-RES-001).
#
# Formato `custom` de pg_dump y no SQL plano: es lo que permite restaurar en una
# infraestructura objetivo distinta (otra version menor, otro nombre de base,
# solo algunas tablas) con pg_restore, y ademas viene comprimido.
#
# Uso:
#   DATABASE_NAME=siga_inebi DATABASE_USER=siga_inebi DATABASE_HOST=db \
#   PGPASSWORD=... sh scripts/backup/backup-database.sh
#
# Salida: $DATABASE_BACKUP_DIR/siga-db-<UTC>.dump y su .manifest.json

set -eu

script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
. "$script_dir/common.sh"

require_command pg_dump

db_name="${DATABASE_NAME:-siga_inebi}"
db_user="${DATABASE_USER:-siga_inebi}"
db_host="${DATABASE_HOST:-localhost}"
db_port="${DATABASE_PORT:-5432}"

require_command psql
require_matching_pg_version \
  "$(pg_dump --version | awk '{print $NF}')" \
  "$(server_major_version "$db_host" "$db_port" "$db_user" "$db_name")" \
  "respaldo de '$db_name'"

mkdir -p "$DATABASE_BACKUP_DIR"

stamp=$(timestamp)
artifact="$DATABASE_BACKUP_DIR/siga-db-$stamp.dump"
manifest="$DATABASE_BACKUP_DIR/siga-db-$stamp.manifest.json"

# --no-owner y --no-privileges: el destino puede tener otro rol dueno, y un dump
# que insiste en el rol de origen falla al restaurar en la infraestructura
# objetivo, que es exactamente lo que este requerimiento tiene que garantizar.
pg_dump \
  --format=custom \
  --no-owner \
  --no-privileges \
  --host="$db_host" \
  --port="$db_port" \
  --username="$db_user" \
  --dbname="$db_name" \
  --file="$artifact"

server_version=$(pg_dump --version | awk '{print $NF}')

write_manifest "$manifest" "database" "$artifact" ",
  \"database_name\": \"$db_name\",
  \"pg_dump_version\": \"$server_version\",
  \"format\": \"custom\""

echo "$artifact"
