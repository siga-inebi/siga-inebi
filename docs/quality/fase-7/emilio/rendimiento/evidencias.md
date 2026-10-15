# Evidencia del informe de rendimiento

Artefactos locales ignorados por Git en `docs/quality/fase-7/evidence/`. Los hashes permiten comprobar identidad; los archivos deben adjuntarse por el canal acordado si un revisor necesita inspeccionarlos. `seed.json` contiene solo usuarios, contraseña y códigos sintéticos de la siembra de carga.

| Corrida | Qué es | Inicio / fin (UTC) |
| --- | --- | --- |
| RUN-EMI-20261014-01 | Serie del desfase del reloj, 180 s | 2026-10-15T05:36:54Z |
| RUN-EMI-20261015-01 | Carga pico (sin pausa), 3 rondas; `intento-1/` conserva el intento fallido por la salida de `manage.py shell` | 2026-10-15T06:16:46Z – 06:17:12Z |
| RUN-EMI-20261015-02 | Carga normal (pausa 2 s), 3 rondas | 2026-10-15T06:18:21Z – 06:22:59Z |

La serie del reloj se nombró con la fecha local del 14 de octubre; su inicio en UTC ya es el 15.

## RUN-EMI-20261014-01

| Archivo | Bytes | SHA-256 |
| --- | ---: | --- |
| `clock-series.csv` | 12317 | `472966e425e2db8adda0ae67dc4025aba373d9e2e7c86a25d89b8f9bdff6c685` |
| `clock-series.log` | 48 | `a414d7cb88a54cae16a15b4f2abf7abc68b9dcf956e7d56f35b3ac0afa20a5c9` |
| `clock_series.py` | 889 | `8723fe4ee8d9521b645ebc5b25a88925c44cfa50277db7d83d6ccaa9e75a6eaa` |
| `finished-utc.txt` | 21 | `f1d273d526b8a17f8da8cb10cbb849ebf9e295e03bc7573f9f695ff0b61773de` |
| `git-sha.txt` | 41 | `0f2b8e302082214f12386af2194c1ae60688882e87fc661fdec6003ff081a337` |
| `kernel.txt` | 34 | `600c01e56d5afd93f0ecd74ff4ebb5ef91623d779bbba04388a866c3b581fc92` |
| `started-utc.txt` | 21 | `f2a3d62e9db53fe2de833251bc0d46199b3a52bd78d1d9439c45cf79995fe37e` |

## RUN-EMI-20261015-01

| Archivo | Bytes | SHA-256 |
| --- | ---: | --- |
| `backend-access.log` | 16771 | `129a781684a2bc561b7d3cc4028d5e326620e6233cd240219cc300558a7e9173` |
| `backend-limits.txt` | 34 | `a061be1c2963311e1f66b9fd106bf9ebfbc6f6d38447578b0e7ce4e0dcb51912` |
| `build.log` | 2865 | `b14425fe04aa3588b40900698730da57f557e047abd90d8da821c9d5d249ebdc` |
| `docker-stats.csv` | 1253 | `fd1a4760aa3b7ba0a66e2f8d9f782435eab531084233c2c26188421cf117a33c` |
| `exit-code.txt` | 2 | `9a271f2a916b0b6ee6cecb2426f0b3206ef074578be55d9bc94f6f3fe3ab86aa` |
| `finished-utc.txt` | 21 | `5e8a485ee2361c0410c1c0cd5852c2ad5eb400a162ef27602b4b7e81edd0c86a` |
| `git-sha.txt` | 41 | `9f1e1f2f8a85105da34e1f472570dfe9675e01bc31d133f3d03996ef324908e2` |
| `git-status.txt` | 43 | `9309448a642eefa0ea176a48c13b50dd1a8ef5c0600ab2cdf7f4a83779d51242` |
| `graficas.py` | 4841 | `8b51b6d4cb8ceaf6723d1dc69308485ea1ce0ad39ee3a69d470d54e3dd7dd9d0` |
| `intento-1/backend-access.log` | 299 | `a73307ff20adef7ad937f9b7a9bc5223f4d9a22031ce8b52f12966f73d8f407a` |
| `intento-1/docker-stats.csv` | 189 | `eec7b4819a3d1609a57875be8eadbdff1f6c20a218abbc5181ffa665b63ce65e` |
| `intento-1/exit-code.txt` | 2 | `4355a46b19d348dc2f57c046f8ef63d4538ebb936000f3c9ee954a27460dd865` |
| `intento-1/finished-utc.txt` | 21 | `9e758ab764b7377e525f855605ae118c139f0d04b76f83bb43d3c5d7aedd5b42` |
| `intento-1/load.log` | 696 | `812a150df2026445787a1188e3cd2a1760d01b0b2ffd0d6b668793563cedca85` |
| `intento-1/seed.json` | 5687 | `8b69e3623cff77b403bc71d61339c34c84918bff32162eac3cbdada0c84fccf8` |
| `intento-1/seed.log` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `intento-1/started-utc.txt` | 21 | `16ff76fd39c5c33f6bf527015c3aad83ba522c1be23714555b90b0ff84c2b23d` |
| `load.log` | 2229 | `8420d3a54cc033ee2d4c74e1d19d7a1eef9af179b6b52e300ab0cbf5b22fb847` |
| `postgresql-version.txt` | 89 | `683ecaee6342addcdb0697c81ee983b7085b774acade718fe5f7718a81c6178e` |
| `result.json` | 2229 | `8420d3a54cc033ee2d4c74e1d19d7a1eef9af179b6b52e300ab0cbf5b22fb847` |
| `run_perf.sh` | 3810 | `31c4578d66c730049dbbf91bbbffe4ee6c840e3574510548c11841f93e3b0346` |
| `seed.json` | 5628 | `ec6619e0c287f8daefbad112533f245fc2d8c767ee402788e99e6c9e54fec375` |
| `seed.log` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `seed.raw` | 5687 | `f19503e0062656387f28976569d7a40cd791eea6e36f2c684f1db0f5357b83e5` |
| `started-utc.txt` | 21 | `e5e3aa9f3fd70ca5f037ee34c95fba3ee51a33fdb228832260a1916478b73ca6` |

## RUN-EMI-20261015-02

| Archivo | Bytes | SHA-256 |
| --- | ---: | --- |
| `backend-access.log` | 16681 | `79247192ee1823f31e3e3cb8d3b3e9cf31ba883493f0efafc2165c9842a3a3af` |
| `backend-limits.txt` | 34 | `a061be1c2963311e1f66b9fd106bf9ebfbc6f6d38447578b0e7ce4e0dcb51912` |
| `build.log` | 2861 | `16c799296b9eb9f70302cbdfe762f8ff1e93fe5679e67bfe089493ea05b78d5c` |
| `docker-stats.csv` | 12253 | `2d70654850d61ad03547f92fdd5e5865df80999d07eb1bc4b66c033d71f85a07` |
| `exit-code.txt` | 2 | `9a271f2a916b0b6ee6cecb2426f0b3206ef074578be55d9bc94f6f3fe3ab86aa` |
| `finished-utc.txt` | 21 | `8559aef5ceadd3b4a682bcf2a80087a78321dfb76efdeaaa27933e0ea3fd8255` |
| `git-sha.txt` | 41 | `9f1e1f2f8a85105da34e1f472570dfe9675e01bc31d133f3d03996ef324908e2` |
| `git-status.txt` | 43 | `9309448a642eefa0ea176a48c13b50dd1a8ef5c0600ab2cdf7f4a83779d51242` |
| `load.log` | 2226 | `6d49d554c148004e0f8feb4e39d41b5c5121ab2fdd656a225c48b4e79d65993c` |
| `postgresql-version.txt` | 89 | `683ecaee6342addcdb0697c81ee983b7085b774acade718fe5f7718a81c6178e` |
| `result.json` | 2226 | `6d49d554c148004e0f8feb4e39d41b5c5121ab2fdd656a225c48b4e79d65993c` |
| `run_perf.sh` | 3883 | `1a024a935cba9668fae430988003eeee4a6935b56bf5c97115e8a9eb9f2e80b4` |
| `seed.json` | 5628 | `22f8cb4f2915aa56661e8a5508bbe5fa896d39f4a6b1eb8dc708713cf0310e22` |
| `seed.log` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `seed.raw` | 5687 | `9c2d4c26a0db75729ac0d4e1fba08586b86ef767056e3c97df589e72b5611199` |
| `started-utc.txt` | 21 | `3ab214bfde198a473df97c0c38901861b2420217b3b3aa66c88e4429552b4996` |
