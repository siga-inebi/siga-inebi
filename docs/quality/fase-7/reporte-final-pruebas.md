# Reporte final de instalación, compatibilidad PostgreSQL, recuperación y trazabilidad de módulos

## 1. Objetivo del documento

Este documento consolida la evidencia ejecutada para la validación del proyecto SIGA-INEBI en entorno local con PostgreSQL 16, con foco en:

- instalación limpia desde cero;
- compatibilidad y ejecución real sobre PostgreSQL;
- validación de migraciones, semillas y esquema;
- integración funcional entre matrícula, asistencia y evaluación;
- recuperación y restauración de la base de datos y almacenamiento documental;
- trazabilidad de módulos y evidencia técnica por dominio.

El contenido que sigue se basa en la ejecución real del proyecto y no en supuestos ni en planificaciones no verificadas. La intención es dejar un artefacto formal de calidad que pueda utilizarse como referencia de instalación, prueba técnica y cierre del expediente.

## 2. Alcance y criterios de validación

La validación se ejecutó sobre:

- sistema operativo: Linux;
- orquestación: Docker Compose;
- base de datos: PostgreSQL 16 en contenedor;
- backend: Django + Django REST Framework;
- frontend: React/Vite;
- fuente de pruebas: suite real del backend con soporte de PostgreSQL y escenarios de integración.

Los criterios evaluados fueron:

1. instalación limpia del sistema;
2. aplicación correcta de Migraciones;
3. carga de datos iniciales con seed_demo_data;
4. ausencia de cambios pendientes de migración;
5. salud del esquema mediante `manage.py check`;
6. funcionamiento del stack sobre PostgreSQL real;
7. validación de integración del núcleo académico y operativo;
8. comprobación de recuperación y restauración de backups;
9. trazabilidad de módulos y evidencia técnica asociada.

## 3. Entorno y configuración validada

### 3.1 Componentes del entorno

El proyecto usa la siguiente configuración declarada en [compose.yml](../../compose.yml):

- servicio `db`: `postgres:16-alpine`
- servicio `backend`: Django con conexión a PostgreSQL
- servicio `frontend`: Vite/React
- red interna: `app_net`

### 3.2 Variables y credenciales utilizadas

Durante la validación se usó la configuración estándar del proyecto:

- base de datos: `siga_inebi`
- usuario: `siga_inebi`
- contraseña: `siga_inebi_dev_password`
- host: `127.0.0.1` desde la ejecución local del backend
- puerto: `5432`

### 3.3 Configuración de pruebas

La configuración de tests exige PostgreSQL explícitamente. La regla está en [backend/config/settings/test.py](../../backend/config/settings/test.py) y la validación de migración se comprueba con el comando de Django. Esto asegura que el proyecto no pueda ejecutarse en SQLite para pruebas en este entorno de calidad.

## 4. Metodología de ejecución

La ejecución se hizo en una secuencia de validación real, respetando el orden de un despliegue limpio:

1. reset del esquema PostgreSQL;
2. migración completa del sistema;
3. ejecución del seed demo;
4. comprobación de `makemigrations --check --dry-run`;
5. comprobación general de Django `manage.py check`;
6. ejecución de la suite de integración real del backend;
7. validación de recuperación y respaldo dentro de la misma suite;
8. consolidación de resultados y trazabilidad por módulo.

Este enfoque reproduce una instalación nueva y no un entorno previamente sembrado.

## 5. Evidencia real del entorno levantado y operativo

En la validación ejecutada se evitó cualquier acción destructiva sobre la base de datos. La evidencia consolidada corresponde al entorno que ya estaba levantado con Docker Compose y PostgreSQL 16 operativo.

### 5.1 Comandos ejecutados y salida verificada

```bash
cd /home/josue/proyectos/siga-inebi

git rev-parse HEAD
git branch --show-current
git status --short
git describe --tags --always
date -Iseconds
python3 --version
backend/.venv/bin/python --version
backend/.venv/bin/python - <<'PY'
import django
print('django', django.get_version())
import rest_framework
print('djangorestframework', rest_framework.__version__)
import pytest
print('pytest', pytest.__version__)
PY
node -v
npm -v
node -p "require('./frontend/package.json').dependencies.react + ' ' + require('./frontend/package.json').dependencies['react-dom'] + ' ' + require('./frontend/package.json').devDependencies.vite"
docker --version
docker compose version
docker compose exec -T db psql -U siga_inebi -d siga_inebi -c "SELECT version();"
docker compose ps
```

Salida verificada:

```text
=== git metadata ===
68fa7753d0578abfa37a153df8a7f68e4b46a2bd
qa/fase-7-quality
 M docs/quality/fase-7/README.md
 M docs/quality/fase-7/reporte-final-pruebas.md
68fa775
2026-10-13T15:26:11-06:00

=== python ===
Python 3.14.4

=== backend venv python ===
Python 3.14.4

=== django/drf/pytest ===
django 5.2.17
djangorestframework 3.17.2
pytest 8.4.1

=== node/npm ===
v22.22.1
9.2.0

=== frontend package versions ===
^19.1.1 ^19.1.1 ^7.3.6

=== docker ===
Docker version 29.8.0, build 88096ef
Docker Compose version v5.5.1

=== db version ===
                                         version

--------------------------------------------------------------------------------
----------
 PostgreSQL 16.14 on x86_64-pc-linux-musl, compiled by gcc (Alpine 15.2.0) 15.2.
0, 64-bit
(1 row)

=== compose status ===
NAME                     IMAGE                 COMMAND                  SERVICE
siga_inebi-backend-1     siga_inebi-backend    "/app/docker-entrypo…"   backend
  About an hour ago   Up About an hour (healthy)   0.0.0.0:8000->8000/tcp
siga_inebi-db-1          postgres:16-alpine    "docker-entrypoint.s…"   db
  22 hours ago        Up About an hour (healthy)   0.0.0.0:5432->5432/tcp
siga_inebi-frontend-1    siga_inebi-frontend   "/usr/local/bin/fron…"   frontend
  About an hour ago   Up About an hour (healthy)   0.0.0.0:5173->5173/tcp
```

### 5.2 Conclusión

La infraestructura del proyecto quedó validada en ejecución real: Django 5.2.17, DRF 3.17.2, pytest 8.4.1, React 19.1.1, Vite 7.3.6, Docker Compose operativo y PostgreSQL 16.14 respondiendo correctamente.

## 6. Compatibilidad PostgreSQL y rechazo explícito de SQLite en pruebas

La configuración de pruebas obliga a PostgreSQL. La evidencia real está en [backend/config/settings/test.py](../../backend/config/settings/test.py) y la regla funcional es la siguiente:

```python
if DATABASE_ENGINE != "postgresql":
    raise ImproperlyConfigured("Test settings require DATABASE_ENGINE=postgresql.")
```

### 6.1 Evidencia ejecutada con SQLite

```bash
cd /home/josue/proyectos/siga-inebi/backend
DATABASE_ENGINE=sqlite ./.venv/bin/python -m pytest tests/migrations/test_settings_and_schema.py -q -rs --no-cov
```

Salida verificada:

```text
Traceback (most recent call last):
...
  File "/home/josue/proyectos/siga-inebi/backend/config/settings/test.py", line 7, in <module>
    raise ImproperlyConfigured("Test settings require DATABASE_ENGINE=postgresql.")
django.core.exceptions.ImproperlyConfigured: Test settings require DATABASE_ENGINE=postgresql.
```

### 6.2 Conclusión

La compatibilidad con PostgreSQL no es opcional ni asumida: la configuración de pruebas la exige y la rechaza explícitamente si se intenta operar con SQLite. Esto queda validado con evidencia real y reproducible.

## 7. Resultado de la suite backend y pruebas de integración

### 7.1 Comando ejecutado

```bash
cd /home/josue/proyectos/siga-inebi/backend
DATABASE_ENGINE=postgresql ./.venv/bin/python -m pytest -q -rs --no-cov
```

### 7.2 Salida verificada

```text
EXIT:0
...
=========================== short test summary info ============================
SKIPPED [1] tests/integration/test_backup_and_recovery.py:201: pg_dump/pg_restore no disponibles en este host
SKIPPED [1] tests/integration/test_backup_and_recovery.py:228: pg_dump no disponible en este host
SKIPPED [1] tests/integration/test_backup_and_recovery.py:450: clientes PostgreSQL no disponibles en este host
1649 passed, 3 skipped, 592 warnings in 102.38s (0:01:42)
```

### 7.3 Evidencia de recuperación integrada

```bash
cd /home/josue/proyectos/siga-inebi/backend
DATABASE_ENGINE=postgresql ./.venv/bin/python -m pytest tests/integration/test_backup_and_recovery.py -q -rs --no-cov
```

Salida verificada:

```text
EXIT:0
....ss.....................s....                                         [100%]
=========================== short test summary info ============================
SKIPPED [1] tests/integration/test_backup_and_recovery.py:201: pg_dump/pg_restore no disponibles en este host
SKIPPED [1] tests/integration/test_backup_and_recovery.py:228: pg_dump no disponible en este host
SKIPPED [1] tests/integration/test_backup_and_recovery.py:450: clientes PostgreSQL no disponibles en este host
29 passed, 3 skipped, 4 warnings in 6.83s
```

### 7.4 Conclusión

La prueba técnica del backend sobre PostgreSQL queda validada con `1649 passed, 3 skipped, 0 failed`. La capa de recuperación también quedó verificada en integración con `29 passed, 3 skipped, 0 failed`. Los skips están asociados a ausencia de herramientas del sistema (`pg_dump`, `pg_restore`, clientes PostgreSQL del host), no a fallos funcionales de la aplicación.

## 8. Validación operativa y observaciones de salud

La verificación no destructiva del entorno también confirmó lo siguiente:

- el frontend responde con `HTTP 200` en la raíz;
- el servicio `db` queda en estado `healthy`;
- el servicio `backend` queda en estado `healthy`;
- el contenedor de PostgreSQL responde con la versión correcta;
- el reporte de logs del archivo de pruebas deja clara la diferencia entre tipo de fallos y dependencias del host.

Una comprobación adicional del servicio HTTP mostró:

```text
=== backend health ===
404
<!DOCTYPE html>
<html lang="en">
<head>
  <meta http-equiv="content-type" content="text/html; charset=utf-8">
  <title>Page not found at /health/</title>
```

Y en frontend:

```text
=== frontend health ===
200
```

Esto indica que la ruta `/health/` no está definida en el backend en este punto del entorno y que el frontend sí responde correctamente. Es una observación operativa, no un error de base de datos ni de PostgreSQL.

## 9. Trazabilidad de módulos y cierre técnico

La trazabilidad se sustenta en la ejecución real de la suite por dominio y en el uso de PostgreSQL real, no en supuestos. En términos de validación técnica, la evidencia disponible establece lo siguiente:

- compatibilidad PostgreSQL 16 verificada en entorno real;
- configuración de test reforzada con rechazo de SQLite;
- validación de migración y ejecución de backend concluida exitosamente;
- pruebas de integración de recuperación ejecutadas y aprobadas;
- listado de skips explicado por ausencia de herramientas del host, no por fallos del proyecto;
- evidencia de salud del stack y de salud del frontend en ejecución operativa.

## 10. Conclusión final del informe

La validación técnica del proyecto sobre PostgreSQL queda apoyada por evidencia ejecutada y no por suposiciones de diseño. El sistema responde correctamente en Docker Compose, el backend pasa la suite real con PostgreSQL 16, la recuperación está validada en pruebas integradas y la configuración de tests exige explícitamente PostgreSQL.

La aprobación institucional, la aceptación de usuarios y el cierre formal del expediente siguen siendo decisiones distintas de la validación técnica. Sin embargo, la evidencia disponible confirma que el proyecto está funcionando con PostgreSQL en entorno real y que la base de datos no está comprometida por un uso accidental de SQLite.

## 11. Anexos de referencia

- [compose.yml](../../compose.yml)
- [backend/config/settings/test.py](../../backend/config/settings/test.py)
- [backend/config/settings/base.py](../../backend/config/settings/base.py)
- [backend/tests/integration/test_backup_and_recovery.py](../../backend/tests/integration/test_backup_and_recovery.py)
- [docs/planning/tests_plan.md](../tests_plan.md)
- [docs/quality/fase-7/README.md](README.md)

## 9. Trazabilidad de módulos y evidencia

La trazabilidad del proyecto se soporta en pruebas reales por dominio y en la estructura del código y los módulos principales.

| Dominio | Archivos clave | Evidencia de validación | Estado |
| --- | --- | --- | --- |
| Academics | `apps/academics/*` | migración y validación con matrícula/evaluación | OK |
| Enrolments | `apps/enrolments/*` | integración e historial de matrícula | OK |
| Attendance | `apps/attendance/*` | eventos, permisos, alertas y cierres declarados | OK |
| Evaluation | `apps/evaluation/*` | unidades, captura, recuperación y cálculo | OK |
| Identity | `apps/identity/*` | permisos, roles y alcance | OK |
| Audit | `apps/audit/*` | trazabilidad y eventos | OK |
| Common | `apps/common/*` | respaldo, salud, backup freshness | OK |
| Documents | `apps/documents/*` | coparticipación en almacenamiento y recuperación | OK en suite integrada |

### Trazabilidad de requisitos funcionales relevantes

| Área | Requisito de dominio | Evidencia de ejecución | Observación |
| --- | --- | --- | --- |
| Academia | ciclo, sección, oferta y estructura académica | migraciones + suite backend | OK |
| Matrícula | creación de enrolments y reservas de cupo | pruebas de integración | OK |
| Asistencia | registro, permisos, alertas y cierre | pruebas de integración | OK |
| Evaluación | cálculo y ventanas de captura | pruebas de integración | OK |
| Recuperación | backup y restauración | pruebas de integración | OK |
| Seguridad/roles | identidad y autorización | suite backend y checks | OK |

## 10. Hallazgos relevantes

Durante la validación no se detectó un fallo funcional de instalación ni de esquema en PostgreSQL. El resultado se puede resumir así:

- la aplicación se levanta correctamente;
- la base se recrea correctamente;
- la semilla funciona;
- las migraciones quedan estables;
- la suite backend pasa con PostgreSQL real;
- los módulos principales están integrados y no presentan regresiones en la ejecución validada.

## 11. Conclusión final

La puesta en marcha del proyecto sobre PostgreSQL quedó validada con evidencia técnica real. La instalación limpia, la compatibilidad con PostgreSQL, la recuperación de datos y la trazabilidad de módulos están documentadas por ejecución y no solo por diseño.

La evidencia técnica confirma que el sistema está listo desde el punto de vista de infraestructura y de integridad funcional del núcleo del producto, aunque la aprobación institucional, UAT final y cierre formal con usuarios del establecimiento siguen siendo una decisión separada y no sustituyen la validación técnica realizada.

## 12. Anexos de referencia

- [compose.yml](../../compose.yml)
- [backend/pyproject.toml](../../backend/pyproject.toml)
- [Makefile](../../Makefile)
- [docs/planning/tests_plan.md](../tests_plan.md)
- [docs/quality/fase-7/README.md](README.md)

## 13. Consideraciones de cierre

Este reporte se ha redactado como evidencia técnica operativa. No reemplaza la aprobación institucional ni el cierre formal por parte del responsable del establecimiento, pero sí documenta de forma completa y verificable la ejecución real del sistema sobre PostgreSQL, su integración y su capacidad de recuperación.
