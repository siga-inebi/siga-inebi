"""Where each requirement gets implemented, derived from the actual repository.

A ticket that only restates the acceptance criterion tells nobody what to write.
This module answers "what am I expected to program" with paths that exist in this
repository today, plus the layers the project's own conventions demand.

Sources:
- `docs/architecture/domain-map.md` for the domain responsibilities and their
  fundational dependencies.
- The real layout of `backend/apps/<app>/` and `backend/tests/`.
- `docs/architecture/api-conventions.md` for the API rules, and the domain map's
  boundary rule: business logic lives in the domain layer, not in views.
"""

# Every domain the catalogue uses, mapped onto its Django app. `app` is None when
# the domain has no app yet: saying so is the useful part of the ticket.
DOMAINS = {
    "people-registry": {
        "app": "people",
        "responsibility": "Persona institucional base para cuentas y actores",
        "depends_on": [],
        "design_docs": ["docs/architecture/initial-data-model.md"],
    },
    "identity-access": {
        "app": "identity",
        "responsibility": "Autenticacion, cuentas, roles, permisos, alcances, sesiones",
        "depends_on": ["people-registry", "institutional-structure"],
        "design_docs": ["docs/architecture/authorization-model.md"],
    },
    "security-compliance": {
        "app": "identity",
        "responsibility": "Politicas de seguridad transversales",
        "depends_on": ["identity-access"],
        "design_docs": [
            "docs/architecture/authorization-model.md",
            "docs/architecture/data-classification.md",
        ],
    },
    "student-records": {
        "app": "students",
        "responsibility": "Expediente estudiantil, fotografia, salud, contactos, encargados",
        "depends_on": ["people-registry"],
        "design_docs": [
            "docs/architecture/initial-data-model.md",
            "docs/architecture/data-classification.md",
        ],
    },
    "school-cycle": {
        "app": "academics",
        "responsibility": "Ciclos, estados, apertura, cierre, historia",
        "depends_on": ["institutional-structure"],
        "design_docs": ["docs/architecture/initial-data-model.md"],
    },
    "institutional-structure": {
        "app": "academics",
        "responsibility": "Grados, secciones, subareas, jornadas, asignaciones, horarios",
        "depends_on": ["school-cycle"],
        "design_docs": ["docs/architecture/initial-data-model.md"],
    },
    "enrollment-lifecycle": {
        "app": "enrolments",
        "responsibility": "Matricula, reinscripcion, retiros, cambios, promociones",
        "depends_on": ["student-records", "school-cycle", "institutional-structure"],
        "design_docs": ["docs/architecture/initial-data-model.md"],
    },
    "audit-compliance": {
        "app": "audit",
        "responsibility": "Bitacora, lecturas sensibles, intentos denegados",
        "depends_on": ["identity-access"],
        "design_docs": ["docs/architecture/audit-strategy.md"],
    },
    "academic-evaluation": {
        "app": None,
        "suggested_app": "evaluation",
        "responsibility": "Unidades, notas, recuperacion, resultados",
        "depends_on": ["enrollment-lifecycle", "institutional-structure"],
        "design_docs": [
            "docs/architecture/initial-data-model.md",
            "docs/architecture/domain-map.md",
        ],
    },
    "attendance-capture": {
        "app": None,
        "suggested_app": "attendance",
        "responsibility": "Credencial, QR, turnos, lotes, eventos de asistencia",
        "depends_on": ["enrollment-lifecycle", "identity-access"],
        "design_docs": [
            "docs/architecture/domain-map.md",
            "docs/architecture/audit-strategy.md",
        ],
    },
    "attendance-governance": {
        "app": None,
        "suggested_app": "attendance",
        "responsibility": "Estado diario, cierres, justificaciones, alertas",
        "depends_on": ["attendance-capture", "school-cycle"],
        "design_docs": [
            "docs/architecture/domain-map.md",
            "docs/architecture/audit-strategy.md",
        ],
    },
    "document-management": {
        "app": None,
        "suggested_app": "documents",
        "responsibility": "Documentos, tipos, acceso, descargas seguras",
        "depends_on": ["file-storage", "identity-access"],
        "design_docs": [
            "docs/architecture/file-storage-strategy.md",
            "docs/architecture/data-classification.md",
        ],
    },
    "document-generation": {
        "app": None,
        "suggested_app": "documents",
        "responsibility": "Plantillas, emision, folios, documentos oficiales",
        "depends_on": ["academic-evaluation", "enrollment-lifecycle"],
        "design_docs": ["docs/architecture/file-storage-strategy.md"],
    },
    "file-storage": {
        "app": None,
        "suggested_app": "documents",
        "responsibility": "Metadatos, integridad, retencion, referencias a binarios",
        "depends_on": ["document-management", "student-records"],
        "design_docs": ["docs/architecture/file-storage-strategy.md"],
    },
    "reporting-notifications": {
        "app": None,
        "suggested_app": "reporting",
        "responsibility": "Alertas y reportes minimos",
        "depends_on": ["attendance-governance", "academic-evaluation"],
        "design_docs": ["docs/architecture/domain-map.md"],
    },
    "platform": {
        "app": None,
        "suggested_app": None,
        "responsibility": "Configuracion, despliegue y operacion transversal",
        "depends_on": [],
        "design_docs": [
            "docs/architecture/system-context.md",
            "docs/architecture/database-strategy.md",
        ],
    },
    "frontend-platform": {
        "app": None,
        "suggested_app": None,
        "responsibility": "Base del cliente web",
        "depends_on": [],
        "design_docs": ["docs/architecture/system-context.md"],
    },
}


def domain_info(domain):
    """Return the domain entry, or a conservative placeholder for a new domain."""
    return DOMAINS.get(
        domain,
        {
            "app": None,
            "suggested_app": None,
            "responsibility": "",
            "depends_on": [],
            "design_docs": ["docs/architecture/domain-map.md"],
        },
    )


def backend_paths(domain):
    """Return the backend files a requirement in this domain touches."""
    info = domain_info(domain)
    app = info.get("app") or info.get("suggested_app")
    if not app:
        return []

    prefix = f"backend/apps/{app}"
    return [
        (f"{prefix}/models.py", "modelo, estados y restricciones de base de datos"),
        (
            f"{prefix}/services.py",
            "regla de negocio; el domain map prohibe ponerla en vistas o componentes",
        ),
        (f"{prefix}/api/serializers.py", "contrato de entrada y salida"),
        (f"{prefix}/api/views.py", "endpoint REST"),
        (f"{prefix}/api/urls.py", "ruta bajo el prefijo de version"),
        (
            f"{prefix}/migrations/",
            "migracion; `make migrations-check` falla si falta",
        ),
    ]


def frontend_paths(domain, area_label):
    """Return the frontend files a requirement touches, when it has a UI."""
    if area_label != "area:frontend" and domain != "frontend-platform":
        return []
    return [
        ("frontend/src/features/<feature>/", "estado y llamadas al API"),
        ("frontend/src/pages/", "pagina contenedora"),
        ("frontend/src/components/", "componentes presentacionales"),
    ]


def test_paths(domain, area_label):
    """Return the test files that must exist, following the repo's real layout."""
    info = domain_info(domain)
    app = info.get("app") or info.get("suggested_app")
    paths = []

    if app:
        paths.append(
            (
                f"backend/tests/unit/test_{app}_services.py",
                "regla de negocio en aislamiento",
            )
        )
        paths.append(
            (f"backend/tests/api/test_{app}_api.py", "contrato del endpoint")
        )
        if area_label == "area:security" or domain in {
            "identity-access",
            "security-compliance",
            "audit-compliance",
        }:
            paths.append(
                (
                    f"backend/tests/permissions/test_{app}_permissions.py",
                    "autorizacion por operacion y alcance",
                )
            )
        if info.get("depends_on"):
            paths.append(
                (
                    f"backend/tests/integration/test_{app}.py",
                    "flujo cruzando dominios",
                )
            )
    if area_label == "area:frontend" or domain == "frontend-platform":
        paths.append(("frontend/src/test/", "prueba de componente o de pagina"))

    return paths


def app_status_note(domain):
    """Explain whether the app exists, since that changes the first commit."""
    info = domain_info(domain)
    if info.get("app"):
        return f"La app `backend/apps/{info['app']}` ya existe: extenderla, no crear otra."
    suggested = info.get("suggested_app")
    if suggested:
        return (
            f"**La app `backend/apps/{suggested}` todavia no existe.** El primer "
            f"issue de este dominio la crea (`models.py`, `services.py`, `api/`, "
            f"`apps.py`, registro en `INSTALLED_APPS`) y los demas la extienden."
        )
    return (
        "Dominio transversal: no le corresponde una app propia. El cambio vive en "
        "configuracion, infraestructura o en la capa compartida."
    )
