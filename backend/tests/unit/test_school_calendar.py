"""
Reglas de calendario del ciclo escolar guatemalteco.

Sin base de datos a proposito: son fechas derivadas de un anio, y un test que
levanta PostgreSQL para comprobar que el 15 de enero de 2027 cae viernes esconde
el error entre 200 ms de arranque.
"""

from datetime import date

import pytest

from apps.academics.school_calendar import cycle_dates, cycle_end, cycle_name, cycle_start

pytestmark = [pytest.mark.unit]


@pytest.mark.parametrize(
    "year,expected",
    [
        # 15/01/2027 es viernes: se toma tal cual.
        (2027, date(2027, 1, 15)),
        # 15/01/2028 es sabado -> lunes 17. Hacia ADELANTE: las clases no pueden
        # empezar antes de la fecha que declara el calendario.
        (2028, date(2028, 1, 17)),
        # 15/01/2033 es sabado -> lunes 17.
        (2033, date(2033, 1, 17)),
        # 15/01/2034 es domingo -> lunes 16.
        (2034, date(2034, 1, 16)),
    ],
)
def test_cycle_start_moves_forward_to_a_working_day(year, expected):
    assert cycle_start(year) == expected


@pytest.mark.parametrize(
    "year,expected",
    [
        # 31/10/2028 es martes: se toma tal cual.
        (2028, date(2028, 10, 31)),
        # 31/10/2027 es domingo -> viernes 29. Hacia ATRAS: el ciclo no puede
        # derramarse a noviembre, porque su cierre acota las unidades de
        # evaluacion y sus ventanas de recuperacion.
        (2027, date(2027, 10, 29)),
        # 31/10/2026 es sabado -> viernes 30.
        (2026, date(2026, 10, 30)),
    ],
)
def test_cycle_end_moves_backward_to_a_working_day(year, expected):
    assert cycle_end(year) == expected


def test_cycle_dates_stay_inside_the_same_calendar_year():
    """
    El ciclo cabe en un anio calendario.

    ``create_academic_cycle`` exige que el anio del inicio coincida con el anio
    del ciclo, asi que una regla que se corriera a diciembre o a enero siguiente
    haria imposible crear ese ciclo.
    """
    for year in range(2024, 2041):
        starts_on, ends_on = cycle_dates(year)

        assert starts_on.year == year
        assert ends_on.year == year
        assert starts_on < ends_on


def test_cycle_name_is_derived_from_the_year():
    assert cycle_name(2027) == "Ciclo 2027"
