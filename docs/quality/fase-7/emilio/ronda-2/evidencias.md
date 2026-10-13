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


### RUN-EMI-20261013-01 (seguimiento de INC-010)

SHA evaluado: `df50384313057d596d5415b301b6e1bbef90f053`; inicio 2026-10-13T12:30:36Z, fin 2026-10-13T12:34:33Z (06:30–06:34 del 13/10, America/Guatemala). `inc010_probe.py` y `selfcheck/` son diagnóstico local: el complemento se cargó con `-p inc010_probe` y la autoverificación se copió solo dentro del contenedor efímero. `clock-watch.json` es la salida de `clock_watch.py`.

| Archivo local | Bytes | SHA-256 |
| --- | ---: | --- |
| `build.log` | 2814 | `113b3ac9c299c012b35eb97fabfc5110d01d439ea40708055163294fef21cb6e` |
| `clock-watch.json` | 589 | `ccf737eb0c6bca2ce42889568b2fbeeed80d448a157fe07c54f69da7bc1f6232` |
| `clock_watch.py` | 895 | `9ec1dc2a2b14aa149b2d911b6c6c3bebe3f7c2db7dc5d372fbe8f9c858b29b79` |
| `database-start.log` | 205 | `9173a8eacb7d96280fd632264518a3c4aa0d718a1fdb86d7c5adef793302012b` |
| `execution.log` | 1820 | `15a60fa56c60b7bb76859061eefd92d4dbf5646d6051af9303078927e6bbda29` |
| `exit-code.txt` | 2 | `9a271f2a916b0b6ee6cecb2426f0b3206ef074578be55d9bc94f6f3fe3ab86aa` |
| `finished-utc.txt` | 21 | `512cbb2d794639d86deebe503f7fa3c90084a94850658a43c82e685cf46fa8e1` |
| `git-sha.txt` | 41 | `2e5ee949549307145187f28115a9dc9f6d01c391db84a644f0e57cf9f3d99f63` |
| `git-status.txt` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `inc010_probe.py` | 3151 | `11c942a8216be9c17ca75943405b32fd66a76b36fc14e3022fc62e67f28f5de5` |
| `junit-1.xml` | 43400 | `8bdc8b8bdbc95d1f1c57dfc6c0259e51c8b5439989f0a9c6ed0520198592a83c` |
| `junit-2.xml` | 45265 | `7a42a93aa3cb3a921eba97cb7056c156c6fce7e5f031385aa50e17a4ca738db8` |
| `junit-3.xml` | 49232 | `96bdcb6c57b57fd3d1224a195c09e22ba8798c02a14df52a8da640fb987ff75a` |
| `junit-4.xml` | 43400 | `f1733c07a3e67327dbe77a44d6be725cf38de4c23383bbab473f862f5917fa26` |
| `junit-5.xml` | 43400 | `5c9b1ecea1d4277579a59212eaae4f250ca5cac20491e5283882b4e1e5ea7bcd` |
| `junit-6.xml` | 43400 | `8a6474da7312bc97e81fa0215de97424b77ff27b98881618e50ae75e9fd66325` |
| `junit-7.xml` | 43400 | `0a8df777b0005c45c08632c99eb644b265ebd6028d278cc6b877e7eddf08e837` |
| `junit-8.xml` | 44849 | `16057ae071a775b16f43033f38e28838664cb5f7449b6e05833be0ff1f5ac252` |
| `junit-9.xml` | 43400 | `a247556258c29f913d4e4da36f63a4cf5a921f24fc793d0adc4d79aa70e3fa3b` |
| `junit-10.xml` | 43400 | `c50e28dd5173c765206f930394984d818698075b21f3e101df3cb8fb7ad43420` |
| `postgresql-version.txt` | 89 | `683ecaee6342addcdb0697c81ee983b7085b774acade718fe5f7718a81c6178e` |
| `probe-2.jsonl` | 421 | `0aa004f769ccf3b032dc5142fe12cf7ff860ba499d4708322032dd122caeab8a` |
| `probe-3.jsonl` | 827 | `fd8e7eed04e41d03c69a8fdfcd7b4636e20255df04ad2b89061b97a0c770ef0b` |
| `probe-8.jsonl` | 407 | `5eeade90001ffd0366bdd80986fa28d4333548640976c3b18399d30a174414cc` |
| `probe-selfcheck.jsonl` | 894 | `0cfb259c731bdefbf5eed5721f8d064a69b74ee07870c0f0eaeadb77a187ed6d` |
| `run.sh` | 744 | `a75842e0df6e61ab6f6d3abd751b26402772fb3db1802f02bd001615b3fd797c` |
| `runtime-versions.txt` | 35 | `3117e34127323b373135337b0eee9022afdc176028bc41d2a5b6809b27445a8c` |
| `selfcheck/test_probe_selfcheck.py` | 976 | `c86fb9b96b9669e5e16869cc63c2b6951337852350746e33c03593ab5b2fcb92` |
| `started-utc.txt` | 21 | `b3bb7c3c2ad47bfe564c829570caf7852525c60f4bcffb48f844dec2b87290ed` |
