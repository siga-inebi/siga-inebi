# Evidencia revisada — RUN-DIA-20261012-01, 02 y 03

Esta referencia publica resultados sintéticos revisados. Los artefactos crudos
permanecen locales en `docs/quality/fase-7/evidence/RUN-DIA-20261012-0N/`,
ignorados por Git conforme a la política actual. Su entrega a revisores está
pendiente; los hashes permiten comprobar integridad, no sustituyen su acceso.

- SHA evaluado: `72ea438cd9a2427524346856d850578f6132e715`.
- Python 3.11.17, Django 5.2.17, pytest 8.4.1, PostgreSQL 16.14; Node 22.23.3, Vitest 4.1.11.
- [Resultados por caso](resultados-pruebas.csv), transcritos de JUnit y cotejados con los 181 casos del inventario.
- Operador técnico: Claude Code para Diana. Revisión de Santiago pendiente.
- Ningún artefacto contiene secretos, cookies, tokens ni datos institucionales.

## Comandos ejecutados

Desde la raíz del repositorio; el marcador de directorio representa la ruta
absoluta local del directorio de cada corrida. La imagen de backend se construyó con
`docker compose -p siga_inebi_diana_qa -f compose.yml -f compose.test.yml build backend-test`
y se inició únicamente `db-test` del mismo proyecto.

RUN-DIA-20261012-01 (backend):

```text
docker compose -p siga_inebi_diana_qa -f compose.yml -f compose.test.yml run --rm -v <absolute-evidence-directory>:/evidence backend-test sh -lc 'python --version > /evidence/runtime-versions.txt && python -m django --version >> /evidence/runtime-versions.txt && pytest --version >> /evidence/runtime-versions.txt && python manage.py migrate --noinput && pytest tests/unit/test_people_services.py tests/unit/test_students.py tests/unit/test_students_services.py tests/unit/test_student_guardian_relation_services.py tests/unit/test_emergency_contact_services.py tests/unit/test_student_health_note_services.py tests/unit/test_student_observation_services.py tests/api/test_people_api.py tests/api/test_students_api.py tests/api/test_guardians_api.py tests/api/test_emergency_contacts_api.py tests/api/test_student_health_notes_api.py tests/api/test_student_observations_api.py tests/integration/test_student_lifecycle.py tests/permissions/test_guardian_derived_scope.py tests/unit/test_qr.py tests/unit/test_no_store_api_middleware.py tests/permissions/test_attendance_permissions.py tests/api/test_attendance_api.py::test_scan_endpoint_confirmation_never_leaks_health_academic_or_contact_data tests/api/test_attendance_api.py::test_issue_credential_qr_code_encodes_only_the_opaque_identifier tests/api/test_attendance_api.py::test_credential_print_content_is_not_stored_on_the_operator_device tests/api/test_attendance_api.py::test_presence_list_is_not_stored_on_the_operator_device tests/api/test_attendance_api.py::test_justification_attachment_read_is_not_stored_on_the_operator_device tests/integration/test_attendance.py::test_gate_scan_of_a_real_enrolment_is_not_stored_while_catalogues_keep_their_cache --no-cov --junitxml=/evidence/junit.xml -q'
```

RUN-DIA-20261012-02 (frontend):

```text
docker compose run --rm --no-deps -v <absolute-evidence-directory>:/evidence frontend sh -lc 'node --version > /evidence/runtime-versions.txt && npx vitest --version >> /evidence/runtime-versions.txt && npx vitest --run src/test/AlumnosPage.test.jsx src/test/GuardiansPage.test.jsx src/test/personasPage.test.jsx --reporter=default --reporter=junit --outputFile.junit=/evidence/junit.xml'
```

RUN-DIA-20261012-03 (diagnóstico de los dos fallos):

```text
docker compose run --rm --no-deps -v <absolute-evidence-directory>:/evidence frontend sh -lc 'npx vitest --run src/test/GuardiansPage.test.jsx src/test/personasPage.test.jsx --testTimeout=30000 --reporter=verbose --reporter=junit --outputFile.junit=/evidence/junit.xml'
```

## Integridad de artefactos locales

### RUN-DIA-20261012-01

| Archivo local | Bytes | SHA-256 |
| --- | ---: | --- |
| `build-exit-code.txt` | 2 | `9a271f2a916b0b6ee6cecb2426f0b3206ef074578be55d9bc94f6f3fe3ab86aa` |
| `build.log` | 77281 | `070f322478908feffb4a92a5e656d49798405939c3a14af1e7c385a139ae75f9` |
| `command.txt` | 1755 | `22ee8953b17d91df64e16b096598cbf965126de31ee4a2fae69c2a290259d694` |
| `database-exit-code.txt` | 2 | `9a271f2a916b0b6ee6cecb2426f0b3206ef074578be55d9bc94f6f3fe3ab86aa` |
| `database-start.log` | 295 | `6e3ee2296c6a1362a1d4a24c66a00a2487013451b0cbc7b1a01e4b76782147cb` |
| `execution.log` | 8715 | `9f16363f97a691054b4048f3c2cca58e04fb7436d88edb4ad4e37436bf9d8e24` |
| `exit-code.txt` | 2 | `9a271f2a916b0b6ee6cecb2426f0b3206ef074578be55d9bc94f6f3fe3ab86aa` |
| `finished-utc.txt` | 21 | `15da91cd2a152468c6cd785b3b37a947b019f25e2e0c6a3719b611caca9a8569` |
| `git-sha.txt` | 41 | `616dd5eac5b9f6f995b954362fe464591c19a813142baa4258aa9c6df4dd44a7` |
| `git-status.txt` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `junit.xml` | 19941 | `5be015a222c5b5bfadcf89a74d02aa9419aab6ce74d3bb3fc11bcfa06e2728f1` |
| `postgresql-version.txt` | 89 | `ed73277d2db0e44351cec96477235ce19061de7029d709eb25cc3da0c4024639` |
| `runtime-versions.txt` | 35 | `5098d735f48e5a9834a10243524dec162e571a6374b711ff416743bd75a3c0aa` |
| `started-utc.txt` | 21 | `30ed49764704fc50780331db7df48dad38f609c4fd36b65c5719de6dba414ce9` |

### RUN-DIA-20261012-02

| Archivo local | Bytes | SHA-256 |
| --- | ---: | --- |
| `command.txt` | 389 | `b92cb9ed2937864d59b74d15935036218e3bdde8f18b14d90d0f679712628cbf` |
| `execution.log` | 8641 | `a0970377c124666fb7d8a802ecfddfe4ee04e18f04ebaaeb7533a897fe6202b3` |
| `exit-code.txt` | 2 | `4355a46b19d348dc2f57c046f8ef63d4538ebb936000f3c9ee954a27460dd865` |
| `finished-utc.txt` | 21 | `5dffb102c8924a0676b7de3c97360ba2f3e58207b63663c0705bc927722affdb` |
| `git-sha.txt` | 41 | `616dd5eac5b9f6f995b954362fe464591c19a813142baa4258aa9c6df4dd44a7` |
| `junit.xml` | 8439 | `41854e79a6c3639f5ea3a898cfc3ef82524b42d6911e0d0c14e7428affc5d01b` |
| `runtime-versions.txt` | 47 | `bde829a07fd09b264e6761e244a50ece66788bd89ed8cb248ff3d0fd1ae6cfb9` |
| `started-utc.txt` | 21 | `24878781e66c9c818a743a6e3ab6636431cdaeb05ff680414a579c98d0fa1040` |

### RUN-DIA-20261012-03

| Archivo local | Bytes | SHA-256 |
| --- | ---: | --- |
| `command.txt` | 270 | `86e36794e1899b944c8412d438ade4bb8af366d117ccc222355042ee43082b55` |
| `execution.log` | 3459 | `3f4a4fff40cb173da5825a900e2368b89113339fbbb0a69a365dc399a726e0d1` |
| `exit-code.txt` | 2 | `9a271f2a916b0b6ee6cecb2426f0b3206ef074578be55d9bc94f6f3fe3ab86aa` |
| `finished-utc.txt` | 21 | `74a1c3cf3fa7786c47d268539b206a16caacef3670077947bbffa52e28364c62` |
| `git-sha.txt` | 41 | `616dd5eac5b9f6f995b954362fe464591c19a813142baa4258aa9c6df4dd44a7` |
| `junit.xml` | 3331 | `e8b45cd045d04406586e8383d318dea443f7b52b579f35bd3a6b9ff1713c4167` |
| `started-utc.txt` | 21 | `24569d215d4df6244cbcf27c25d7dd784ab94e5227e21f22d27fa48d735fc5ac` |
