"""Context processors del dominio.

Expone el rol del usuario autenticado a TODOS los templates, para que el
navbar (en base.html) decida qué navegación mostrar sin que cada template
repita la lógica. Sigue la misma precedencia que principal.views.home():
admin > profesional > paciente.
"""
from .models import Administrador, Profesional, Paciente


def rol_usuario(request):
    user = getattr(request, "user", None)
    if not user or not user.is_authenticated:
        return {"es_admin": False, "es_profesional": False, "es_paciente": False}

    rut = user.username
    es_admin = Administrador.objects.filter(usuario__rut=rut).exists()
    es_profesional = (
        not es_admin
        and Profesional.objects.filter(usuario__rut=rut).exists()
    )
    es_paciente = (
        not es_admin
        and not es_profesional
        and Paciente.objects.filter(usuario__rut=rut).exists()
    )
    return {
        "es_admin": es_admin,
        "es_profesional": es_profesional,
        "es_paciente": es_paciente,
    }
