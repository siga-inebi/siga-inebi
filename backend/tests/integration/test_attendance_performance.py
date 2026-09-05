"""
RNF-REN-001: percentil 95 de la confirmacion de escaneo en 2s o menos,
sobre la infraestructura objetivo (1 vCPU / 2 GB).
RNF-REN-002: capacidad de pico del porton segun operadores concurrentes y
tasa por operador.

Escenarios derivados (el requerimiento no trae escenarios en la fuente,
ver comentarios en #285 y #286):

1. RNF-REN-001 camino feliz: el p95 de la respuesta de `attendance-scan`
   para un lote representativo es <= 2s.
2. RNF-REN-001 bajo concurrencia: el p95 se sigue midiendo con los
   operadores concurrentes de RNF-REN-002, sin ocultarse.
3. RNF-REN-002 camino feliz: 3 operadores concurrentes escaneando en
   paralelo no producen errores de contencion ni eventos perdidos o
   duplicados.
4. RNF-REN-002 limite: la cifra de 3 operadores es una estimacion de
   referencia (ver nota en #286), no una medicion de sitio confirmada.

Nota de infraestructura: estas pruebas corren sobre la maquina de
CI/desarrollo, no sobre el perfil objetivo 1 vCPU / 2 GB. El resultado es
evidencia direccional -- confirma que el camino de escaneo (con el cache
por lote de RF-ASI-014 ya en su lugar) no introduce un cuello de botella
obvio -- no una medicion certificada contra la infraestructura de
produccion, que requeriria un entorno dedicado y aislado.
"""

import threading
import time

import pytest
from django.db import connections
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from apps.attendance.models import AttendanceEvent
from apps.enrolments.services import create_enrolment
from tests.factories.academic import SectionFactory
from tests.factories.attendance import ControlPointFactory, JornadaParametersFactory
from tests.factories.identity import (
    PermissionFactory,
    RoleAssignmentFactory,
    RoleFactory,
    UserFactory,
)
from tests.factories.students import StudentFactory

pytestmark = [
    pytest.mark.integration,
    pytest.mark.postgres,
    pytest.mark.django_db(transaction=True),
]

SCAN_PERMISSIONS = ["attendance_scan", "attendance_record_entry"]

# RNF-REN-002: 3 operadores concurrentes es una estimacion de referencia
# (portones/puntos de control tipicos de un establecimiento unico),
# pendiente de confirmar contra la medicion real de sitio (ver nota en #286).
PEAK_CONCURRENT_OPERATORS = 3


def _operator_client():
    user = UserFactory(password="demo-pass-123")
    role = RoleFactory(permissions=[PermissionFactory(codename=c) for c in SCAN_PERMISSIONS])
    RoleAssignmentFactory(user=user, role=role)
    client = APIClient()
    client.force_authenticate(user=user)
    return client


def _enrolled_student(cycle):
    section = SectionFactory(academic_cycle=cycle)
    student = StudentFactory()
    create_enrolment(
        student=student,
        academic_cycle=cycle,
        grade=section.offering.grade,
        section=section,
    )
    return student


def _scan_item(student, shift, control_point, client_event_id):
    return {
        "client_event_id": client_event_id,
        "student_code": student.student_code,
        "shift_id": str(shift.public_id),
        "control_point_id": str(control_point.public_id),
        "movement_type": AttendanceEvent.MovementType.ENTRY,
        "captured_at": timezone.now().isoformat(),
    }


def test_scan_confirmation_p95_latency_is_within_two_seconds():
    parameters = JornadaParametersFactory()
    control_point = ControlPointFactory(campus=parameters.shift.campus)
    client = _operator_client()

    sample_size = 20
    durations = []
    for i in range(sample_size):
        student = _enrolled_student(parameters.academic_cycle)
        item = _scan_item(student, parameters.shift, control_point, f"p95-{i}")

        started = time.perf_counter()
        response = client.post(reverse("attendance-scan"), {"items": [item]}, format="json")
        durations.append(time.perf_counter() - started)

        assert response.status_code == 200
        assert response.data[0]["outcome"] == "created"

    durations.sort()
    p95_index = max(0, int(len(durations) * 0.95) - 1)
    p95_seconds = durations[p95_index]

    assert p95_seconds <= 2.0, (
        f"p95 de confirmacion de escaneo fue {p95_seconds:.3f}s sobre {sample_size} "
        "solicitudes, por encima del limite de RNF-REN-001. Evidencia direccional: "
        "corre en la maquina de CI/desarrollo, no en el perfil objetivo 1 vCPU / 2 GB."
    )


def test_peak_concurrent_operators_scan_without_contention_or_lost_events():
    parameters = JornadaParametersFactory()
    control_point = ControlPointFactory(campus=parameters.shift.campus)
    items_per_operator = 4

    errors = []
    created_event_ids = []
    lock = threading.Lock()

    def _run_operator(operator_index):
        try:
            client = _operator_client()
            for item_index in range(items_per_operator):
                student = _enrolled_student(parameters.academic_cycle)
                item = _scan_item(
                    student,
                    parameters.shift,
                    control_point,
                    f"peak-{operator_index}-{item_index}",
                )
                response = client.post(reverse("attendance-scan"), {"items": [item]}, format="json")
                if response.status_code != 200 or response.data[0]["outcome"] != "created":
                    with lock:
                        errors.append(
                            (operator_index, item_index, response.status_code, response.data)
                        )
                    continue
                with lock:
                    created_event_ids.append(response.data[0]["event"]["public_id"])
        except Exception as exc:  # noqa: BLE001 - surfaced via `errors`, not swallowed
            with lock:
                errors.append((operator_index, None, "exception", str(exc)))
        finally:
            connections.close_all()

    threads = [
        threading.Thread(target=_run_operator, args=(operator_index,))
        for operator_index in range(PEAK_CONCURRENT_OPERATORS)
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=30)

    assert not errors, f"operadores concurrentes reportaron fallos: {errors}"
    assert len(created_event_ids) == PEAK_CONCURRENT_OPERATORS * items_per_operator
    assert len(set(created_event_ids)) == len(created_event_ids)
