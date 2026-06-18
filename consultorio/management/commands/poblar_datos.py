from datetime import date, datetime, time, timedelta

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from consultorio.models import (
    Usuario, Profesional, Paciente, Consultorio, Disponibilidad, Reserva,
)
from registro.backends import _normalize_rut


# (rut, nombre, apellido, especialidad)
PROFESIONALES = [
    ("11111111-1", "Carlos",  "Muñoz",     "Medicina General"),
    ("22222222-2", "María",   "Rojas",     "Pediatría"),
    ("33333333-3", "Javiera", "Contreras", "Ginecología"),
    ("44444444-4", "Pedro",   "Sandoval",  "Traumatología"),
    ("55555555-5", "Antonia", "Fuentes",   "Salud Mental"),
]

# Nombres para los 10 pacientes (los RUTs se generan consecutivos desde 66666666-6)
PACIENTES_NOMBRES = [
    ("Lucía",     "Pérez"),
    ("Diego",     "González"),
    ("Camila",    "Soto"),
    ("Matías",    "Hernández"),
    ("Valentina", "Díaz"),
    ("Benjamín",  "Torres"),
    ("Isidora",   "Castro"),
    ("Vicente",   "Reyes"),
    ("Florencia", "Vega"),
    ("Tomás",     "Araya"),
]

MOTIVOS = [
    "Control de presión arterial",
    "Dolor abdominal persistente hace una semana",
    "Control de embarazo (segundo trimestre)",
    "Dolor lumbar tras esfuerzo físico",
    "Cuadro de ansiedad y problemas para dormir",
    "Control de niño sano",
    "Resfrío con fiebre y dolor de garganta",
    "Control de diabetes tipo 2",
    "Esguince de tobillo derecho",
    "Cefaleas frecuentes en las últimas semanas",
]

# Distribución de estados pedida: 5 + 5 + 3 + 3 + 2 + 2 = 20
ESTADOS = (
    ["pendiente"]   * 5 +
    ["confirmada"]  * 5 +
    ["cancelada"]   * 3 +
    ["completada"]  * 3 +
    ["seguimiento"] * 2 +
    ["no_asistio"]  * 2
)


class Command(BaseCommand):
    help = "Genera datos de prueba realistas (idempotente). Usa los consultorios ya cargados en BD."

    @transaction.atomic
    def handle(self, *args, **options):
        if not Consultorio.objects.exists():
            raise CommandError(
                "No hay consultorios en la BD. Ejecuta primero: "
                "python manage.py cargar_consultorios"
            )

        # ── 1. Profesionales ────────────────────────────────────────────
        # 5 consultorios reales de Viña del Mar (en BD; no se crean).
        # Si hay menos de 5, se toman los que existan.
        consultorios = list(
            Consultorio.objects
            .filter(nom_com__icontains='VIÑA DEL MAR')
            .order_by('?')[:5]
        )
        self.stdout.write(
            f"Consultorios de Viña del Mar encontrados: {len(consultorios)}"
        )
        if not consultorios:
            raise CommandError(
                "No se encontraron consultorios en Viña del Mar. "
                "¿Cargaste los datos con cargar_consultorios?"
            )
        profesionales = []
        for (rut, nombre, apellido, especialidad), consultorio in zip(PROFESIONALES, consultorios):
            usuario = self._crear_usuario(
                rut=rut, nombre=nombre, apellido=apellido,
                fecha_nacimiento=date(1980, 1, 1),
                password="prof123",
            )
            profesional, _ = Profesional.objects.get_or_create(
                usuario=usuario,
                defaults={"especialidad": especialidad, "consultorio": consultorio},
            )
            # Reasigna consultorio/especialidad también si el profesional ya existía
            # (re-ejecución idempotente: actualiza sin duplicar).
            if profesional.consultorio_id != consultorio.objectid or profesional.especialidad != especialidad:
                profesional.consultorio = consultorio
                profesional.especialidad = especialidad
                profesional.save(update_fields=["consultorio", "especialidad"])
            profesionales.append(profesional)

        # ── 1b. Profesional fijo en "Nueva Aurora" (para que el paciente de
        #        prueba pueda reservar en ese consultorio del flujo de reserva) ──
        nueva_aurora = Consultorio.objects.filter(nombre__icontains='Nueva Aurora').first()
        if nueva_aurora is None:
            self.stdout.write(self.style.WARNING(
                "Advertencia: consultorio 'Nueva Aurora' no encontrado en BD; "
                "se omite el profesional fijo María González."
            ))
        else:
            usuario = self._crear_usuario(
                rut="99999999-9", nombre="María", apellido="González",
                fecha_nacimiento=date(1980, 1, 1),
                password="prof123",
            )
            profesional, _ = Profesional.objects.get_or_create(
                usuario=usuario,
                defaults={"especialidad": "Medicina General", "consultorio": nueva_aurora},
            )
            # Reasigna también si ya existía (idempotente).
            if profesional.consultorio_id != nueva_aurora.objectid or profesional.especialidad != "Medicina General":
                profesional.consultorio = nueva_aurora
                profesional.especialidad = "Medicina General"
                profesional.save(update_fields=["consultorio", "especialidad"])
            profesionales.append(profesional)

        # ── 2. Pacientes ────────────────────────────────────────────────
        pacientes = []
        for i, (nombre, apellido) in enumerate(PACIENTES_NOMBRES):
            num = 66666666 + i
            rut = f"{num}-{num % 10}"                       # 66666666-6, 66666667-7, ...
            anio = 1970 + (i * 3)                           # 1970..1997
            nacimiento = date(anio, (i % 12) + 1, (i * 2 % 28) + 1)
            usuario = self._crear_usuario(
                rut=rut, nombre=nombre, apellido=apellido,
                fecha_nacimiento=nacimiento,
                password="pac123",
            )
            paciente, _ = Paciente.objects.get_or_create(
                usuario=usuario,
                defaults={"ingreso": date.today()},
            )
            pacientes.append(paciente)

        # ── 3. Disponibilidades (3 fechas hábiles próximas, 08:00–13:00) ──
        fechas = self._proximas_fechas_habiles(3)
        disponibilidades_creadas = 0
        for profesional in profesionales:
            for f in fechas:
                _, creada = Disponibilidad.objects.get_or_create(
                    profesional=profesional,
                    fecha=f,
                    hora_inicio=time(8, 0),
                    defaults={"hora_fin": time(13, 0)},
                )
                disponibilidades_creadas += int(creada)

        # ── 4. Reservas (20, estados variados, en slots de las disponibilidades) ──
        # Pool determinista de slots de 30 min por profesional/fecha → sin doble reserva.
        slots = []
        for profesional in profesionales:
            for f in fechas:
                t = datetime.combine(f, time(8, 0))
                fin = datetime.combine(f, time(13, 0))
                while t < fin:
                    slots.append((profesional, t))
                    t += timedelta(minutes=30)

        reservas_creadas = 0
        for i, estado in enumerate(ESTADOS):
            profesional, slot_dt = slots[i]            # slot único por reserva
            paciente = pacientes[i % len(pacientes)]
            consultorio = profesional.consultorio or consultorios[0]
            fecha_reserva = timezone.make_aware(slot_dt)

            defaults = {
                "consultorio": consultorio,
                "motivo": MOTIVOS[i % len(MOTIVOS)],
                "estado": estado,
            }
            if estado == "cancelada":
                defaults["motivo_cancelacion"] = "El paciente no podrá asistir a la hora agendada."
            elif estado == "seguimiento":
                defaults["fecha_seguimiento"] = slot_dt.date() + timedelta(days=14)
                defaults["notas_doctor"] = "Requiere control en dos semanas para evaluar evolución."
            elif estado == "completada":
                defaults["notas_doctor"] = "Atención realizada sin novedades. Indicaciones entregadas."

            _, creada = Reserva.objects.get_or_create(
                paciente=paciente,
                profesional=profesional,
                fecha_reserva=fecha_reserva,
                defaults=defaults,
            )
            reservas_creadas += int(creada)

        # ── Resumen ─────────────────────────────────────────────────────
        self.stdout.write(self.style.SUCCESS("\nDatos de prueba poblados:"))
        self.stdout.write(f"  Profesionales creados/existentes: {len(profesionales)}")
        self.stdout.write(f"  Pacientes creados/existentes: {len(pacientes)}")
        self.stdout.write(f"  Disponibilidades creadas: {disponibilidades_creadas}")
        self.stdout.write(f"  Reservas creadas: {reservas_creadas}")

    # ── Helpers ──────────────────────────────────────────────────────────
    def _crear_usuario(self, *, rut, nombre, apellido, fecha_nacimiento, password):
        """Crea/recupera auth.User + consultorio.Usuario vinculados por RUT normalizado."""
        rut_norm = _normalize_rut(rut)
        correo = f"{rut_norm}@example.cl"

        user, _ = User.objects.get_or_create(
            username=rut_norm,
            defaults={
                "first_name": nombre,
                "last_name": apellido,
                "email": correo,
            },
        )
        # Garantiza la credencial conocida del dato semilla (idempotente:
        # re-ejecutar solo vuelve a fijar el mismo password).
        user.set_password(password)
        user.save(update_fields=["password"])

        usuario, _ = Usuario.objects.get_or_create(
            rut=rut_norm,
            defaults={
                "nombre": nombre,
                "apellido": apellido,
                "fecha_nacimiento": fecha_nacimiento,
                "correo": correo,
            },
        )
        return usuario

    def _proximas_fechas_habiles(self, n):
        fechas = []
        d = timezone.localdate() + timedelta(days=1)
        while len(fechas) < n:
            if d.weekday() < 5:        # 0=lunes ... 4=viernes
                fechas.append(d)
            d += timedelta(days=1)
        return fechas
