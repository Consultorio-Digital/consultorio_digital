"""Parte 3 — Registro de usuarios y autenticación."""
import pytest
from django.contrib.auth.models import User

from consultorio.models import Paciente, Usuario
from tests.conftest import PASSWORD


@pytest.mark.django_db
def test_registro_paciente_exitoso(cliente):
    """POST a /registro/ con datos válidos → 302 y se crean User + Paciente."""
    datos = {
        "username": "12.345.678-5",     # RUT válido (DV correcto)
        "email": "nuevo@test.cl",
        "first_name": "María",
        "last_name": "González",
        "address": "Av. Principal 123",
        "phone": "+56912345678",
        "birthdate": "01/01/1990",
        "password1": "Reserva_Segura_2026",
        "password2": "Reserva_Segura_2026",
        "tipo": "paciente",
    }

    response = cliente.post("/registro/", datos)

    assert response.status_code == 302
    # El username se almacena normalizado (sin puntos ni guion).
    assert User.objects.filter(username="123456785").exists()
    usuario = Usuario.objects.get(rut="123456785")
    assert Paciente.objects.filter(usuario=usuario).exists()


@pytest.mark.django_db
def test_registro_rut_invalido(cliente):
    """POST con RUT de DV inválido → 200 y error en el campo username."""
    datos = {
        "username": "12.345.678-0",     # DV incorrecto (el válido es 5)
        "email": "malo@test.cl",
        "first_name": "Juan",
        "last_name": "Pérez",
        "password1": "Reserva_Segura_2026",
        "password2": "Reserva_Segura_2026",
        "tipo": "paciente",
    }

    response = cliente.post("/registro/", datos)

    assert response.status_code == 200
    form = response.context["form"]
    assert "username" in form.errors
    assert not User.objects.filter(username="123456780").exists()


@pytest.mark.django_db
def test_login_por_rut(cliente, paciente_user):
    """Login con RUT (con formato) → 302 hacia '/'."""
    response = cliente.post(
        "/login/",
        {"username": "66666666-6", "password": PASSWORD},
    )

    assert response.status_code == 302
    assert response.url == "/"


@pytest.mark.django_db
def test_login_por_email(cliente, paciente_user):
    """Login con correo electrónico → 302."""
    response = cliente.post(
        "/login/",
        {"username": "paciente@test.cl", "password": PASSWORD},
    )

    assert response.status_code == 302
    assert response.url == "/"


@pytest.mark.django_db
def test_login_credenciales_incorrectas(cliente, paciente_user):
    """Login con contraseña incorrecta → 200 (re-renderiza el formulario)."""
    response = cliente.post(
        "/login/",
        {"username": "66666666-6", "password": "clave_incorrecta"},
    )

    assert response.status_code == 200
    # No se inició sesión.
    assert not response.wsgi_request.user.is_authenticated


@pytest.mark.django_db
def test_registro_toggle_tipo(cliente):
    """El registro usa el toggle con hidden `tipo` + función setTipo (renderiza)."""
    resp = cliente.get("/registro/")
    assert resp.status_code == 200
    assert b'id="id_tipo"' in resp.content
    assert b'id="btn-paciente"' in resp.content
    assert b'id="btn-profesional"' in resp.content
    assert b'function setTipo' in resp.content


@pytest.mark.django_db
def test_login_tiene_link_recuperar(cliente):
    """El login muestra el enlace de recuperación de contraseña."""
    resp = cliente.get("/login/")
    assert resp.status_code == 200
    assert b'Olvidaste tu contrase' in resp.content


@pytest.mark.django_db
def test_password_reset_form_renderiza(cliente):
    """GET /password_reset/ → 200 con campo de correo."""
    resp = cliente.get("/password_reset/")
    assert resp.status_code == 200
    assert b'name="email"' in resp.content


@pytest.mark.django_db
def test_password_reset_envia_y_redirige(cliente, paciente_user):
    """POST con correo válido → 302 a /password_reset/done/, que renderiza."""
    resp = cliente.post("/password_reset/", {"email": "paciente@test.cl"})
    assert resp.status_code == 302
    assert resp.url == "/password_reset/done/"
    assert cliente.get("/password_reset/done/").status_code == 200


@pytest.mark.django_db
def test_password_reset_complete_renderiza(cliente):
    """La página final del flujo de recuperación renderiza."""
    assert cliente.get("/reset/done/").status_code == 200


@pytest.mark.django_db
def test_password_reset_confirm_link_valido(cliente, paciente_user):
    """Un enlace de recuperación válido muestra el formulario de nueva clave."""
    from django.contrib.auth.tokens import default_token_generator
    from django.utils.encoding import force_bytes
    from django.utils.http import urlsafe_base64_encode

    uid = urlsafe_base64_encode(force_bytes(paciente_user.pk))
    token = default_token_generator.make_token(paciente_user)

    resp = cliente.get(f"/reset/{uid}/{token}/", follow=True)
    assert resp.status_code == 200
    assert b'name="new_password1"' in resp.content
