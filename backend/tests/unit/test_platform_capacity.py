"""RNF-CAP-001: dimensionamiento sobre la matricula real del establecimiento;
toda meta se mide contra 1 vCPU y 2 GB.

Escenarios derivados (el requerimiento no trae escenarios en la fuente,
ver comentario en #267):

1. Camino feliz: la conexion a PostgreSQL se reutiliza (`CONN_MAX_AGE`) en
   vez de abrirse por peticion, que es el costo que un perfil de 1 vCPU no
   puede permitirse pagar en cada request.
2. Limite: el valor es configurable por entorno (`DATABASE_CONN_MAX_AGE`),
   para que un despliegue con mas recursos pueda ajustarlo sin tocar codigo.
"""

import subprocess
import sys

import pytest
from django.conf import settings


@pytest.mark.unit
def test_postgresql_connections_are_reused_within_the_target_infra_profile():
    assert settings.DATABASES["default"]["CONN_MAX_AGE"] == 60


@pytest.mark.unit
def test_connection_max_age_is_configurable_by_environment():
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "import os; "
            "os.environ['DJANGO_SETTINGS_MODULE']='config.settings.base'; "
            "os.environ['DATABASE_ENGINE']='postgresql'; "
            "os.environ['DATABASE_CONN_MAX_AGE']='120'; "
            "import config.settings.base as base; "
            "assert base.DATABASES['default']['CONN_MAX_AGE'] == 120",
        ],
        capture_output=True,
        text=True,
        cwd=".",
    )

    assert result.returncode == 0, result.stderr
