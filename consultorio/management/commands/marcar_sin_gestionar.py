from django.core.management.base import BaseCommand

from consultorio.models import Reserva


class Command(BaseCommand):
    help = (
        "Marca como 'sin_gestionar' las reservas pendientes (sin confirmar) "
        "cuya fecha/hora ya pasó. Idempotente; pensado para correr por cron."
    )

    def handle(self, *args, **options):
        actualizadas = Reserva.expirar_pendientes()
        self.stdout.write(
            self.style.SUCCESS(
                f"Reservas marcadas como 'sin gestionar': {actualizadas}"
            )
        )
