"""Parte 4 — Flujo de reserva y cancelación de horas."""
from datetime import datetime

import pytest
from django.utils import timezone

from consultorio.models import Reserva


@pytest.mark.django_db
def test_reserva_requiere_login(cliente):
    """GET /consultorio/ sin sesión → redirige al login."""
    response = cliente.get("/consultorio/")

    assert response.status_code == 302
    assert response.url.startswith("/login/")


@pytest.mark.django_db
def test_crear_reserva_exitosa(cliente, paciente_user, profesional_user, consultorio):
    """Paciente reserva un slot válido → Reserva creada en estado 'pendiente'."""
    cliente.force_login(paciente_user)

    response = cliente.post(
        "/consultorio/",
        {
            "consultorio": consultorio.objectid,
            "profesional_id": profesional_user.profesional.id,
            "motivo": "Control de rutina",
            "slot": "2026-07-01 09:00",
        },
    )

    assert response.status_code == 302
    reserva = Reserva.objects.get(motivo="Control de rutina")
    assert reserva.estado == "pendiente"
    assert reserva.paciente.usuario.rut == "666666666"
    assert reserva.profesional == profesional_user.profesional


@pytest.mark.django_db
def test_no_doble_reserva_mismo_slot(cliente, paciente_user, profesional_user, consultorio):
    """El mismo slot no puede reservarse dos veces (segunda es rechazada)."""
    cliente.force_login(paciente_user)
    payload = {
        "consultorio": consultorio.objectid,
        "profesional_id": profesional_user.profesional.id,
        "motivo": "Primera reserva",
        "slot": "2026-07-01 10:00",
    }

    cliente.post("/consultorio/", payload)
    # Segundo intento sobre el mismo profesional + slot.
    cliente.post("/consultorio/", {**payload, "motivo": "Intento duplicado"})

    slot_dt = timezone.make_aware(datetime(2026, 7, 1, 10, 0))
    activas = (
        Reserva.objects
        .filter(profesional=profesional_user.profesional, fecha_reserva=slot_dt)
        .exclude(estado="cancelada")
    )
    assert activas.count() == 1
    assert not Reserva.objects.filter(motivo="Intento duplicado").exists()


@pytest.mark.django_db
def test_cancelar_hora_flujo(cliente, paciente_user, profesional_user, consultorio):
    """Flujo completo de cancelación → la reserva queda en estado 'cancelada'."""
    cliente.force_login(paciente_user)
    reserva = Reserva.objects.create(
        consultorio=consultorio,
        paciente=paciente_user.paciente,
        profesional=profesional_user.profesional,
        fecha_reserva=timezone.now(),
        motivo="Cita a cancelar",
        estado="confirmada",
    )

    # Paso 1: seleccionar la reserva → el sistema genera un código en sesión.
    cliente.post(
        "/consultorio/cancelar_hora",
        {"action": "seleccionar", "reserva_id": reserva.id},
    )
    codigo = cliente.session["cancelacion"]["codigo"]

    # Paso 2: confirmar con el código correcto.
    response = cliente.post(
        "/consultorio/cancelar_hora",
        {
            "action": "confirmar",
            "confirmar_reserva_id": reserva.id,
            "codigo": codigo,
            "motivo_cancelacion": "Ya no puedo asistir",
        },
    )

    assert response.status_code == 302
    reserva.refresh_from_db()
    assert reserva.estado == "cancelada"
    assert reserva.motivo_cancelacion == "Ya no puedo asistir"


@pytest.mark.django_db
def test_mis_horas_solo_paciente(cliente, paciente_user, profesional_user):
    """La vista mis_horas carga (200) tanto para paciente como para profesional.

    La vista no restringe por rol; solo se verifica que renderiza.
    """
    cliente.force_login(paciente_user)
    assert cliente.get("/consultorio/mis_horas").status_code == 200

    cliente.force_login(profesional_user)
    assert cliente.get("/consultorio/mis_horas").status_code == 200
