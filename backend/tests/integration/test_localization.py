"""
RNF-LOC-001 — servidor y base de datos fijados en la zona horaria del
establecimiento; los eventos y las fechas de efecto se interpretan en hora
local.

Escenarios derivados del criterio de aceptacion (el requerimiento no trae
escenarios en la fuente):

1. Camino feliz: el servidor esta fijado en la zona del establecimiento y
   almacena instantes con zona.
2. Un movimiento capturado antes de la medianoche local pertenece al dia
   escolar local, no al dia siguiente en UTC.
3. La base de datos filtra por fecha en hora local: la misma fila cae bajo su
   dia local cuando la consulta la hace Postgres, no Python.
4. Una fecha de efecto derivada del reloj coincide con la fecha local.

El instante de prueba es 23:30 del 10 de marzo de 2026. Guatemala esta en
UTC-6 todo el ano, asi que ese instante es 05:30 del 11 de marzo en UTC: un
servidor leyendo UTC archivaria el movimiento en el dia escolar equivocado, y
esa es exactamente la confusion que este requerimiento prohibe.
"""

from datetime import UTC, datetime, time, timedelta
from zoneinfo import ZoneInfo

import pytest
from django.conf import settings
from django.db import connection
from django.utils import timezone

from apps.attendance.models import AttendanceEvent
from tests.factories.attendance import AttendanceEventFactory

pytestmark = [pytest.mark.integration, pytest.mark.postgres, pytest.mark.django_db]

LOCAL_DAY = datetime(2026, 3, 10).date()
LATE_EVENING = time(23, 30)


def _late_evening_instant():
    """23:30 local del dia de prueba, como instante con zona."""
    return timezone.make_aware(datetime.combine(LOCAL_DAY, LATE_EVENING))


def test_the_server_is_pinned_to_the_establishments_timezone():
    """Escenario 1: la configuracion esta fijada, no heredada del entorno."""
    assert settings.USE_TZ is True
    assert settings.TIME_ZONE
    # La zona es resoluble: un nombre invalido reventaria aqui y no en
    # produccion a las once y media de la noche.
    assert ZoneInfo(settings.TIME_ZONE)
    assert timezone.get_current_timezone_name() == settings.TIME_ZONE
    # El almacenamiento sigue siendo absoluto: la zona interpreta, no guarda.
    assert timezone.now().utcoffset() == timedelta(0)


def test_an_event_captured_before_local_midnight_belongs_to_the_local_day():
    """Escenario 2: el dia escolar lo decide el reloj local."""
    captured_at = _late_evening_instant()

    # La trampa, escrita: en UTC ese instante ya es del dia siguiente.
    assert captured_at.astimezone(UTC).date() == LOCAL_DAY + timedelta(days=1)
    assert timezone.localdate(captured_at) == LOCAL_DAY


def test_the_database_filters_dates_in_local_time():
    """
    Escenario 3: el filtro por fecha lo resuelve Postgres, no Python.

    ``captured_at__date`` se compila con la zona del establecimiento. Si el
    servidor interpretara en UTC, la fila caeria bajo el 11 de marzo y esta
    consulta no la encontraria.
    """
    captured_at = _late_evening_instant()
    event = AttendanceEventFactory(event_date=LOCAL_DAY, captured_at=captured_at)

    same_day = AttendanceEvent.objects.filter(pk=event.pk, captured_at__date=LOCAL_DAY)
    next_day_utc = AttendanceEvent.objects.filter(
        pk=event.pk, captured_at__date=LOCAL_DAY + timedelta(days=1)
    )

    assert same_day.exists()
    assert not next_day_utc.exists()
    assert settings.TIME_ZONE in str(same_day.query)


def test_the_database_connection_stores_absolute_instants():
    """
    La sesion de Django habla UTC a proposito: el almacenamiento es absoluto y
    la zona del establecimiento interpreta al leer. Fijar el reloj del cluster
    (ver ``compose.yml``) sirve para lo que entra por fuera de Django --
    ``psql``, ``pg_dump``, las lineas del log -- no para cambiar como se guarda.
    """
    with connection.cursor() as cursor:
        cursor.execute("SHOW timezone")
        session_timezone = cursor.fetchone()[0]

    assert session_timezone == "UTC"

    captured_at = _late_evening_instant()
    event = AttendanceEventFactory(event_date=LOCAL_DAY, captured_at=captured_at)
    event.refresh_from_db()

    assert event.captured_at == captured_at
    assert timezone.localtime(event.captured_at).time() == LATE_EVENING


def test_an_effective_date_derived_from_the_clock_is_the_local_date():
    """Escenario 4: las fechas de efecto se derivan del reloj local."""
    assert timezone.localdate() == timezone.localtime(timezone.now()).date()
    assert timezone.localdate(_late_evening_instant()) == LOCAL_DAY
