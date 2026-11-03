# Security Tooling

## Backend

- `bandit -q -r apps config`
- `pip-audit -r requirements/dev.txt`

## Politica actual

- Hallazgos explotables con fix disponible deben corregirse antes de PR.
- Hallazgos sin version instalable disponible pueden quedar en allowlist temporal documentada.
- Placeholders de entorno como `insecure-development-key` se marcan con `# nosec` cuando no representan secreto real.

## Allowlist temporal actual

Vacia: `pip-audit` corre sin `--ignore-vuln`.

## Excepciones retiradas

El 2026-10-12, `pip-audit -r requirements/dev.txt` sin excepciones resolvio
versiones ya corregidas de estas dependencias, por lo que sus
excepciones se retiraron. Si una resolucion vuelve a una version vulnerable,
CI debe fallar en lugar de ocultarlo.

| ID | Paquete y version afectada | Resuelto el 2026-10-12 |
| --- | --- | --- |
| `PYSEC-2026-1845` (CVE-2025-71176) | `pytest==8.4.1` | `pytest==9.0.3` fijado en `requirements/dev.txt` |
| `GHSA-6v7p-g79w-8964` | `msgpack==1.1.2` | `msgpack 1.2.3` |
| `PYSEC-2026-1375`, `PYSEC-2026-1374` | `filelock==3.19.1` | `filelock 4.1.1` |
| `PYSEC-2026-2275` | `requests==2.32.5` | `requests 2.34.2` |
| `PYSEC-2026-142`, `PYSEC-2026-141` | `urllib3==2.6.3` | `urllib3 2.8.0` |

Salvo `pytest`, son dependencias transitivas sin version fijada en `requirements/`; la version efectiva
depende del indice al instalar.
