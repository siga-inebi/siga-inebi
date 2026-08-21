"""
Codigos institucionales autogenerados y orden pedagogico por posicion.

Dos cosas que antes se escribian a mano y no deberian: el codigo de un registro
(estudiante, docente, sede, nivel, grado) y el numero de secuencia de un nivel o
un grado. Lo que se prueba aca es que la serie no se salte ni repita numeros, que
un codigo ajeno a la serie no la corra, y que insertar en el medio deje el orden
contiguo en vez de chocar con el constraint de unicidad.
"""

import pytest

from apps.academics.models import Grade, Level
from apps.academics.services import (
    APPEND,
    create_grade,
    create_level,
    ensure_national_levels,
    next_grade_code,
    next_level_code,
    update_grade,
    update_level,
)
from apps.common.models import DomainError
from apps.students.models import Student
from apps.students.services import create_student, next_student_code
from apps.teachers.models import Teacher
from apps.teachers.services import create_teacher, next_employee_code
from tests.factories.academic import GradeFactory, InstitutionFactory, LevelFactory
from tests.factories.students import StudentFactory
from tests.factories.teachers import TeacherFactory

pytestmark = [pytest.mark.unit, pytest.mark.django_db]


def _person():
    return {"first_name": "Ana", "last_name": "Lopez"}


# --------------------------------------------------------------------------- #
# estudiantes y docentes
# --------------------------------------------------------------------------- #


def test_student_code_series_is_per_year_and_zero_padded():
    first = create_student(person_data=_person())
    second = create_student(person_data=_person())

    year = next_student_code()[4:8]
    assert first.student_code == f"EST-{year}-0001"
    assert second.student_code == f"EST-{year}-0002"


def test_student_code_series_ignores_codes_from_outside_it():
    """
    Un codigo del ministerio o de un traslado no mueve el contador.

    Si lo moviera, un expediente importado con "2026-99" dejaria la serie
    saltando a 100 sin que nadie pueda explicar por que.
    """
    StudentFactory(student_code="P-9999-0001")

    assert create_student(person_data=_person()).student_code.endswith("-0001")


def test_explicit_student_code_is_kept_and_its_duplicate_rejected():
    created = create_student(person_data=_person(), student_code=" mineduc-77 ")

    assert created.student_code == "mineduc-77"
    with pytest.raises(DomainError, match="ya esta registrado"):
        create_student(person_data=_person(), student_code="mineduc-77")


def test_generated_student_code_survives_a_taken_number():
    """
    El numero ocupado se saltea en vez de estallar.

    Es la carrera real: dos altas simultaneas calculan el mismo codigo y una
    pierde. Perder no puede significar un 500 en la cara de quien captura.
    """
    taken = next_student_code()
    StudentFactory(student_code=taken)

    created = create_student(person_data=_person())

    assert created.student_code != taken
    assert Student.objects.filter(student_code=created.student_code).count() == 1


def test_employee_code_series_is_institutional_and_padded_to_three():
    first = create_teacher(
        person_data=_person(), specialty="Matematica", position="Docente Titulado"
    )
    second = create_teacher(person_data=_person(), specialty="Lengua", position="Docente Interino")

    assert (first.employee_code, second.employee_code) == ("DOC-001", "DOC-002")


def test_employee_code_continues_after_the_highest_in_the_series():
    TeacherFactory(employee_code="DOC-041")

    created = create_teacher(person_data=_person(), specialty="Fisica", position="Docente Titulado")

    assert created.employee_code == "DOC-042"
    assert next_employee_code() == "DOC-043"
    assert Teacher.objects.filter(employee_code="DOC-042").count() == 1


# --------------------------------------------------------------------------- #
# niveles y grados
# --------------------------------------------------------------------------- #


def test_level_code_is_generated_from_its_own_series():
    institution = InstitutionFactory()

    first = create_level(institution=institution, name="Preprimaria")
    second = create_level(institution=institution, name="Primaria")

    assert (first.code, second.code) == ("NIV-01", "NIV-02")
    assert next_level_code(institution=institution) == "NIV-03"


def test_grade_code_is_derived_from_the_level_code():
    """
    "BAS1" dice de que nivel es el grado; "GRA-07" no dice nada.

    Se deriva del codigo del nivel, que ya es unico por institucion, asi que dos
    niveles no pueden producir el mismo codigo de grado.
    """
    level = LevelFactory(code="BAS")

    first = create_grade(level=level, name="Primero Basico")
    second = create_grade(level=level, name="Segundo Basico")

    assert (first.code, second.code) == ("BAS1", "BAS2")
    assert next_grade_code(level=level) == "BAS3"


def test_grade_codes_of_two_levels_do_not_collide():
    institution = InstitutionFactory()
    basico = LevelFactory(institution=institution, code="BAS", sequence=3)
    diversificado = LevelFactory(institution=institution, code="DIV", sequence=4)

    create_grade(level=basico, name="Primero Basico")
    created = create_grade(level=diversificado, name="Cuarto Bachillerato")

    assert created.code == "DIV1"


# --------------------------------------------------------------------------- #
# orden pedagogico por posicion
# --------------------------------------------------------------------------- #


def _sequence_by_name(institution):
    return {
        level.name: level.sequence
        for level in Level.objects.filter(institution=institution).order_by("sequence")
    }


def test_level_without_a_position_goes_last():
    institution = InstitutionFactory()

    create_level(institution=institution, name="Primaria")
    create_level(institution=institution, name="Basico")

    assert _sequence_by_name(institution) == {"Primaria": 1, "Basico": 2}


def test_level_inserted_in_the_middle_pushes_the_rest_down():
    """
    Lo que antes obligaba a renumerar a mano, formulario por formulario.

    Y no se podia: la secuencia es unica por institucion, asi que cualquier
    estado intermedio del renumerado lo rechazaba la base.
    """
    institution = InstitutionFactory()
    primaria = create_level(institution=institution, name="Primaria")
    create_level(institution=institution, name="Diversificado")

    create_level(institution=institution, name="Basico", insert_after=primaria)

    assert _sequence_by_name(institution) == {
        "Primaria": 1,
        "Basico": 2,
        "Diversificado": 3,
    }


def test_level_inserted_at_the_start_takes_the_first_position():
    """``insert_after=None`` es una posicion real: la primera."""
    institution = InstitutionFactory()
    create_level(institution=institution, name="Primaria")
    create_level(institution=institution, name="Basico")

    create_level(institution=institution, name="Preprimaria", insert_after=None)

    assert _sequence_by_name(institution) == {
        "Preprimaria": 1,
        "Primaria": 2,
        "Basico": 3,
    }


def test_moving_a_level_leaves_the_order_contiguous():
    """Sin huecos: una columna "Orden" que dice 1, 2, 4 se lee como una falla."""
    institution = InstitutionFactory()
    preprimaria = create_level(institution=institution, name="Preprimaria")
    create_level(institution=institution, name="Primaria")
    create_level(institution=institution, name="Basico")
    diversificado = create_level(institution=institution, name="Diversificado")

    update_level(level=diversificado, insert_after=preprimaria)

    assert _sequence_by_name(institution) == {
        "Preprimaria": 1,
        "Diversificado": 2,
        "Primaria": 3,
        "Basico": 4,
    }


def test_moving_a_level_to_the_first_position_shifts_everyone():
    institution = InstitutionFactory()
    create_level(institution=institution, name="Primaria")
    basico = create_level(institution=institution, name="Basico")

    update_level(level=basico, insert_after=None)

    assert _sequence_by_name(institution) == {"Basico": 1, "Primaria": 2}


def test_an_inactive_level_still_occupies_its_place_in_the_order():
    """
    La secuencia es unica sobre activos e inactivos.

    Si el renumerado ignorara a los desactivados, escribiria encima de su numero
    y el constraint rechazaria la operacion entera.
    """
    institution = InstitutionFactory()
    primaria = create_level(institution=institution, name="Primaria")
    retired = create_level(institution=institution, name="Nivel retirado")
    retired.is_active = False
    retired.save(update_fields=["is_active"])

    create_level(institution=institution, name="Basico", insert_after=primaria)

    assert _sequence_by_name(institution) == {
        "Primaria": 1,
        "Basico": 2,
        "Nivel retirado": 3,
    }


def test_explicit_sequence_still_wins_over_a_position():
    """El contrato anterior de la API sigue valiendo."""
    institution = InstitutionFactory()
    first = create_level(institution=institution, name="Primaria")

    created = create_level(institution=institution, name="Basico", sequence=9, insert_after=first)

    assert created.sequence == 9


def test_position_referring_to_another_group_is_rejected():
    """
    Un hermano de otro nivel dejaria el orden a medio escribir.

    Se rechaza antes de tocar una fila: un renumerado parcial es peor que un
    rechazo, porque nadie lo ve hasta que el listado sale desordenado.
    """
    level = LevelFactory(code="BAS")
    stranger = GradeFactory()
    create_grade(level=level, name="Primero Basico")

    with pytest.raises(DomainError, match="mismo grupo"):
        create_grade(level=level, name="Segundo Basico", insert_after=stranger)


def test_grade_order_is_per_level():
    institution = InstitutionFactory()
    basico = LevelFactory(institution=institution, code="BAS", sequence=3)
    diversificado = LevelFactory(institution=institution, code="DIV", sequence=4)
    primero = create_grade(level=basico, name="Primero Basico")
    create_grade(level=basico, name="Tercero Basico")
    create_grade(level=diversificado, name="Cuarto Bachillerato")

    create_grade(level=basico, name="Segundo Basico", insert_after=primero)

    assert [
        (grade.name, grade.sequence)
        for grade in Grade.objects.filter(level=basico).order_by("sequence")
    ] == [("Primero Basico", 1), ("Segundo Basico", 2), ("Tercero Basico", 3)]
    assert Grade.objects.get(level=diversificado).sequence == 1


def test_renaming_a_grade_does_not_move_it():
    """
    ``APPEND`` no es ``None``.

    Si el ausente se confundiera con la primera posicion, cambiarle el nombre a
    un grado lo mandaria al principio del nivel.
    """
    level = LevelFactory(code="BAS")
    create_grade(level=level, name="Primero Basico")
    segundo = create_grade(level=level, name="Segundo Basico")

    update_grade(grade=segundo, name="Segundo Basico B", insert_after=APPEND)

    segundo.refresh_from_db()
    assert (segundo.name, segundo.sequence) == ("Segundo Basico B", 2)


# --------------------------------------------------------------------------- #
# niveles del sistema nacional
# --------------------------------------------------------------------------- #


def test_national_levels_are_created_in_pedagogical_order():
    institution = InstitutionFactory()

    ensure_national_levels(institution=institution)

    assert [
        (level.code, level.sequence)
        for level in Level.objects.filter(institution=institution).order_by("sequence")
    ] == [("PRE", 1), ("PRI", 2), ("BAS", 3), ("DIV", 4)]


def test_national_levels_are_idempotent_and_keep_what_exists():
    """Se identifican por codigo: un nivel renombrado sigue siendo el mismo."""
    institution = InstitutionFactory()
    LevelFactory(institution=institution, code="BAS", name="Ciclo Basico", sequence=3)

    ensure_national_levels(institution=institution)
    ensure_national_levels(institution=institution)

    levels = Level.objects.filter(institution=institution)
    assert levels.count() == 4
    assert levels.get(code="BAS").name == "Ciclo Basico"


def test_national_levels_do_not_steal_an_occupied_position():
    """
    Un nivel propio conserva su lugar; el nacional se agrega al final.

    Reacomodar el catalogo de alguien mas para calzar un numero preferido seria
    peor que un orden imperfecto.
    """
    institution = InstitutionFactory()
    LevelFactory(institution=institution, code="TEC", name="Tecnico", sequence=2)

    ensure_national_levels(institution=institution)

    # PRE toma su lugar preferido porque estaba libre; los demas se corren detras
    # del nivel propio en vez de desplazarlo.
    assert [
        (level.code, level.sequence)
        for level in Level.objects.filter(institution=institution).order_by("sequence")
    ] == [("PRE", 1), ("TEC", 2), ("PRI", 3), ("BAS", 4), ("DIV", 5)]
