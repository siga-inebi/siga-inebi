# Evidencia de la segunda ronda

Artefactos locales ignorados por Git en `docs/quality/fase-7/evidence/RUN-EMI-20261012-04/` y `RUN-EMI-20261012-05/`. Los hashes permiten comprobar identidad; los archivos originales deben adjuntarse por el canal de entrega acordado si el revisor necesita inspeccionarlos.

- SHA evaluado: `4bf2b543ab669646045f102c200047fff121f904`; `git status --porcelain` vacío al iniciar ambas corridas.
- RUN-04: inicio 2026-10-13T02:44:55Z, fin 2026-10-13T02:45:41Z. RUN-05: inicio 2026-10-13T02:46:02Z, fin 2026-10-13T02:55:02Z (20:44–20:55 del 12/10, America/Guatemala).
- `run.sh` contiene el comando exacto ejecutado dentro de `backend-test`.
- RUN-05 no tiene `exit-code` por iteración: el resultado de cada una sale de su `junit-N.xml` y del resumen de pytest en `execution.log`. El `exit-code.txt` de RUN-05 es el del ciclo completo, no el de cada pytest.
- Operador técnico: Claude Code para Emilio. Revisión de Josué pendiente.

Los CSV publicados derivan de JUnit y contienen únicamente identificadores de pruebas, nivel, estado, duración y SHA. No contienen cuentas, contraseñas ni datos institucionales reales.

### RUN-EMI-20261012-04

| Archivo local | Bytes | SHA-256 |
| --- | ---: | --- |
| `build.log` | 3036 | `55e14cc7266d5f95b027247432a7e04fb732ec25adacfccc3e2501a455d259e1` |
| `build-exit-code.txt` | 2 | `9a271f2a916b0b6ee6cecb2426f0b3206ef074578be55d9bc94f6f3fe3ab86aa` |
| `database-exit-code.txt` | 2 | `9a271f2a916b0b6ee6cecb2426f0b3206ef074578be55d9bc94f6f3fe3ab86aa` |
| `database-start.log` | 103 | `af0ae44d60dfcc4cc6380e972339020ee0727798188dc52cb32b1a432e50c5df` |
| `execution.log` | 8096 | `9671961dcb34e840609399a013c002155375b89f0b2e85c060224f94e65fc382` |
| `exit-code.txt` | 2 | `9a271f2a916b0b6ee6cecb2426f0b3206ef074578be55d9bc94f6f3fe3ab86aa` |
| `finished-utc.txt` | 21 | `c05563d202083337a7c266ee3407226954e48e8cb9ad40672b8bc5cb81d401d1` |
| `git-sha.txt` | 41 | `16666c04ecbeee0da66f88ddc10897506daee9758a24030e683b122d42a5a087` |
| `git-status.txt` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `junit.xml` | 4265 | `2c978889a68b0a1c18b0b9f08eedeaab9487c5f0c831d6cce18b9700873761ff` |
| `postgresql-version.txt` | 89 | `683ecaee6342addcdb0697c81ee983b7085b774acade718fe5f7718a81c6178e` |
| `run.sh` | 353 | `0d81d63037cfe8b63fc04abb9743e57858e9f1c68b31a081af120333f435d2bf` |
| `runtime-versions.txt` | 35 | `3117e34127323b373135337b0eee9022afdc176028bc41d2a5b6809b27445a8c` |
| `started-utc.txt` | 21 | `003f88bcb4141a8f06b197850d42584786b8761af51a1ecaa1a3e1838b6e5c9e` |

### RUN-EMI-20261012-05

| Archivo local | Bytes | SHA-256 |
| --- | ---: | --- |
| `execution.log` | 1125 | `8d721c5ff89297a17a6dcf4bae3342e606224d6dcd607385e638d9a020bccb07` |
| `exit-code.txt` | 2 | `9a271f2a916b0b6ee6cecb2426f0b3206ef074578be55d9bc94f6f3fe3ab86aa` |
| `finished-utc.txt` | 21 | `362cd019c68fcda3fa572c5b236e2eeb1bb882c8d87de637c36ddd4365665e8c` |
| `git-sha.txt` | 41 | `16666c04ecbeee0da66f88ddc10897506daee9758a24030e683b122d42a5a087` |
| `git-status.txt` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `junit-1.xml` | 42843 | `5078cfdc868fc9ff031436407b0d70851a3a4a53b5392001946217c0027bd67b` |
| `junit-2.xml` | 42843 | `854f7d5099df3e8f849e2183c9fdde9ab50ddf65df661d5f2884531e2e7a8ede` |
| `junit-3.xml` | 44677 | `9d263c5fd9489ce59c1e43cc27732899d45488ac164a406144c771817a65da5b` |
| `junit-4.xml` | 42843 | `de6035cf9637e96a7cb73fbd1591d266ce8fee1777ccf6976dd2dc49f2973eb0` |
| `junit-5.xml` | 42843 | `8e957b3fd9190e088210c372d945a5caa4b0ca0b8db1ce3d8361323b41dfc2bb` |
| `junit-6.xml` | 42843 | `3e8e0c482b95b78d7d7e0b9be0698bd4c8b05137e6db67dee807e9ee85553d87` |
| `junit-7.xml` | 42843 | `6a7c74df952aa73c7f99c3dc31a2486743fc366c9c35fedcf8a2dbac7fe06f98` |
| `junit-8.xml` | 42843 | `f839ef84309f971946ecc4207e719c99e963880eb995c2cade416f3c9719a469` |
| `junit-9.xml` | 42843 | `69424f2da03f69128b15c3ff43b8275f0495588a6446726c8f96aeb37a1edb2a` |
| `junit-10.xml` | 42843 | `e649acc3e004cf6b156d44b1263b4fd076814aa9a50f399280e364399964cfe5` |
| `run.sh` | 481 | `8fad76776b544578a91887f25731772eda2259d98740e47b6ae72127c5d4d1b4` |
| `started-utc.txt` | 21 | `f28da04eaa448a5ca8bf122c7eabe7e9da9911437ec4238ff5722c0f2bf17728` |

