# SIGA-INEBI

SIGA-INEBI es propuesta de plataforma integral para Instituto Nacional de Educacion Basica de Salcaja. Este repositorio contiene fundacion documental y estructural inicial. No contiene aun implementacion funcional de modulos.

## Proposito

- Centralizar informacion academica, administrativa y operativa bajo control de acceso estricto.
- Proveer base evolutiva para monolito modular con frontend y backend separados dentro de monorepo.
- Mantener trazabilidad entre requerimientos, decisiones, codigo y pruebas desde inicio.

## Arquitectura General

- Monorepositorio.
- Frontend previsto: React + Vite + JavaScript.
- Backend previsto: Python + Django + Django REST Framework.
- Arquitectura inicial: monolito modular por dominios.
- Desarrollo local inicial: SQLite.
- Pruebas automatizadas, staging y produccion: PostgreSQL.
- API: REST con JSON.
- Binarios fuera de base de datos.
- Auditoria transversal para operaciones y lecturas sensibles.
- Docker Compose para desarrollo recomendado.
- Modo local sin dependencia obligatoria de Docker para frontend y backend.

## Stack Previsto

| Capa | Tecnologia |
| --- | --- |
| Frontend | React, Vite, JavaScript |
| Backend | Python, Django, Django REST Framework |
| Base de datos local | SQLite |
| Base de datos pruebas/staging/prod | PostgreSQL |
| API | REST JSON |
| Control de versiones | Git + Pull Requests |

## Estructura

```text
.
├── .github/
├── backend/
├── docs/
│   ├── architecture/
│   ├── decisions/
│   ├── development/
│   └── requirements/
├── frontend/
├── scripts/
├── AGENTS.md
├── CODE_OF_CONDUCT.md
├── CONTRIBUTING.md
├── LICENSE
├── README.md
└── SECURITY.md
```

## Estado Actual

- Fase: fundacion ejecutable inicial.
- Backend Django funcional con API base, auth de sesion, health checks, OpenAPI y modelos fundacionales.
- Frontend React/Vite funcional con rutas base, login, layout y cliente HTTP centralizado.
- Docker Compose funcional con `db`, `backend` y `frontend`.
- Datos demo idempotentes disponibles por comando de management.
- Fundacion de pruebas, TDD y calidad en progreso dentro de repo.

## Inicio Rapido con Docker

```bash
cp .env.example .env
docker compose up --build
```

Servicios por defecto:

- Frontend: `http://127.0.0.1:5173`
- Backend API: `http://127.0.0.1:8000/api/v1/`
- OpenAPI UI: `http://127.0.0.1:8000/api/v1/docs/`
- PostgreSQL: `127.0.0.1:5432`

Comandos utiles:

```bash
make ps
make logs
make migrate
make seed
make test
make coverage
```

## Inicio Local sin Docker Completo

### Backend con PostgreSQL en Docker

```bash
cp .env.example .env
docker compose up -d db
cd backend
/usr/bin/python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements/dev.txt
DATABASE_ENGINE=postgresql \
DATABASE_NAME=siga_inebi \
DATABASE_USER=siga_inebi \
DATABASE_PASSWORD=siga_inebi_dev_password \
DATABASE_HOST=127.0.0.1 \
DATABASE_PORT=5432 \
python manage.py migrate
python manage.py runserver 127.0.0.1:8001
```

### Backend con SQLite para desarrollo rapido

```bash
cd backend
source .venv/bin/activate
DATABASE_ENGINE=sqlite python manage.py migrate
DATABASE_ENGINE=sqlite python manage.py runserver 127.0.0.1:8002
```

### Frontend local

```bash
cd frontend
npm ci
VITE_API_URL=http://127.0.0.1:8001/api/v1 npm run dev -- --host 127.0.0.1 --port 4173
```

Windows y mas detalle: ver [local setup](docs/development/local-setup.md) y [docker setup](docs/development/docker-setup.md).

## Flujo Git

- Rama protegida y reglas remotas: pendientes.
- Trabajo esperado: ramas cortas por cambio, Pull Request, revision y trazabilidad.
- Guia inicial: [git workflow](docs/development/git-workflow.md).

## Calidad y Pruebas

```bash
make test
make coverage
make security
make ci-local
```

- Backend usa `pytest`, `pytest-django`, `pytest-cov`, `factory_boy` y PostgreSQL.
- Frontend usa `Vitest`, `React Testing Library` y cobertura V8.
- `compose.test.yml` ejecuta backend contra base aislada de prueba.
- `.pre-commit-config.yaml` agrega hooks rapidos de formato, lint y secretos.

## Documentacion Clave

- Alcance funcional: [functional scope](docs/requirements/functional-scope.md)
- Catalogo de requerimientos: [requirements catalogue](docs/requirements/requirements-catalogue.md)
- Trazabilidad: [traceability matrix](docs/requirements/traceability-matrix.md)
- Diseno de interfaz y navegacion: [design](docs/design/README.md)
- Mapa de dominios: [domain map](docs/architecture/domain-map.md)
- Autorizacion: [authorization model](docs/architecture/authorization-model.md)
- Base de datos y ambientes: [database strategy](docs/architecture/database-strategy.md)
- ADR: [decisions index](docs/decisions/README.md)
- Docker: [docker setup](docs/development/docker-setup.md)
- Troubleshooting: [troubleshooting](docs/development/troubleshooting.md)
- Guia para agentes y desarrolladores: [AGENTS.md](AGENTS.md)

## Advertencia de Datos

No usar datos reales, secretos ni documentos institucionales reales en este repositorio. Toda carga futura debe usar datos sinteticos o anonimizados.
