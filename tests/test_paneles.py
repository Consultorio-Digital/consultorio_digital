"""Parte 5 — Paneles por rol y acciones del doctor sobre reservas."""
from datetime import date

import pytest
from django.contrib.auth.models import User
from django.utils import timezone

from consultorio.models import Profesional, Reserva, Usuario


@pytest.mark.django_db
def test_home_admin_redirige_panel_admin(cliente, admin_user):
    """Admin en / → redirige a /panel_admin/."""
    cliente.force_login(admin_user)
    response = cliente.get("/")

    assert response.status_code == 302
    assert response.url == "/panel_admin/"


@pytest.mark.django_db
def test_home_profesional_redirige_panel_doctor(cliente, profesional_user):
    """Profesional en / → redirige a /panel_doctor/."""
    cliente.force_login(profesional_user)
    response = cliente.get("/")

    assert response.status_code == 302
    assert response.url == "/panel_doctor/"


@pytest.mark.django_db
def test_home_paciente_muestra_dashboard(cliente, paciente_user):
    """Paciente en / → 200 (dashboard del paciente)."""
    cliente.force_login(paciente_user)
    response = cliente.get("/")

    assert response.status_code == 200


@pytest.mark.django_db
def test_panel_admin_requiere_admin(cliente, paciente_user):
    """Paciente intentando entrar a /panel_admin/ → 403."""
    cliente.force_login(paciente_user)
    response = cliente.get("/panel_admin/")

    assert response.status_code == 403


@pytest.mark.django_db
def test_panel_doctor_requiere_profesional(cliente, paciente_user):
    """Paciente intentando entrar a /panel_doctor/ → redirige a /."""
    cliente.force_login(paciente_user)
    response = cliente.get("/panel_doctor/")

    assert response.status_code == 302
    assert response.url == "/"


@pytest.mark.django_db
def test_actualizar_reserva_por_doctor(cliente, paciente_user, profesional_user, consultorio):
    """El doctor cambia el estado de SU reserva a 'confirmada'."""
    reserva = Reserva.objects.create(
        consultorio=consultorio,
        paciente=paciente_user.paciente,
        profesional=profesional_user.profesional,
        fecha_reserva=timezone.now(),
        motivo="Cita por confirmar",
    )
    cliente.force_login(profesional_user)

    response = cliente.post(
        "/consultorio/actualizar_reserva/",
        {"reserva_id": reserva.id, "nuevo_estado": "confirmada"},
    )

    assert response.status_code == 302
    reserva.refresh_from_db()
    assert reserva.estado == "confirmada"


@pytest.mark.django_db
def test_actualizar_reserva_otro_doctor_prohibido(cliente, paciente_user, profesional_user, consultorio):
    """Un doctor no puede modificar la reserva de OTRO profesional → 404."""
    reserva = Reserva.objects.create(
        consultorio=consultorio,
        paciente=paciente_user.paciente,
        profesional=profesional_user.profesional,
        fecha_reserva=timezone.now(),
        motivo="Cita de otro doctor",
    )

    # Segundo profesional, distinto del dueño de la reserva.
    otro = User.objects.create_user(
        username="222222222", email="otro@test.cl", password="Consultorio_2026!",
    )
    otro_usuario = Usuario.objects.create(
        rut="222222222", nombre="Otro", apellido="Doctor",
        fecha_nacimiento=date(1970, 2, 2), correo="otro@test.cl",
    )
    Profesional.objects.create(usuario=otro_usuario, especialidad="Pediatría")
    cliente.force_login(otro)

    response = cliente.post(
        "/consultorio/actualizar_reserva/",
        {"reserva_id": reserva.id, "nuevo_estado": "confirmada"},
    )

    assert response.status_code == 404
    reserva.refresh_from_db()
    assert reserva.estado == "pendiente"  # sin cambios
