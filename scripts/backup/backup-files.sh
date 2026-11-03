#!/usr/bin/env sh
# Respaldo de la pila de archivos adjuntos, independiente del de la base de
# datos (RNF-RES-001).
#
# Los binarios viven fuera de la base (`docs/architecture/file-storage-strategy.md`),
# asi que tienen su propio esquema, su propia cadencia y su propia
# restauracion. Este script no sabe nada de PostgreSQL y no debe saberlo.
#
# Uso:
#   MEDIA_ROOT=backend/media sh scripts/backup/backup-files.sh
#
# Salida: $FILES_BACKUP_DIR/siga-files-<UTC>.tar.gz y su .manifest.json

set -eu

script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
. "$script_dir/common.sh"

require_command tar

media_root="${MEDIA_ROOT:-backend/media}"
[ -d "$media_root" ] || die "no existe el directorio de archivos '$media_root'"

mkdir -p "$FILES_BACKUP_DIR"

stamp=$(timestamp)
artifact="$FILES_BACKUP_DIR/siga-files-$stamp.tar.gz"
manifest="$FILES_BACKUP_DIR/siga-files-$stamp.manifest.json"

# Se archiva el CONTENIDO del directorio, no el directorio: asi el destino puede
# tener el suyo en otra ruta, que es el caso normal al restaurar en otra
# infraestructura.
tar -czf "$artifact" -C "$media_root" .

file_count=$(tar -tzf "$artifact" | grep -vc '/$' || true)

write_manifest "$manifest" "files" "$artifact" ",
  \"source_path\": \"$media_root\",
  \"file_count\": $file_count,
  \"format\": \"tar.gz\""

echo "$artifact"
