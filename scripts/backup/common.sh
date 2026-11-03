#!/usr/bin/env sh
# Piezas compartidas por los scripts de respaldo y restauracion (RNF-RES-001).
#
# Deliberadamente comun SOLO en plomeria: rutas, manifiestos y comprobacion de
# integridad. Ningun script de base de datos llama a uno de archivos ni al
# reves, porque el requerimiento pide que los dos esquemas sean independientes
# y una dependencia compartida entre ellos seria justo lo contrario.
#
# No contiene secretos. La contrasena viaja por PGPASSWORD, que el operador
# exporta en su entorno y este codigo nunca imprime.

set -eu

BACKUP_ROOT="${BACKUP_ROOT:-./backups}"
DATABASE_BACKUP_DIR="${DATABASE_BACKUP_DIR:-$BACKUP_ROOT/database}"
FILES_BACKUP_DIR="${FILES_BACKUP_DIR:-$BACKUP_ROOT/files}"

# `pg_dump`/`pg_restore`/`psql` solo leen PGPASSWORD. El resto del repositorio
# habla en DATABASE_PASSWORD, asi que se puentea aqui para no obligar al
# operador a exportar la misma credencial con dos nombres. Nunca se imprime.
if [ -z "${PGPASSWORD:-}" ] && [ -n "${DATABASE_PASSWORD:-}" ]; then
  PGPASSWORD="$DATABASE_PASSWORD"
  export PGPASSWORD
fi

timestamp() {
  date -u +%Y%m%dT%H%M%SZ
}

iso_now() {
  date -u +%Y-%m-%dT%H:%M:%SZ
}

die() {
  echo "error: $*" >&2
  exit 1
}

require_command() {
  command -v "$1" >/dev/null 2>&1 || die "falta el comando '$1' en este host"
}

checksum_of() {
  # sha256sum en Linux, shasum en entornos BSD/macOS.
  if command -v sha256sum >/dev/null 2>&1; then
    sha256sum "$1" | cut -d' ' -f1
  else
    shasum -a 256 "$1" | cut -d' ' -f1
  fi
}

size_of() {
  # -c%s es GNU; -f%z es BSD. El tamano va al manifiesto, asi que se resuelve
  # aqui y no en cada script.
  stat -c%s "$1" 2>/dev/null || stat -f%z "$1"
}

# Escribe el manifiesto junto al artefacto. El manifiesto describe UN artefacto
# y nunca menciona al otro esquema: es lo que permite restaurar uno solo.
write_manifest() {
  manifest_path="$1"
  kind="$2"
  artifact_path="$3"
  extra="$4"

  cat >"$manifest_path" <<JSON
{
  "kind": "$kind",
  "artifact": "$(basename "$artifact_path")",
  "created_at": "$(iso_now)",
  "size_bytes": $(size_of "$artifact_path"),
  "sha256": "$(checksum_of "$artifact_path")"$extra
}
JSON
}

# Un respaldo que no se puede verificar no es un respaldo. Se comprueba antes de
# restaurar, nunca despues.
verify_artifact() {
  artifact_path="$1"
  manifest_path="$2"

  [ -f "$artifact_path" ] || die "no existe el artefacto '$artifact_path'"
  [ -f "$manifest_path" ] || die "no existe el manifiesto '$manifest_path'"

  expected=$(sed -n 's/.*"sha256": "\([a-f0-9]*\)".*/\1/p' "$manifest_path")
  [ -n "$expected" ] || die "el manifiesto '$manifest_path' no declara sha256"

  actual=$(checksum_of "$artifact_path")
  [ "$expected" = "$actual" ] ||
    die "checksum distinto en '$artifact_path': el respaldo esta corrupto o incompleto"
}

major_version() {
  # "18.6" -> "18"; "16beta1" -> "16".
  echo "$1" | sed -n 's/^\([0-9][0-9]*\).*/\1/p'
}

server_major_version() {
  psql --host="$1" --port="$2" --username="$3" --dbname="$4" \
    -tAc "SHOW server_version;" 2>/dev/null | head -n 1
}

# Cliente y servidor tienen que compartir version mayor.
#
# Sin esto el fallo llega como "unrecognized configuration parameter
# transaction_timeout" a mitad de una restauracion, que es justo cuando menos se
# puede investigar. El requerimiento exige restaurar EN LA INFRAESTRUCTURA
# OBJETIVO, asi que la version de las herramientas es parte del respaldo, no un
# detalle del host que lo produjo: por eso el manifiesto la guarda.
require_matching_pg_version() {
  client_version="$1"
  server_version="$2"
  context="$3"

  client_major=$(major_version "$client_version")
  server_major=$(major_version "$server_version")

  [ -n "$server_major" ] || return 0

  [ "$client_major" = "$server_major" ] || die "$(cat <<MSG
version de PostgreSQL incompatible ($context)
  cliente: $client_version (mayor $client_major)
  servidor: $server_version (mayor $server_major)
Use un cliente de la misma version mayor que la infraestructura objetivo. La
imagen 'postgres:16-alpine' de compose.yml trae uno que coincide:
  docker compose exec db pg_dump ...
MSG
)"
}

# El artefacto mas reciente de un directorio, por nombre: los nombres llevan
# marca de tiempo UTC ordenable, asi que no depende de la mtime del archivo,
# que un copiado entre hosts reescribe.
latest_artifact() {
  directory="$1"
  extension="$2"
  ls -1 "$directory"/*"$extension" 2>/dev/null | sort | tail -n 1
}
