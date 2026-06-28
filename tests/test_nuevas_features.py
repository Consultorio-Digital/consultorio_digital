"""Tests de las 4 funcionalidades nuevas:

1. Completado → Seguimiento (modal Completar, vía actualizar_reserva).
2. Auto-expiración de pendientes vencidas a 'sin_gestionar'.
3. Calendario de disponibilidad (datos en el contexto del panel doctor).
4. Registro dinámico paciente/profesional (especialidad obligatoria + recinto).
"""
from datetime import timedelta

import pytest
from django.core.management import call_command
from django.utils import timezone

from consultorio.models import Disponibilidad, Profesional, Reserva, Usuario
from tests.conftest import PASSWORD


# ── 1. Completado → Seguimiento ──────────────────────────────────────────
@pytest.mark.django_db
def test_completar_simple(cliente, paciente_user, profesional_user, consultorio):
    """nuevo_estado='completada' → la reserva queda completada con notas."""
    cliente.force_login(profesional_user)
    reserva = Reserva.objects.create(
        consultorio=consultorio, paciente=paciente_user.paciente,
        profesional=profesional_user.profesional,
        fecha_reserva=timezone.now(), motivo="Consulta", estado="confirmada",
    )

    resp = cliente.post("/consultorio/actualizar_reserva/", {
        "reserva_id": reserva.id,
        "nuevo_estado": "completada",
        "notas_doctor": "Traer exámenes",
    })

    assert resp.status_code == 302
    reserva.refresh_from_db()
    assert reserva.estado == "completada"
    assert reserva.notas_doctor == "Traer exámenes"
    assert reserva.fecha_seguimiento is None


@pytest.mark.django_db
def test_completar_con_seguimiento(cliente, paciente_user, profesional_user, consultorio):
    """Completar marcando seguimiento → estado 'seguimiento' con fecha guardada."""
    cliente.force_login(profesional_user)
    reserva = Reserva.objects.create(
        consultorio=consultorio, paciente=paciente_user.paciente,
        profesional=profesional_user.profesional,
        fecha_reserva=timezone.now(), motivo="Consulta", estado="confirmada",
    )
    fecha_seg = (timezone.localdate() + timedelta(days=14)).isoformat()

    resp = cliente.post("/consultorio/actualizar_reserva/", {
        "reserva_id": reserva.id,
        "nuevo_estado": "seguimiento",
        "notas_doctor": "Control en dos semanas",
        "fecha_seguimiento": fecha_seg,
    })

    assert resp.status_code == 302
    reserva.refresh_from_db()
    assert reserva.estado == "seguimiento"
    assert reserva.fecha_seguimiento.isoformat() == fecha_seg
    assert reserva.notas_doctor == "Control en dos semanas"


# ── 2. Auto-expiración a 'sin_gestionar' ─────────────────────────────────
@pytest.mark.django_db
def test_expirar_pendientes_marca_vencidas(paciente_user, profesional_user, consultorio):
    """Pendiente vencida → 'sin_gestionar'; confirmada vencida y pendiente
    futura no se tocan."""
    ahora = timezone.now()
    pendiente_vencida = Reserva.objects.create(
        consultorio=consultorio, paciente=paciente_user.paciente,
        profesional=profesional_user.profesional,
        fecha_reserva=ahora - timedelta(days=1), motivo="Vencida", estado="pendiente",
    )
    confirmada_vencida = Reserva.objects.create(
        consultorio=consultorio, paciente=paciente_user.paciente,
        profesional=profesional_user.profesional,
        fecha_reserva=ahora - timedelta(days=1), motivo="Confirmada", estado="confirmada",
    )
    pendiente_futura = Reserva.objects.create(
        consultorio=consultorio, paciente=paciente_user.paciente,
        profesional=profesional_user.profesional,
        fecha_reserva=ahora + timedelta(days=1), motivo="Futura", estado="pendiente",
    )

    actualizadas = Reserva.expirar_pendientes()

    assert actualizadas == 1
    pendiente_vencida.refresh_from_db()
    confirmada_vencida.refresh_from_db()
    pendiente_futura.refresh_from_db()
    assert pendiente_vencida.estado == "sin_gestionar"
    assert confirmada_vencida.estado == "confirmada"
    assert pendiente_futura.estado == "pendiente"


@pytest.mark.django_db
def test_panel_doctor_dispara_expiracion(cliente, paciente_user, profesional_user, consultorio):
    """Cargar el panel del doctor expira las pendientes vencidas (lazy)."""
    reserva = Reserva.objects.create(
        consultorio=consultorio, paciente=paciente_user.paciente,
        profesional=profesional_user.profesional,
        fecha_reserva=timezone.now() - timedelta(days=2), motivo="Olvidada", estado="pendiente",
    )

    cliente.force_login(profesional_user)
    resp = cliente.get("/panel_doctor/")

    assert resp.status_code == 200
    reserva.refresh_from_db()
    assert reserva.estado == "sin_gestionar"
    assert resp.context["sin_gestionar"] == 1


@pytest.mark.django_db
def test_comando_marcar_sin_gestionar(paciente_user, profesional_user, consultorio):
    """El management command marca las pendientes vencidas."""
    reserva = Reserva.objects.create(
        consultorio=consultorio, paciente=paciente_user.paciente,
        profesional=profesional_user.profesional,
        fecha_reserva=timezone.now() - timedelta(hours=3), motivo="X", estado="pendiente",
    )

    call_command("marcar_sin_gestionar")

    reserva.refresh_from_db()
    assert reserva.estado == "sin_gestionar"


# ── 3. Calendario de disponibilidad ──────────────────────────────────────
@pytest.mark.django_db
def test_panel_doctor_datos_calendario(cliente, profesional_user, consultorio):
    """El contexto expone la disponibilidad serializada para el calendario."""
    profesional_user.profesional.consultorio = consultorio
    profesional_user.profesional.save()
    Disponibilidad.objects.create(
        profesional=profesional_user.profesional,
        fecha=timezone.localdate() + timedelta(days=3),
        hora_inicio="08:00", hora_fin="13:00",
    )

    cliente.force_login(profesional_user)
    resp = cliente.get("/panel_doctor/")

    cal = resp.context["disponibilidades_cal"]
    assert len(cal) == 1
    assert cal[0]["inicio"] == "08:00"
    assert cal[0]["fin"] == "13:00"
    assert "fecha" in cal[0]


# ── 4. Registro dinámico ─────────────────────────────────────────────────
@pytest.mark.django_db
def test_registro_get_renderiza(cliente):
    """GET /registro/ renderiza el selector de tipo (pills) sin error."""
    resp = cliente.get("/registro/")
    assert resp.status_code == 200
    assert b'name="tipo"' in resp.content


@pytest.mark.django_db
def test_registro_profesional_sin_especialidad(cliente):
    """Profesional sin especialidad → 200, error en 'especialidad', sin crear."""
    resp = cliente.post("/registro/", {
        "username": "12.345.678-5",
        "email": "prof@test.cl",
        "first_name": "Ana",
        "last_name": "Soto",
        "password1": "Reserva_Segura_2026",
        "password2": "Reserva_Segura_2026",
        "tipo": "profesional",
        "especialidad": "",
    })

    assert resp.status_code == 200
    assert "especialidad" in resp.context["form"].errors
    assert not Usuario.objects.filter(rut="123456785").exists()


@pytest.mark.django_db
def test_registro_profesional_con_recinto(cliente, consultorio):
    """Profesional con especialidad + consultorio → crea Profesional con recinto."""
    resp = cliente.post("/registro/", {
        "username": "12.345.678-5",
        "email": "prof@test.cl",
        "first_name": "Ana",
        "last_name": "Soto",
        "password1": "Reserva_Segura_2026",
        "password2": "Reserva_Segura_2026",
        "tipo": "profesional",
        "especialidad": "Cardiología",
        "consultorio": consultorio.objectid,
    })

    assert resp.status_code == 302
    usuario = Usuario.objects.get(rut="123456785")
    profesional = Profesional.objects.get(usuario=usuario)
    assert profesional.especialidad == "Cardiología"
    assert profesional.consultorio == consultorio


@pytest.mark.django_db
def test_geodata_comunas_sin_login(cliente, consultorio):
    """obtener_comunas es público (lo usa la cascada del registro anónimo)."""
    resp = cliente.get(f"/consultorio/obtener_comunas/{int(consultorio.c_reg)}/")
    assert resp.status_code == 200
    assert any(c["nom_com"] == "Viña del Mar" for c in resp.json())
