#!/usr/bin/env sh
# Restauracion de la pila de archivos adjuntos (RNF-RES-001).
#
# Independiente de la base de datos: no la consulta ni la necesita. Restaurar
# los archivos sin la base deja binarios que ninguna fila referencia todavia,
# que es inofensivo y reversible.
#
# Uso:
#   MEDIA_ROOT=backend/media sh scripts/backup/restore-files.sh [ruta.tar.gz]
#
# Sin argumento toma el respaldo mas reciente de $FILES_BACKUP_DIR.

set -eu

script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
. "$script_dir/common.sh"

require_command tar

artifact="${1:-$(latest_artifact "$FILES_BACKUP_DIR" .tar.gz)}"
[ -n "$artifact" ] || die "no hay respaldos de archivos en '$FILES_BACKUP_DIR'"

manifest="${artifact%.tar.gz}.manifest.json"
verify_artifact "$artifact" "$manifest"

media_root="${MEDIA_ROOT:-backend/media}"
mkdir -p "$media_root"

# Se extrae SOBRE el destino sin borrarlo. Borrar el directorio seria destruir
# archivos que el respaldo quiza no contiene, y esta operacion se ejecuta bajo
# presion, cuando menos conviene un paso irreversible.
tar -xzf "$artifact" -C "$media_root"

echo "archivos restaurados desde $artifact hacia $media_root"
