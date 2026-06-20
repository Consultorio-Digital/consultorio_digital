"""Acciones de administración: el admin gestiona reservas y cuentas.

Cubre las vistas admin_actualizar_reserva y admin_toggle_cuenta
(principal/views.py), que enriquecen el rol de administrador con
capacidad de manipular datos, no solo verlos.
"""
import pytest
from django.contrib.auth.models import Group, User
from django.core.management import call_command
from django.utils import timezone

from consultorio.models import Reserva


@pytest.fixture
def reserva(db, paciente_user, profesional_user, consultorio):
    """Una reserva pendiente lista para que el admin la manipule."""
    return Reserva.objects.create(
        consultorio=consultorio,
        paciente=paciente_user.paciente,
        profesional=profesional_user.profesional,
        fecha_reserva=timezone.now(),
        motivo="Cita de prueba",
    )


# ── Gestión de reservas ──────────────────────────────────────────────

@pytest.mark.django_db
def test_admin_cambia_estado_reserva(cliente, admin_user, reserva):
    """El admin cambia el estado de cualquier reserva."""
    cliente.force_login(admin_user)

    response = cliente.post(
        "/panel_admin/reserva/",
        {"reserva_id": reserva.id, "nuevo_estado": "completada"},
    )

    assert response.status_code == 302
    assert response.url == "/panel_admin/"
    reserva.refresh_from_db()
    assert reserva.estado == "completada"


@pytest.mark.django_db
def test_admin_cancela_reserva_guarda_motivo(cliente, admin_user, reserva):
    """Al cancelar, se persiste el motivo indicado."""
    cliente.force_login(admin_user)

    cliente.post(
        "/panel_admin/reserva/",
        {
            "reserva_id": reserva.id,
            "nuevo_estado": "cancelada",
            "motivo_cancelacion": "Consultorio cerrado ese día",
        },
    )

    reserva.refresh_from_db()
    assert reserva.estado == "cancelada"
    assert reserva.motivo_cancelacion == "Consultorio cerrado ese día"


@pytest.mark.django_db
def test_admin_cancela_sin_motivo_usa_default(cliente, admin_user, reserva):
    """Cancelar sin motivo deja un texto por defecto, no vacío."""
    cliente.force_login(admin_user)

    cliente.post(
        "/panel_admin/reserva/",
        {"reserva_id": reserva.id, "nuevo_estado": "cancelada"},
    )

    reserva.refresh_from_db()
    assert reserva.estado == "cancelada"
    assert reserva.motivo_cancelacion == "Cancelada por administración"


@pytest.mark.django_db
def test_admin_estado_invalido_rechazado(cliente, admin_user, reserva):
    """Un estado fuera de las opciones válidas → 400 y sin cambios."""
    cliente.force_login(admin_user)

    response = cliente.post(
        "/panel_admin/reserva/",
        {"reserva_id": reserva.id, "nuevo_estado": "inventado"},
    )

    assert response.status_code == 400
    reserva.refresh_from_db()
    assert reserva.estado == "pendiente"


@pytest.mark.django_db
def test_admin_actualizar_reserva_requiere_admin(cliente, paciente_user, reserva):
    """Un no-admin no puede usar la acción → 403."""
    cliente.force_login(paciente_user)

    response = cliente.post(
        "/panel_admin/reserva/",
        {"reserva_id": reserva.id, "nuevo_estado": "completada"},
    )

    assert response.status_code == 403
    reserva.refresh_from_db()
    assert reserva.estado == "pendiente"


@pytest.mark.django_db
def test_admin_actualizar_reserva_inexistente(cliente, admin_user):
    """Reserva inexistente → 404."""
    cliente.force_login(admin_user)

    response = cliente.post(
        "/panel_admin/reserva/",
        {"reserva_id": 999999, "nuevo_estado": "completada"},
    )

    assert response.status_code == 404


# ── Activar / desactivar cuentas ─────────────────────────────────────

@pytest.mark.django_db
def test_admin_desactiva_cuenta(cliente, admin_user, profesional_user):
    """El admin desactiva la cuenta de un profesional (bloquea el login)."""
    cliente.force_login(admin_user)

    response = cliente.post(
        "/panel_admin/cuenta/", {"rut": "111111111"},
    )

    assert response.status_code == 302
    profesional_user.refresh_from_db()
    assert profesional_user.is_active is False


@pytest.mark.django_db
def test_admin_reactiva_cuenta(cliente, admin_user, profesional_user):
    """Aplicar el toggle dos veces vuelve a activar la cuenta."""
    cliente.force_login(admin_user)

    cliente.post("/panel_admin/cuenta/", {"rut": "111111111"})  # desactiva
    cliente.post("/panel_admin/cuenta/", {"rut": "111111111"})  # reactiva

    profesional_user.refresh_from_db()
    assert profesional_user.is_active is True


@pytest.mark.django_db
def test_admin_no_puede_desactivarse_a_si_mismo(cliente, admin_user):
    """Salvaguarda: el admin no puede desactivar su propia cuenta."""
    cliente.force_login(admin_user)

    response = cliente.post(
        "/panel_admin/cuenta/", {"rut": "123456789"},
    )

    assert response.status_code == 302
    admin_user.refresh_from_db()
    assert admin_user.is_active is True


@pytest.mark.django_db
def test_admin_toggle_cuenta_requiere_admin(cliente, paciente_user, profesional_user):
    """Un no-admin no puede activar/desactivar cuentas → 403."""
    cliente.force_login(paciente_user)

    response = cliente.post(
        "/panel_admin/cuenta/", {"rut": "111111111"},
    )

    assert response.status_code == 403
    profesional_user.refresh_from_db()
    assert profesional_user.is_active is True


# ── Exportación a CSV ────────────────────────────────────────────────

@pytest.mark.django_db
def test_admin_exporta_reservas_csv(cliente, admin_user, reserva):
    """El admin descarga un CSV con la cabecera y la reserva existente."""
    cliente.force_login(admin_user)

    response = cliente.get("/panel_admin/exportar/reservas/")

    assert response.status_code == 200
    assert response["Content-Type"].startswith("text/csv")
    assert "attachment" in response["Content-Disposition"]
    assert ".csv" in response["Content-Disposition"]

    cuerpo = response.content.decode("utf-8")
    assert "ID,Paciente,RUT paciente" in cuerpo
    assert "Cita de prueba" in cuerpo          # motivo de la reserva del fixture
    assert reserva.paciente.usuario.rut in cuerpo


@pytest.mark.django_db
def test_admin_exportar_requiere_admin(cliente, paciente_user):
    """Un no-admin no puede exportar → 403."""
    cliente.force_login(paciente_user)

    response = cliente.get("/panel_admin/exportar/reservas/")

    assert response.status_code == 403


# ── Acceso al admin de Django vía grupo de permisos ──────────────────

@pytest.mark.django_db
def test_crear_admin_asigna_grupo_con_permisos():
    """crear_admin deja al usuario is_staff y en el grupo 'Administradores'
    con permisos acotados (CRUD de dominio + ver/editar cuentas)."""
    call_command(
        "crear_admin",
        rut="12345678-9", password="admin123",
        nombre="Admin", apellido="Test", email="admin@test.cl",
    )

    user = User.objects.get(username="123456789")
    assert user.is_staff is True
    assert user.is_superuser is False
    assert user.groups.filter(name="Administradores").exists()

    grupo = Group.objects.get(name="Administradores")
    codenames = set(grupo.permissions.values_list("codename", flat=True))
    # CRUD sobre el dominio.
    assert {"add_reserva", "change_reserva", "delete_reserva", "view_reserva"} <= codenames
    # Sobre cuentas: solo ver y cambiar (no crear/borrar).
    assert {"view_user", "change_user"} <= codenames
    assert "delete_user" not in codenames


@pytest.mark.django_db
def test_crear_admin_es_idempotente():
    """Ejecutarlo dos veces no duplica grupos ni rompe la asignación."""
    for _ in range(2):
        call_command(
            "crear_admin",
            rut="12345678-9", password="admin123",
            nombre="Admin", apellido="Test", email="admin@test.cl",
        )

    assert Group.objects.filter(name="Administradores").count() == 1
    assert User.objects.filter(username="123456789").count() == 1
