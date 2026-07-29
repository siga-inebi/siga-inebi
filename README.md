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

- Fase: fundacion documental y estructural.
- Implementacion funcional: no iniciada.
- Requerimientos: catalogados y no marcados como implementados.
- Decisiones base: documentadas en ADR iniciales.
- Configuracion de herramientas: minima y segura.

## Instalacion Futura

Instalacion aun no habilitada. Ver [local setup](docs/development/local-setup.md). Cuando implementacion comience, este documento se actualizara con pasos verificables para `frontend/` y `backend/`.

## Flujo Git

- Rama protegida y reglas remotas: pendientes.
- Trabajo esperado: ramas cortas por cambio, Pull Request, revision y trazabilidad.
- Guia inicial: [git workflow](docs/development/git-workflow.md).

## Documentacion Clave

- Alcance funcional: [functional scope](docs/requirements/functional-scope.md)
- Catalogo de requerimientos: [requirements catalogue](docs/requirements/requirements-catalogue.md)
- Trazabilidad: [traceability matrix](docs/requirements/traceability-matrix.md)
- Mapa de dominios: [domain map](docs/architecture/domain-map.md)
- Autorizacion: [authorization model](docs/architecture/authorization-model.md)
- ADR: [decisions index](docs/decisions/README.md)
- Guia para agentes y desarrolladores: [AGENTS.md](AGENTS.md)

## Advertencia de Datos

No usar datos reales, secretos ni documentos institucionales reales en este repositorio. Toda carga futura debe usar datos sinteticos o anonimizados.
