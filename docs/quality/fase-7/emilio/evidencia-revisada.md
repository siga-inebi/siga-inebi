# Evidencia revisada — RUN-EMI-20261012-01, 02 y 03

Esta referencia publica resultados sintéticos revisados. Los artefactos crudos
permanecen locales en `docs/quality/fase-7/evidence/RUN-EMI-20261012-0N/`,
ignorados por Git conforme a la política actual. Su entrega a revisores está
pendiente; los hashes permiten comprobar integridad, no sustituyen su acceso.

- SHA evaluado: `5ed5fd24d02f494053c53dbbbafe50a8412534e5`.
- Python 3.11.15, Django 5.2.17, pytest 8.4.1, PostgreSQL 16.11; Node 22.23.2, Vitest 4.1.11.
- [Resultados por caso](resultados-pruebas.csv), transcritos de JUnit y cotejados con los 329 casos del inventario.
- Operador técnico: Claude Code para Emilio. Revisión de Josué pendiente.
- Ningún artefacto contiene secretos, cookies, tokens ni datos institucionales.

## Comandos ejecutados

Desde la raíz del repositorio; el marcador de directorio representa la ruta
absoluta local del directorio de cada corrida. La imagen de backend se construyó con
`docker compose -p siga_inebi_emilio_qa -f compose.yml -f compose.test.yml build backend-test`
y se inició únicamente `db-test` del mismo proyecto. La carpeta de evidencia
necesita permiso de escritura para el usuario del contenedor.

RUN-EMI-20261012-01 (backend):

```text
docker compose -p siga_inebi_emilio_qa -f compose.yml -f compose.test.yml run --rm -v <absolute-evidence-directory>:/evidence backend-test sh -lc 'python --version > /evidence/runtime-versions.txt && python -m django --version >> /evidence/runtime-versions.txt && pytest --version >> /evidence/runtime-versions.txt && python manage.py migrate --noinput && pytest tests/unit/test_qr.py tests/unit/test_attendance_services.py tests/api/test_attendance_api.py tests/permissions/test_attendance_permissions.py tests/integration/test_attendance.py tests/integration/test_attendance_performance.py --no-cov --junitxml=/evidence/junit.xml -q'
```

RUN-EMI-20261012-02 (frontend):

```text
docker compose run --rm --no-deps -v <absolute-evidence-directory>:/evidence frontend sh -lc 'node --version > /evidence/runtime-versions.txt && npx vitest --version >> /evidence/runtime-versions.txt && npx vitest --run src/test/AttendancePage.test.jsx src/test/CameraPreviewWindow.test.jsx src/test/camera.test.js src/test/useBatchSubmit.test.jsx --reporter=default --reporter=junit --outputFile.junit=/evidence/junit.xml'
```

Diagnóstico previo a la 03 (sin JUnit; salida en consola: `1 passed`):

```text
docker compose -p siga_inebi_emilio_qa -f compose.yml -f compose.test.yml run --rm backend-test sh -lc "python manage.py migrate --noinput && pytest 'tests/api/test_attendance_api.py::test_close_jornada_creates_alert_for_permanence_without_closure' --no-cov -q"
```

RUN-EMI-20261012-03 (diagnóstico backend, misma selección que la 01):

```text
docker compose -p siga_inebi_emilio_qa -f compose.yml -f compose.test.yml run --rm -v <absolute-evidence-directory>:/evidence backend-test sh -lc 'python manage.py migrate --noinput && pytest tests/unit/test_qr.py tests/unit/test_attendance_services.py tests/api/test_attendance_api.py tests/permissions/test_attendance_permissions.py tests/integration/test_attendance.py tests/integration/test_attendance_performance.py --no-cov --junitxml=/evidence/junit.xml -q'
```

## Integridad de artefactos locales

### RUN-EMI-20261012-01

| Archivo local | Bytes | SHA-256 |
| --- | ---: | --- |
| `build-exit-code.txt` | 2 | `9a271f2a916b0b6ee6cecb2426f0b3206ef074578be55d9bc94f6f3fe3ab86aa` |
| `build.log` | 2930 | `f599e551740344240cfaf4a49d1f75526174545a0f3ce2a7466a046da0ddc755` |
| `command.txt` | 667 | `89035b21137fccde564672a5604bce72fc24620d6d49bbcbf4dcc285096ff1e0` |
| `database-exit-code.txt` | 2 | `9a271f2a916b0b6ee6cecb2426f0b3206ef074578be55d9bc94f6f3fe3ab86aa` |
| `database-start.log` | 301 | `4e124e02e74d36815f2758d8cba0500c138ea46c729f21285718703bb8c69e85` |
| `environment.json` | 707 | `0610cd2396c45c420bed18e183aa6defc4804a898dc00455742220eaa0892107` |
| `execution.log` | 6029 | `2348d099ef4c7ede95abb2f57d653ce4c659011896cab4c936d3a692dc74d1dd` |
| `exit-code.txt` | 2 | `4355a46b19d348dc2f57c046f8ef63d4538ebb936000f3c9ee954a27460dd865` |
| `finished-utc.txt` | 21 | `8dc7d4082587fe29086109cc6c71fe4a77db0065b18510255e0361f8e446bee7` |
| `git-sha.txt` | 41 | `dadfb59296ad12c8cd9b38b47c0da5bc2818d472d7989f88e71f6ee6fc679c6b` |
| `git-status.txt` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `junit.xml` | 45299 | `9390b4c40ca774595ac051a1d93528d4c806bf0d7941e43239e0b3750fc4ddcc` |
| `postgresql-version.txt` | 89 | `683ecaee6342addcdb0697c81ee983b7085b774acade718fe5f7718a81c6178e` |
| `runtime-versions.txt` | 35 | `3117e34127323b373135337b0eee9022afdc176028bc41d2a5b6809b27445a8c` |
| `started-utc.txt` | 21 | `10c8abebdc6b845042b87193352e1061a186caafd6cd2e9e184bcd5585badd43` |

### RUN-EMI-20261012-02

| Archivo local | Bytes | SHA-256 |
| --- | ---: | --- |
| `command.txt` | 329 | `7c78e62c991d429b9833bf3a6d44129a6623a87ccd8a5d02ded8696ec4806387` |
| `execution.log` | 2547 | `68c356448bb818e3b8dae9ada23a21de3e0b08db7327e91d97141151852b7766` |
| `exit-code.txt` | 2 | `9a271f2a916b0b6ee6cecb2426f0b3206ef074578be55d9bc94f6f3fe3ab86aa` |
| `finished-utc.txt` | 21 | `71d60ffee8e7a8fb29a620eeb471da4f17a1983011d3f412d65873b9656d0c89` |
| `git-sha.txt` | 41 | `dadfb59296ad12c8cd9b38b47c0da5bc2818d472d7989f88e71f6ee6fc679c6b` |
| `git-status.txt` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `junit.xml` | 6137 | `ce999aa376a760bf448fe6dd8eea70da7f122ece5090f9c48b8d0e513588775d` |
| `runtime-versions.txt` | 47 | `f47a992e21d968cc02b3ceac9cdcfe6c4afb174ec90a592e593748a851207930` |
| `started-utc.txt` | 21 | `2ea176da0b491f3dcbc5f80f10427a4ee79ad5e97a22ebf897091e6eef6e287e` |

### RUN-EMI-20261012-03

| Archivo local | Bytes | SHA-256 |
| --- | ---: | --- |
| `command.txt` | 328 | `601a59a10aba725e45a16bfb5d7c634cd88bb35b8ff80b1bce997ebe12d997e2` |
| `execution.log` | 3127 | `ee034c4406937b864b73ba9d859ca71cd26098b7c6e2a82057d48b8a2ce6f567` |
| `exit-code.txt` | 2 | `9a271f2a916b0b6ee6cecb2426f0b3206ef074578be55d9bc94f6f3fe3ab86aa` |
| `finished-utc.txt` | 21 | `2f6481f920d6c0cbfb225b6550cf84ee707f9b65e6a9721c3bc2c4899c635fa5` |
| `git-sha.txt` | 41 | `dadfb59296ad12c8cd9b38b47c0da5bc2818d472d7989f88e71f6ee6fc679c6b` |
| `junit.xml` | 42843 | `39034960a60ba43438709e7dd2f9df7cf3de2fe915338443262632ef7c056d94` |
| `started-utc.txt` | 21 | `be06d591608379bc6dd31ec8800f64b737f1175fc5701f9a821f6901ff15976c` |
