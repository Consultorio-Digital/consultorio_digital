from datetime import date

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from consultorio.models import Usuario, Administrador
from registro.backends import _normalize_rut


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

        self.stdout.write(self.style.SUCCESS(
            f"✓ Administrador listo para RUT {rut} "
            f"(User {'creado' if user_created else 'actualizado'}, "
            f"Usuario {'creado' if usuario_created else 'existente'}, "
            f"Administrador {'creado' if admin_created else 'existente'})."
        ))
