"""
Alcance contextual de las escrituras de matricula (RF-ALC-001, INC-DIA-001).

El permiso atomico (``enrollment_create`` / ``enrollment_update``) dice QUE
puede hacer la cuenta; el alcance dice DONDE. Una escritura de matricula afecta
siempre a una o varias secciones (la de destino al matricular, ambas al cambiar
de seccion, la de la matricula al retirar, anular o registrar documentos), asi
que cada seccion afectada debe quedar cubierta por un ``ScopeGrant`` vigente de
un rol que conceda ese permiso.

Se evalua con los grants administrativos de ``apps.identity.scopes`` y no con
``UserAccount.has_scoped_permission``: ``scope_matches`` deniega toda escritura
en un ciclo que no este ``active``, y la reinscripcion opera legitimamente sobre
el ciclo siguiente mientras sigue en preparacion (``draft``). El ciclo cerrado lo
sigue rechazando el dominio (``require_cycle_academic_writes``). Tampoco se
deriva alcance de una asignacion docente: dar clase en una seccion no autoriza a
matricular en ella.
"""

from apps.audit.services import record_event
from apps.common.exceptions import AuthorizationError
from apps.identity.scopes import active_scope_grants, grant_matches_scope

ENROLMENTS_MODULE_KEY = "enrolments"


def require_section_scope(*, actor, codenames, sections):
    """
    Deny unless one of ``codenames`` is held with grants covering every section.

    ``codenames`` admite varios permisos para los recursos que aceptan crear o
    actualizar (requisitos documentales); basta uno de ellos con alcance sobre
    todas las secciones. Cada denegacion queda auditada como
    ``identity.authorization.denied``, igual que ``can_access_student``.
    """
    if isinstance(codenames, str):
        codenames = (codenames,)
    sections = [section for section in sections if section is not None]

    held = [codename for codename in codenames if actor.has_atomic_permission(codename)]
    if not held:
        _audit_denied(
            actor=actor, codenames=codenames, sections=sections, reason="missing_permission"
        )
        raise AuthorizationError("El actor no tiene el permiso requerido.")

    if sections and any(_covers_sections(actor, codename, sections) for codename in held):
        return

    _audit_denied(actor=actor, codenames=held, sections=sections, reason="missing_scope")
    raise AuthorizationError("El actor no tiene alcance sobre la seccion afectada.")


def _covers_sections(actor, codename, sections):
    grants = list(active_scope_grants(user=actor, codename=codename))
    return all(
        any(
            grant_matches_scope(grant, {"section": section, "module_key": ENROLMENTS_MODULE_KEY})
            for grant in grants
        )
        for section in sections
    )


def _audit_denied(*, actor, codenames, sections, reason):
    record_event(
        actor=actor,
        action="identity.authorization.denied",
        resource="Enrolment",
        context={
            "result": "denied",
            "reason": reason,
            "permission": ",".join(codenames),
            "section_ids": [section.pk for section in sections],
        },
    )
