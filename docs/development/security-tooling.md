# Security Tooling

## Backend

- `bandit -q -r apps config`
- `pip-audit -r requirements/dev.txt`

## Politica actual

- Hallazgos explotables con fix disponible deben corregirse antes de PR.
- Hallazgos sin version instalable disponible pueden quedar en allowlist temporal documentada.
- Placeholders de entorno como `insecure-development-key` se marcan con `# nosec` cuando no representan secreto real.

## Allowlist temporal actual

- `PYSEC-2026-1845` sobre `pytest==8.4.1`.
- `GHSA-6v7p-g79w-8964` sobre `msgpack==1.1.2`.
- `PYSEC-2026-1375` y `PYSEC-2026-1374` sobre `filelock==3.19.1`.
- `PYSEC-2026-2275` sobre `requests==2.32.5`.
- `PYSEC-2026-142` y `PYSEC-2026-141` sobre `urllib3==2.6.3`.

Motivo: `pip-audit` reporta versiones de correccion no disponibles en indice utilizable por entorno local actual. Revisar allowlist en siguiente actualizacion de dependencias.
