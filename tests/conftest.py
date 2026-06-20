"""Fixtures reutilizables para la suite pytest del proyecto Consultorio Digital.

Convenciones importantes (ver CLAUDE.md):
- auth.User.username almacena el RUT normalizado (sin puntos ni guion).
- El dominio (consultorio.Usuario) se vincula a auth.User por ese mismo RUT.
- La deteccion de rol consulta Administrador/Profesional/Paciente por
  ``usuario__rut == request.user.username``.

Los fixtures de usuario crean las TRES capas (auth.User + Usuario + rol) con
RUT ya normalizado, y devuelven el auth.User con atributos de conveniencia
``.usuario`` y ``.administrador`` / ``.profesional`` / ``.paciente`` para que
las pruebas accedan a los objetos de dominio sin reconsultar.
"""
from datetime import date

import pytest
from django.contrib.auth.models import User
from django.test import Client

from consultorio.models import (
    Administrador,
    Consultorio,
    Paciente,
    Profesional,
    Usuario,
)

# Contraseña que cumple los validadores de Django (>=8 chars, no numerica,
# no comun, no similar al usuario).
PASSWORD = "Consultorio_2026!"


@pytest.fixture
def cliente():
    """Cliente HTTP de pruebas de Django."""
    return Client()


@pytest.fixture
def consultorio(db):
    """Consultorio de prueba con todos los campos requeridos poblados."""
    return Consultorio.objects.create(
        objectid=9999,
        nombre="Test Consultorio",
        c_reg=5,
        nom_reg="Valparaíso",
        c_com="05109",
        nom_com="Viña del Mar",
        c_ant="",
        c_vig=1.0,
        c_mad="",
        c_nmad="",
        c_depend=1.0,
        depen="Municipal",
        perenec="SNSS",
        tipo="CESFAM",
        ambito="Urbano",
        urgencia="No",
        certifica="No",
        depen_a="Municipal",
        nivel="Primario",
        via="Calle",
        numero="100",
        direccion="Av. Test 100",
        fono=None,
        f_inicio=2000.0,
        f_reaper="",
        sapu="No",
        f_cambio="",
        tipo_camb="",
        prestador="Municipal",
        estado="Activo",
        nivel_com="Primario",
        modalidad="Presencial",
        latitud=-33.0,
        longitud=-71.5,
    )


@pytest.fixture
def admin_user(db):
    """auth.User + Usuario + Administrador con RUT 12345678-9 (normalizado)."""
    user = User.objects.create_user(
        username="123456789",
        email="admin@test.cl",
        password=PASSWORD,
        first_name="Admin",
        last_name="Test",
        is_staff=True,
    )
    usuario = Usuario.objects.create(
        rut="123456789",
        nombre="Admin",
        apellido="Test",
        fecha_nacimiento=date(1980, 1, 1),
        correo="admin@test.cl",
    )
    administrador = Administrador.objects.create(usuario=usuario)
    user.usuario = usuario
    user.administrador = administrador
    return user


@pytest.fixture
def profesional_user(db):
    """auth.User + Usuario + Profesional con RUT 11111111-1, Medicina General."""
    user = User.objects.create_user(
        username="111111111",
        email="profesional@test.cl",
        password=PASSWORD,
        first_name="Doc",
        last_name="Tor",
    )
    usuario = Usuario.objects.create(
        rut="111111111",
        nombre="Doc",
        apellido="Tor",
        fecha_nacimiento=date(1975, 5, 5),
        correo="profesional@test.cl",
    )
    profesional = Profesional.objects.create(
        usuario=usuario,
        especialidad="Medicina General",
    )
    user.usuario = usuario
    user.profesional = profesional
    return user


@pytest.fixture
def paciente_user(db):
    """auth.User + Usuario + Paciente con RUT 66666666-6 (normalizado)."""
    user = User.objects.create_user(
        username="666666666",
        email="paciente@test.cl",
        password=PASSWORD,
        first_name="Pa",
        last_name="Ciente",
    )
    usuario = Usuario.objects.create(
        rut="666666666",
        nombre="Pa",
        apellido="Ciente",
        fecha_nacimiento=date(1990, 3, 3),
        correo="paciente@test.cl",
    )
    paciente = Paciente.objects.create(
        usuario=usuario,
        ingreso=date(2026, 1, 1),
    )
    user.usuario = usuario
    user.paciente = paciente
    return user
