from datetime import date

from django.contrib.auth.models import User, Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from consultorio.models import (
    Usuario, Administrador, Profesional, Paciente,
    Reserva, Consultorio, Disponibilidad,
)
from registro.backends import _normalize_rut


# Nombre del grupo de permisos para administradores de dominio.
GRUPO_ADMIN = "Administradores"


def configurar_grupo_admin() -> Group:
    """Crea (idempotente) el grupo de administradores y le asigna permisos.

    Otorga CRUD completo sobre los modelos del dominio y solo ver/editar
    sobre auth.User (para activar/desactivar cuentas, sin poder borrarlas).
    Así el admin es is_staff=True con permisos acotados, en lugar de un
    superusuario con acceso total.
    """
    grupo, _ = Group.objects.get_or_create(name=GRUPO_ADMIN)

    perms = []
    modelos_dominio = [
        Usuario, Administrador, Profesional, Paciente,
        Reserva, Consultorio, Disponibilidad,
    ]
    for modelo in modelos_dominio:
        ct = ContentType.objects.get_for_model(modelo)
        perms += list(Permission.objects.filter(content_type=ct))

    # auth.User: solo ver y cambiar (no crear ni borrar cuentas desde aquí).
    ct_user = ContentType.objects.get_for_model(User)
    perms += list(
        Permission.objects.filter(
            content_type=ct_user, codename__in=["view_user", "change_user"]
        )
    )

    grupo.permissions.set(perms)
    return grupo


class Command(BaseCommand):
    help = "Crea (de forma idempotente) un administrador: auth.User + Usuario + Administrador."

    def add_arguments(self, parser):
        parser.add_argument("--rut", required=True, help="RUT del administrador (con o sin puntos/guión).")
        parser.add_argument("--password", required=True, help="Contraseña del administrador.")
        parser.add_argument("--nombre", required=True, help="Nombre del administrador.")
        parser.add_argument("--apellido", required=True, help="Apellido del administrador.")
        parser.add_argument("--email", required=True, help="Correo del administrador.")

    @transaction.atomic
    def handle(self, *args, **options):
        rut      = _normalize_rut(options["rut"])
        password = options["password"]
        nombre   = options["nombre"]
        apellido = options["apellido"]
        email    = options["email"]

        if not rut:
            raise CommandError("El RUT no puede estar vacío.")

        # 1. auth.User (idempotente por username = rut normalizado)
        user, user_created = User.objects.get_or_create(
            username=rut,
            defaults={
                "email"      : email,
                "first_name" : nombre,
                "last_name"  : apellido,
                "is_staff"   : True,
                "is_superuser": False,
            },
        )
        # Asegurar atributos clave aunque el usuario ya existiera.
        user.email        = email
        user.first_name   = nombre
        user.last_name    = apellido
        user.is_staff     = True
        user.is_superuser = False
        user.set_password(password)
        user.save()

        # 2. consultorio.Usuario vinculado (PK = rut)
        usuario, usuario_created = Usuario.objects.get_or_create(
            rut=rut,
            defaults={
                "nombre"          : nombre,
                "apellido"        : apellido,
                "fecha_nacimiento": date.today(),
                "correo"          : email,
            },
        )
        usuario.nombre   = nombre
        usuario.apellido = apellido
        usuario.correo   = email
        usuario.save()

        # 3. consultorio.Administrador vinculado al Usuario
        administrador, admin_created = Administrador.objects.get_or_create(usuario=usuario)

        # 4. Grupo de permisos para acceder al admin de Django (/admin/).
        grupo = configurar_grupo_admin()
        user.groups.add(grupo)

        self.stdout.write(self.style.SUCCESS(
            f"✓ Administrador listo para RUT {rut} "
            f"(User {'creado' if user_created else 'actualizado'}, "
            f"Usuario {'creado' if usuario_created else 'existente'}, "
            f"Administrador {'creado' if admin_created else 'existente'}, "
            f"grupo '{GRUPO_ADMIN}' asignado)."
        ))
