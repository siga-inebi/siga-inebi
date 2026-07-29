#!/usr/bin/env bash
set -e

printf "This will remove development PostgreSQL volume. Continue? [y/N] "
read -r answer

if [ "$answer" != "y" ] && [ "$answer" != "Y" ]; then
  echo "Aborted."
  exit 1
fi

docker compose down -v
