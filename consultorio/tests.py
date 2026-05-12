from datetime import date, time

from django.test import TestCase

from .models import (
    Consultorio,
    Disponibilidad,
    Paciente,
    Profesional,
    Reserva,
    Usuario,
)


# ---------------------------------------------------------------------------
# Helpers para crear objetos de prueba
# ---------------------------------------------------------------------------

def _crear_consultorio(objectid=1, nombre="CESFAM Test", c_com="05101"):
    return Consultorio.objects.create(
        objectid  = objectid,
        nombre    = nombre,
        c_reg     = 5.0,
        nom_reg   = "Region de Valparaiso",
        c_com     = c_com,
        nom_com   = "Valparaiso",
        c_ant     = "", c_vig=1.0, c_mad="", c_nmad="",
        c_depend  = 1.0,
        depen     = "Municipal",
        perenec   = "SNSS",
        tipo      = "CESFAM",
        ambito    = "Urbano",
        urgencia  = "No",
        certifica = "No",
        depen_a   = "Municipal",
        nivel     = "Primario",
        via       = "Calle",
        numero    = "100",
        direccion = "Calle Principal 100",
        fono      = None,
        f_inicio  = 2000.0,
        f_reaper  = "",
        sapu      = "No",
        f_cambio  = "",
        tipo_camb = "",
        prestador = "Municipal",
        estado    = "Activo",
        nivel_com = "Primario",
        modalidad = "Presencial",
        latitud   = -33.05,
        longitud  = -71.62,
    )


def _crear_usuario(rut="123456785", nombre="Ana", apellido="Perez",
                   correo="ana@test.cl"):
    return Usuario.objects.create(
        rut             = rut,
        nombre          = nombre,
        apellido        = apellido,
        fecha_nacimiento= date(1990, 1, 15),
        correo          = correo,
    )


def _crear_profesional(rut="987654321", consultorio=None):
    usuario = _crear_usuario(
        rut=rut, nombre="Carlos", apellido="Lopez", correo="carlos@cesfam.cl"
    )
    return Profesional.objects.create(
        usuario      = usuario,
        especialidad = "Medicina General",
        consultorio  = consultorio,
    )


# ---------------------------------------------------------------------------
# ConsultorioModelTests
# ---------------------------------------------------------------------------

class ConsultorioModelTests(TestCase):
    """Pruebas unitarias para el modelo Consultorio."""

    def setUp(self):
        self.consultorio = _crear_consultorio()

    def test_str_retorna_nombre(self):
        self.assertEqual(str(self.consultorio), "CESFAM Test")

    def test_ordering_alfabetico_por_nombre(self):
        _crear_consultorio(objectid=2, nombre="CESFAM Angamos")
        _crear_consultorio(objectid=3, nombre="CESFAM Zonal Norte")
        nombres = list(Consultorio.objects.values_list("nombre", flat=True))
        self.assertEqual(nombres, sorted(nombres))

    def test_fono_puede_ser_nulo(self):
        self.assertIsNone(self.consultorio.fono)

    def test_primary_key_es_objectid(self):
        recuperado = Consultorio.objects.get(pk=1)
        self.assertEqual(recuperado.nombre, "CESFAM Test")


# ---------------------------------------------------------------------------
# UsuarioModelTests
# ---------------------------------------------------------------------------

class UsuarioModelTests(TestCase):
    """Pruebas unitarias para el modelo Usuario."""

    def setUp(self):
        self.usuario = _crear_usuario()

    def test_str_retorna_rut(self):
        self.assertEqual(str(self.usuario), "123456785")

    def test_primary_key_es_rut(self):
        recuperado = Usuario.objects.get(pk="123456785")
        self.assertEqual(recuperado.nombre, "Ana")

    def test_telefono_puede_ser_nulo(self):
        self.assertIsNone(self.usuario.telefono)


# ---------------------------------------------------------------------------
# ReservaModelTests
# ---------------------------------------------------------------------------

class ReservaModelTests(TestCase):
    """Pruebas unitarias para el modelo Reserva."""

    def setUp(self):
        from django.utils import timezone
        self.consultorio = _crear_consultorio()
        self.usuario     = _crear_usuario()
        self.paciente    = Paciente.objects.create(
            usuario = self.usuario,
            ingreso = date(2026, 1, 1),
        )
        self.reserva = Reserva.objects.create(
            consultorio  = self.consultorio,
            paciente     = self.paciente,
            fecha_reserva= timezone.now(),
            motivo       = "Control general",
        )

    def test_estado_por_defecto_es_pendiente(self):
        self.assertEqual(self.reserva.estado, "pendiente")

    def test_estados_disponibles(self):
        estados = [c[0] for c in Reserva.ESTADO_CHOICES]
        for esperado in ("pendiente", "confirmada", "completada",
                         "seguimiento", "cancelada", "no_asistio"):
            self.assertIn(esperado, estados)

    def test_str_contiene_nombre_consultorio_y_paciente(self):
        s = str(self.reserva)
        self.assertIn("CESFAM Test", s)
        self.assertIn("123456785", s)

    def test_notas_doctor_puede_ser_nulo(self):
        self.assertIsNone(self.reserva.notas_doctor)

    def test_fecha_seguimiento_puede_ser_nula(self):
        self.assertIsNone(self.reserva.fecha_seguimiento)

    def test_motivo_cancelacion_puede_ser_nulo(self):
        self.assertIsNone(self.reserva.motivo_cancelacion)

    def test_puede_cambiar_estado_a_cancelada(self):
        self.reserva.estado = "cancelada"
        self.reserva.save()
        actualizada = Reserva.objects.get(pk=self.reserva.pk)
        self.assertEqual(actualizada.estado, "cancelada")


# ---------------------------------------------------------------------------
# ProfesionalModelTests
# ---------------------------------------------------------------------------

class ProfesionalModelTests(TestCase):
    """Pruebas unitarias para el modelo Profesional."""

    def setUp(self):
        self.consultorio = _crear_consultorio()
        self.profesional = _crear_profesional(consultorio=self.consultorio)

    def test_str_retorna_rut_del_usuario(self):
        self.assertEqual(str(self.profesional), "987654321")

    def test_consultorio_puede_ser_nulo(self):
        prof = _crear_profesional(rut="111111115", consultorio=None)
        self.assertIsNone(prof.consultorio)


# ---------------------------------------------------------------------------
# DisponibilidadModelTests
# ---------------------------------------------------------------------------

class DisponibilidadModelTests(TestCase):
    """Pruebas unitarias para el modelo Disponibilidad."""

    def setUp(self):
        self.consultorio = _crear_consultorio()
        self.profesional = _crear_profesional(consultorio=self.consultorio)

    def test_str_contiene_profesional_y_fecha(self):
        disp = Disponibilidad.objects.create(
            profesional = self.profesional,
            fecha       = date(2026, 6, 1),
            hora_inicio = time(9, 0),
            hora_fin    = time(13, 0),
        )
        s = str(disp)
        self.assertIn("2026-06-01", s)

    def test_unique_together_profesional_fecha_hora_inicio(self):
        from django.db import IntegrityError
        Disponibilidad.objects.create(
            profesional = self.profesional,
            fecha       = date(2026, 6, 2),
            hora_inicio = time(14, 0),
            hora_fin    = time(18, 0),
        )
        with self.assertRaises(IntegrityError):
            Disponibilidad.objects.create(
                profesional = self.profesional,
                fecha       = date(2026, 6, 2),
                hora_inicio = time(14, 0),
                hora_fin    = time(16, 0),
            )

    def test_ordering_por_fecha_luego_hora_inicio(self):
        Disponibilidad.objects.create(
            profesional=self.profesional,
            fecha=date(2026, 6, 3),
            hora_inicio=time(14, 0),
            hora_fin=time(18, 0),
        )
        Disponibilidad.objects.create(
            profesional=self.profesional,
            fecha=date(2026, 6, 3),
            hora_inicio=time(9, 0),
            hora_fin=time(13, 0),
        )
        fechas_horas = list(
            Disponibilidad.objects.values_list("fecha", "hora_inicio")
        )
        self.assertEqual(
            fechas_horas,
            sorted(fechas_horas, key=lambda x: (x[0], x[1]))
        )
