"""
RNF-LOC-002 — interfaz, documentos y reportes en espanol.

Escenarios derivados del criterio de aceptacion (el requerimiento no trae
escenarios en la fuente):

1. Camino feliz: un rechazo de dominio llega al cliente en espanol.
2. Rechazo por autorizacion: el 403 tambien se explica en espanol, porque el
   mensaje que mas se lee es el que niega el paso.
3. El idioma no depende del navegador: un `Accept-Language: en` no cambia los
   mensajes propios de DRF ni de Django.
4. Ningun mensaje visible del backend queda escrito en ingles.

El cuarto es el que sostiene los otros tres hacia adelante. Los mensajes de
dominio se muestran literales al usuario: `frontend/src/shared/api/apiClient.js`
toma `error.detail` y lo pone en pantalla sin traducir, asi que un mensaje en
ingles en `apps/` es texto en ingles frente a una secretaria.
"""

import ast
import pathlib

import pytest
from django.conf import settings
from django.test import override_settings
from django.urls import reverse

from tests.factories.identity import PermissionFactory, RoleAssignmentFactory, RoleFactory

pytestmark = [pytest.mark.api, pytest.mark.django_db]

APPS_ROOT = pathlib.Path(settings.BASE_DIR) / "apps"

# Llamadas cuyo texto viaja al cliente. `RuntimeError` queda fuera a proposito:
# los guardias de inmutabilidad de la bitacora protegen contra un error de
# programacion, salen como 500 y no son mensajes que alguien deba leer.
#
# `unique_violation_as` esta aqui porque su diccionario traduce una violacion de
# constraint al mensaje que devuelve la API: se escapo del primer barrido justo
# por no ser un `raise`, y el guardia existe para que eso no vuelva a pasar.
USER_FACING = {
    "DomainError",
    "PermissionDenied",
    "NotFound",
    "ValidationError",
    "unique_violation_as",
}

# Los mapas de constraint declarados como constante de modulo llegan a
# `unique_violation_as` por nombre, asi que el recorrido de llamadas no los ve.
MESSAGE_CONSTANT_SUFFIX = "_MESSAGES"

# Palabras funcionales inglesas que no existen en espanol. Un identificador
# tecnico no las dispara: el guion bajo es caracter de palabra, asi que
# `default_unit_count` no contiene `count` como palabra suelta.
ENGLISH_MARKERS = {
    "the",
    "and",
    "with",
    "for",
    "from",
    "that",
    "this",
    "cannot",
    "must",
    "does",
    "is",
    "are",
    "was",
    "were",
    "not",
    "already",
    "required",
    "found",
    "only",
    "its",
    "their",
    "has",
    "have",
    "been",
    "will",
    "into",
    "than",
    "before",
    "after",
    "belong",
    "belongs",
    "an",
    "of",
    "to",
    "be",
    "by",
}


def _string_parts(node):
    """Los trozos literales de un argumento, incluidas las f-strings."""
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return [node.value]
    if isinstance(node, ast.JoinedStr):
        return [
            v.value for v in node.values if isinstance(v, ast.Constant) and isinstance(v.value, str)
        ]
    if isinstance(node, ast.BinOp):
        return _string_parts(node.left) + _string_parts(node.right)
    if isinstance(node, ast.Dict):
        parts = []
        for value in node.values:
            parts.extend(_string_parts(value))
        return parts
    return []


def _english_words(text):
    words = {word.strip(".,:;'\"()").lower() for word in text.split()}
    return sorted(words & ENGLISH_MARKERS)


def _user_facing_messages():
    """Cada literal que puede llegar al cliente, con su origen."""
    for path in sorted(APPS_ROOT.rglob("*.py")):
        if "migrations" in path.parts:
            continue
        tree = ast.parse(path.read_text())
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            name = (
                node.func.id if isinstance(node.func, ast.Name) else getattr(node.func, "attr", "")
            )
            if name not in USER_FACING:
                continue
            for argument in node.args:
                for part in _string_parts(argument):
                    if part.strip():
                        yield path.relative_to(APPS_ROOT.parent), node.lineno, part
        for node in ast.walk(tree):
            if not isinstance(node, ast.Assign):
                continue
            names = [t.id for t in node.targets if isinstance(t, ast.Name)]
            if not any(name.endswith(MESSAGE_CONSTANT_SUFFIX) for name in names):
                continue
            for part in _string_parts(node.value):
                if part.strip():
                    yield path.relative_to(APPS_ROOT.parent), node.lineno, part


def _grant(user, codename):
    permission = PermissionFactory(codename=codename)
    RoleAssignmentFactory(user=user, role=RoleFactory(permissions=[permission]))


def test_a_domain_rejection_reaches_the_client_in_spanish(auth_client):
    """Escenario 1: el mensaje de una regla de negocio llega traducido."""
    _grant(auth_client.user, "attendance_jornada_configure")

    response = auth_client.post(
        reverse("attendance-jornada-closures"),
        {"shift_id": "00000000-0000-0000-0000-000000000000", "event_date": "2026-03-10"},
        content_type="application/json",
    )

    assert response.status_code == 400
    assert response.json()["error"]["detail"] == "No se encontro la jornada."


def test_an_authorization_rejection_is_explained_in_spanish(auth_client):
    """Escenario 2: el 403 tambien se lee en espanol."""
    response = auth_client.post(
        reverse("attendance-jornada-closures"),
        {"shift_id": "00000000-0000-0000-0000-000000000000", "event_date": "2026-03-10"},
        content_type="application/json",
    )

    assert response.status_code == 403
    assert "El actor no tiene el permiso requerido." in response.content.decode()


def test_the_language_does_not_depend_on_the_browser(client):
    """
    Escenario 3: declarar un solo idioma en ``LANGUAGES`` cierra la puerta que
    ``LocaleMiddleware`` abria. Sin eso, la garantia dependia de la
    configuracion del navegador de cada usuario.
    """
    response = client.get(reverse("attendance-event-list"), HTTP_ACCEPT_LANGUAGE="en-US,en;q=0.9")

    assert response.status_code == 403
    assert "credenciales de autenticación no se proveyeron" in response.content.decode()


@override_settings(LANGUAGES=[("es-gt", "Espanol"), ("en", "English")])
def test_the_guarantee_is_the_single_language_and_not_an_accident(client):
    """
    La contraparte del escenario 3: con un segundo idioma declarado, el mismo
    encabezado devuelve ingles. La prueba deja escrito que lo que sostiene la
    garantia es ``LANGUAGES``, no una casualidad de configuracion.
    """
    response = client.get(reverse("attendance-event-list"), HTTP_ACCEPT_LANGUAGE="en-US,en;q=0.9")

    assert "Authentication credentials were not provided." in response.content.decode()


def test_no_user_facing_message_is_written_in_english():
    """
    Escenario 4: el guardia. Recorre ``apps/`` y reporta cada literal de
    excepcion visible que contenga palabras funcionales inglesas.
    """
    offenders = [
        f"{path}:{line}: {text!r} -> {', '.join(words)}"
        for path, line, text in _user_facing_messages()
        if (words := _english_words(text))
    ]

    assert not offenders, "Mensajes visibles en ingles:\n" + "\n".join(offenders)


def test_the_guard_recognises_an_english_message():
    """
    El guardia sirve si detecta. Sin esta prueba, una lista de marcadores mal
    escrita pasaria en verde para siempre y el escenario 4 no probaria nada.
    """
    assert _english_words("Student already has an active credential.")
    assert not _english_words("El estudiante ya tiene una credencial vigente.")
    # Un identificador tecnico no es una frase en ingles.
    assert not _english_words("default_unit_count debe ser un entero positivo.")


def test_the_guard_reaches_the_constraint_message_maps():
    """
    Los mensajes de `unique_violation_as` son la parte que se escapo del primer
    barrido. Si el recorrido dejara de verlos, esta prueba lo dice en vez de
    dejar el escenario 4 pasando sobre un subconjunto.
    """
    collected = {text for _path, _line, text in _user_facing_messages()}

    assert "El estudiante ya tiene una credencial vigente." in collected
    assert any("ya tiene una inscripcion activa" in text for text in collected)
